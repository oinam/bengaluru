"""Stage 4: join the frames into a Deep Zoom pyramid and write the search index."""

import hashlib
import json
import shutil
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import pyvips
from pyproj import Transformer

from bengaluru.areas import Area
from bengaluru.detail import (
    DEFAULT_VIEW,
    LANDMARKS_PATH,
    LAYERS,
    PROJECTION,
    RENDERED_VIEWS,
    SPRITE_DIR,
    VIADUCT_M,
    _render_view,
    frames_dir,
    frames_fingerprint,
    layer_colors,
    layer_path,
    load_scene,
    manifest_path,
    plan_view,
    trees_path,
)
from bengaluru.palettes import BLOOM_MONTHS, BLOSSOM
from bengaluru.prepare import METRIC_CRS, derived_path, metro_path, prepare_metro
from bengaluru.render import parts

TILE_PX = 512
AREA_KINDS = {"city", "suburb", "town"}
LOCALITY_KINDS = {"village", "neighbourhood", "locality", "quarter", "hamlet"}
NOTABLE_KINDS = {"landmark", "university"}
# Names that label early whatever OSM calls their kind. None yet.
NOTABLE_NAMES: set[str] = set()
TILE_SUFFIX = ".webp[lossless=true,effort=4]"
PYRAMID_DIR = "pyramid"
# A layer is mostly clear, so its tiles are larger: a quarter as many files to keep and send.
LAYER_TILE_PX = 1024
# Blossom shrinks into the pyramid's smaller levels as the map does, by the mean, and thins
# out as the trees it sits on do. Lights are pooled: each time they halve, a pixel keeps this
# many times the mean of the four it stands for, up to a full light. At 1, the mean, a window
# is gone in two halvings and the far city is dark; at 4, the brightest pixel, every window
# stays whole and the far city is one flat sheet. In between a lone window fades slowly, and
# from afar the city glows brightest where it is built densest.
LIGHTS_KEPT = 2.0
# What decides the tiles besides the frames; a view tiled another way is built again.
TILING = f"{TILE_PX}:{TILE_SUFFIX}:{LAYER_TILE_PX}:{LIGHTS_KEPT}"
# A level of the lights this small is held in memory, and the smaller ones made from it;
# a larger one is read from the frames again.
HELD_BYTES = 1 << 30
# What a view's entry names its pyramids by: the map, then each layer.
PYRAMID_KEYS = ("pyramid", *LAYERS)
VIEWS_RECORD = "views.json"
FLOW_SIMPLIFY_M = 6.0
METRO_SIMPLIFY_M = 2.0


def tiles_dir(area: Area) -> Path:
    return Path("out") / area.name / "tiles"


def pyramid_version(paths: list[Path], columns: int, tile_px: int = TILE_PX, how: str = "") -> str:
    """Return a short hash of everything that decides the tile bytes."""
    digest = hashlib.blake2b(f"{tile_px}:{TILE_SUFFIX}:{columns}{how}".encode(), digest_size=5)
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _to_canvas(x: float, y: float, x_offset: float, y_offset: float) -> tuple[int, int]:
    """Return the canvas pixel a metric point lands on."""
    a, b, d, e = PROJECTION.matrix
    return round(a * x + b * y + x_offset), round(d * x + e * y + y_offset)


def search_index(area: Area, x_offset: float, y_offset: float) -> list[dict]:
    """Return OSM names with their canvas positions, one entry per name and place."""
    pois = gpd.read_file(derived_path(area), layer="pois")
    landmarks = landmark_positions(area)
    entries = {}
    for row in pois.itertuples():
        if row.name in landmarks:
            continue
        px, py = _to_canvas(row.geometry.x, row.geometry.y, x_offset, y_offset)
        kind = row.kind or ""
        entries[row.name, px // 200, py // 200] = {
            "name": row.name,
            "kind": kind,
            "x": px,
            "y": py,
            "tier": _tier(row.name, kind),
        }
    for name, (x, y) in landmarks.items():
        px, py = _to_canvas(x, y, x_offset, y_offset)
        entries[name, "landmark"] = {
            "name": name,
            "kind": "landmark",
            "x": px,
            "y": py,
            "tier": 2,
        }
    return sorted(entries.values(), key=lambda entry: (entry["name"], entry["x"]))


def flow_lines(area: Area, x_offset: float, y_offset: float) -> list[dict]:
    """Return waterways as canvas polylines; OSM draws each one in the downstream direction.

    Rivers carry their names, which the viewer labels along the stretch in view.
    """
    ways = gpd.read_file(derived_path(area), layer="waterways")
    lines = []
    for row in ways.itertuples():
        for points in _polylines(row.geometry, FLOW_SIMPLIFY_M, x_offset, y_offset):
            line = {"width": round(row.width_m), "points": points}
            if row.waterway == "river" and isinstance(row.name, str) and len(points) > 1:
                line["name"] = row.name
            lines.append(line)
    return lines


def _polylines(geometry, tolerance_m: float, x_offset: float, y_offset: float) -> list[list]:
    """Return a line, or each part of a broken one, simplified, as canvas points."""
    return [
        [list(_to_canvas(x, y, x_offset, y_offset)) for x, y in part.simplify(tolerance_m).coords]
        for part in parts(geometry)
    ]


def metro_index(area: Area, x_offset: float, y_offset: float) -> dict:
    """Return the metro for the viewer: each track as a canvas polyline in its line's color,
    and each station by name.

    Positions are on the ground. `raised_px` is how far up the canvas the viewer moves
    whatever is `raised`, to set it on the viaduct's deck. A line or a station is open,
    proposed, or, if neither, being built. An area the metro does not reach has no lines
    and no stations.
    """
    path = metro_path(area)
    layers = set(pyogrio.list_layers(path)[:, 0]) if path.exists() else set()
    lines, stations = [], []
    if "metro" in layers:
        for row in gpd.read_file(path, layer="metro").itertuples():
            lines.extend(
                {
                    # A name or a color that no tag gives reads back as a missing number.
                    "line": row.line if isinstance(row.line, str) else None,
                    "colour": row.colour if isinstance(row.colour, str) else None,
                    "open": bool(row.open),
                    "proposed": bool(row.proposed),
                    "level": row.level,
                    "points": points,
                }
                for points in _polylines(row.geometry, METRO_SIMPLIFY_M, x_offset, y_offset)
            )
    if "stations" in layers:
        for row in gpd.read_file(path, layer="stations").itertuples():
            x, y = _to_canvas(row.geometry.x, row.geometry.y, x_offset, y_offset)
            stations.append(
                {
                    "name": row.name,
                    "x": x,
                    "y": y,
                    "open": bool(row.open),
                    "proposed": bool(row.proposed),
                    "level": row.level,
                }
            )
    stations.sort(key=lambda station: (station["name"], station["x"]))
    return {
        "raised_px": round(VIADUCT_M * PROJECTION.lift, 1),
        "lines": lines,
        "stations": stations,
    }


def _tier(name: str, kind: str) -> int:
    """Return the zoom tier for a label: 1 shows first, 3 only when zoomed well in."""
    if kind in AREA_KINDS:
        return 1
    if kind in LOCALITY_KINDS or kind in NOTABLE_KINDS or name in NOTABLE_NAMES:
        return 2
    return 3


def landmark_positions(area: Area) -> dict[str, tuple[float, float]]:
    """Return metric positions for every labeled landmark."""
    to_metric = Transformer.from_crs(4326, METRIC_CRS, always_xy=True)
    positions = {}
    for path in sorted(SPRITE_DIR.glob("*.json")):
        sidecar = json.loads(path.read_text())
        if "label" in sidecar:
            placed = sidecar["placed_at"]
            positions[sidecar["label"]] = to_metric.transform(placed["lon"], placed["lat"])
    buildings = gpd.read_file(derived_path(area), layer="buildings", columns=["building_id"])
    centers = buildings.set_index("building_id").geometry.centroid
    for entry in json.loads(LANDMARKS_PATH.read_text()):
        if "label" in entry and entry["replaces"][0] in centers.index:
            center = centers.loc[entry["replaces"][0]]
            positions[entry["label"]] = (center.x, center.y)
    return positions


def landmark_credits() -> list[dict]:
    """Return one credit per landmark, with the photographs it was drawn from."""
    sources = [json.loads(path.read_text()) for path in sorted(SPRITE_DIR.glob("*.json"))]
    sources += json.loads(LANDMARKS_PATH.read_text())
    entries = {}
    for source in sources:
        name = source.get("credit") or source.get("label") or source["name"]
        entries.setdefault(name, {"name": name, "references": source["references"]})
    return sorted(entries.values(), key=lambda credit: credit["name"])


def _joined(paths: list[Path], columns: int) -> pyvips.Image:
    images = [pyvips.Image.new_from_file(str(path), access="sequential") for path in paths]
    return pyvips.Image.arrayjoin(images, across=columns)


def halved_lights(lights: pyvips.Image) -> pyvips.Image:
    """Return a picture of lights at half its size, each pixel LIGHTS_KEPT times the mean of
    the four it stands for. A pixel past a full light is held to one, in its own color.
    """
    even = lights.embed(0, 0, lights.width + lights.width % 2, lights.height + lights.height % 2)
    pooled = even.cast("float").shrink(2, 2) * LIGHTS_KEPT
    first, *rest = pooled.bandsplit()
    peak = first.bandrank(rest, index=len(rest))
    held = (peak > 255).ifthenelse(pooled * 255 / peak, pooled)
    return held.rint().cast("uchar").copy(interpretation="srgb")


def _save_lights(paths: list[Path], columns: int, pyramid: Path) -> pyvips.Image:
    """Write the lights' pyramid a level at a time, since libvips shrinks a pyramid only by
    the mean or the brightest pixel, and return the picture at full size.
    """
    full = _joined(paths, columns)
    top = (max(full.width, full.height) - 1).bit_length()
    image, held = full, False
    for halvings in range(top + 1):
        if held:
            # Each level is worked out before the next is made from it: left as one long
            # chain of halvings, libvips overruns its stack when it lets the chain go.
            image = halved_lights(image).copy_memory()
        elif halvings:
            image = _joined(paths, columns)
            for _ in range(halvings):
                image = halved_lights(image)
            if image.width * image.height * image.bands <= HELD_BYTES:
                image, held = image.copy_memory(), True
        scratch = pyramid.with_name("level")
        image.dzsave(
            str(scratch), tile_size=LAYER_TILE_PX, overlap=0, suffix=TILE_SUFFIX, depth="one"
        )
        # A pyramid of one level names it 0, whatever its place in this one.
        files = Path(f"{pyramid}_files")
        files.mkdir(exist_ok=True)
        shutil.move(f"{scratch}_files/0", files / str(top - halvings))
        shutil.rmtree(f"{scratch}_files")
        index = scratch.with_suffix(".dzi")
        if halvings:
            index.unlink()
        else:
            index.rename(pyramid.with_suffix(".dzi"))
    return full


def _build_pyramid(
    area: Area, view: str, target: Path, manifest: dict, layer: str | None = None
) -> str:
    """Write the tiles of one view's map, or of one of its layers, and return their version."""
    columns, rows = manifest["columns"], manifest["rows"]
    paths = [
        frames_dir(area, view) / f"{row:03d}_{column:03d}.png"
        for row in range(rows)
        for column in range(columns)
    ]
    tile_px = TILE_PX
    if layer:
        paths = [layer_path(path, layer) for path in paths]
        tile_px = LAYER_TILE_PX
    pooled = f":{LIGHTS_KEPT}" if layer == "lights" else ""
    version = pyramid_version(paths, columns, tile_px, f":{layer}{pooled}" if layer else "")
    pyramid = target / PYRAMID_DIR / version
    # A build stopped partway through leaves an unfinished pyramid; start it again.
    shutil.rmtree(pyramid, ignore_errors=True)
    pyramid.mkdir(parents=True)
    if layer == "lights":
        joined = _save_lights(paths, columns, pyramid / area.name)
    else:
        joined = _joined(paths, columns)
        joined.dzsave(
            str(pyramid / area.name),
            tile_size=tile_px,
            overlap=0,
            suffix=TILE_SUFFIX,
            depth="onepixel",
        )
    print(f"{view} {layer or 'map'} {pyramid}: {joined.width} x {joined.height}")
    return version


def _view_entry(area: Area, view: str, target: Path) -> dict:
    """Build one view's pyramid and return what the viewer needs to place it."""
    manifest = json.loads(manifest_path(area, view).read_text())
    return {
        "pyramid": _build_pyramid(area, view, target, manifest),
        **{layer: _build_pyramid(area, view, target, manifest, layer) for layer in LAYERS},
        "matrix": manifest["matrix"],
        "x_offset": manifest["x_offset"],
        "y_offset": manifest["y_offset"],
    }


def layer_key() -> dict:
    """Return what the viewer needs to lay the layers over the map: their tile size, and for
    each flowering tree the colors it wears and the months, from 1, it is in flower.
    """
    colors = layer_colors("bloom")
    return {
        "tile_px": LAYER_TILE_PX,
        "bloom": {
            kind: {"colors": [colors[kind], colors[f"{kind}_light"]], "months": BLOOM_MONTHS[kind]}
            for kind in BLOSSOM
        },
    }


def pyramids_of(views: dict) -> set[str]:
    """Return every pyramid the views name: each one's map and its layers."""
    return {entry[key] for entry in views.values() for key in PYRAMID_KEYS if key in entry}


def _write_indexes(area: Area, target: Path, views: dict) -> None:
    # Search, flow, and the metro are written in the default view, which is planned but
    # not rendered; the viewer converts them for the views it shows.
    manifest = json.loads(manifest_path(area).read_text())
    entries = search_index(area, manifest["x_offset"], manifest["y_offset"])
    (target / "search.json").write_text(json.dumps(entries, ensure_ascii=False))
    (target / "credits.json").write_text(json.dumps(landmark_credits(), ensure_ascii=False))
    flow = flow_lines(area, manifest["x_offset"], manifest["y_offset"])
    (target / "flow.json").write_text(json.dumps(flow))
    metro = metro_index(area, manifest["x_offset"], manifest["y_offset"])
    (target / "metro.json").write_text(json.dumps(metro, ensure_ascii=False))
    index = {**manifest, "views": views, "layers": layer_key()}
    (target / "manifest.json").write_text(json.dumps(index))
    print(f"{len(entries)} search entries")


def tile(area: Area) -> None:
    target = tiles_dir(area)
    if target.exists():
        shutil.rmtree(target)
    if not manifest_path(area).exists():
        plan_view(area, load_scene(area), DEFAULT_VIEW)
    views = {view: _view_entry(area, view, target) for view in RENDERED_VIEWS}
    _write_indexes(area, target, views)


def refresh_metro(area: Area) -> None:
    """Read the metro again from the downloads and write its index into a map already built.

    Nothing is drawn: the viewer lays the metro over the map, so a line that opens, or a new
    plan, needs no night's work. A map not built yet gets its index when it is built.
    """
    prepare_metro(area)
    target = tiles_dir(area) / "metro.json"
    if not (target.parent.exists() and manifest_path(area).exists()):
        print(f"metro: {area.name} is not built; its index is written when it is")
        return
    manifest = json.loads(manifest_path(area).read_text())
    metro = metro_index(area, manifest["x_offset"], manifest["y_offset"])
    target.write_text(json.dumps(metro, ensure_ascii=False))
    print(f"metro: {target}")


def _drop_old_pyramids(target: Path, views: dict) -> None:
    """Delete the pyramids no view points at, left behind when a view is built again."""
    current = pyramids_of(views)
    for pyramid in (target / PYRAMID_DIR).iterdir():
        if pyramid.is_dir() and pyramid.name not in current:
            shutil.rmtree(pyramid)


def build_inputs(area: Area) -> str:
    """Return what decides a view's tiles: what its frames are drawn from, and how they are
    tiled. A built view that records anything else is stale.
    """
    return f"{frames_fingerprint(area)}:{TILING}"


def _past(deadline: float | None) -> bool:
    return deadline is not None and time.time() >= deadline


def build(area: Area, only: list[str] | None = None, deadline: float | None = None) -> bool:
    """Render and tile one view at a time, then delete its frames, so the disk never holds
    more than the finished tiles and one view's frames. Returns whether the map is built.

    Stopped, it picks up at the first frame that is not on disk. Past the deadline, an epoch
    time, no frame and no pyramid starts; a pyramid already being written is finished. A
    view built from other data, by an older renderer, or tiled another way is built again,
    and until then the viewer keeps showing the one it has.
    """
    target = tiles_dir(area)
    target.mkdir(parents=True, exist_ok=True)
    record = target / VIEWS_RECORD
    views = json.loads(record.read_text()) if record.exists() else {}
    inputs = build_inputs(area)
    scene = None
    for view in only or RENDERED_VIEWS:
        if views.get(view, {}).get("inputs") == inputs:
            continue
        if _past(deadline):
            return False
        if scene is None:
            scene = load_scene(area)
            np.save(trees_path(area), scene.trees)
        if not _render_view(area, scene, view, deadline=deadline) or _past(deadline):
            print(f"{view}: stopped at the deadline; the next run carries on from here")
            return False
        views[view] = {**_view_entry(area, view, target), "inputs": inputs}
        record.write_text(json.dumps(views, indent=2) + "\n")
        shutil.rmtree(frames_dir(area, view))
    finished = all(views.get(view, {}).get("inputs") == inputs for view in RENDERED_VIEWS)
    if finished:
        if not manifest_path(area).exists():
            plan_view(area, scene or load_scene(area), DEFAULT_VIEW)
        _write_indexes(area, target, {view: views[view] for view in RENDERED_VIEWS})
        # Only now: until the manifest is rewritten, the viewer still reads the old ones.
        _drop_old_pyramids(target, views)
    return finished
