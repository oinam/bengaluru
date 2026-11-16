"""Stage 4: join the frames into a Deep Zoom pyramid and write the search index."""

import hashlib
import json
import shutil
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyvips
from pyproj import Transformer

from bengaluru.areas import Area
from bengaluru.detail import (
    DEFAULT_VIEW,
    LANDMARKS_PATH,
    PROJECTION,
    RENDERED_VIEWS,
    SPRITE_DIR,
    _render_view,
    frames_dir,
    load_scene,
    manifest_path,
    plan_view,
    trees_path,
)
from bengaluru.prepare import METRIC_CRS, derived_path

TILE_PX = 512
AREA_KINDS = {"city", "suburb", "town"}
LOCALITY_KINDS = {"village", "neighbourhood", "locality", "quarter", "hamlet"}
NOTABLE_KINDS = {"landmark", "university"}
# Names that label early whatever OSM calls their kind. None yet.
NOTABLE_NAMES: set[str] = set()
TILE_SUFFIX = ".webp[lossless=true,effort=4]"
PYRAMID_DIR = "pyramid"
VIEWS_RECORD = "views.json"
FLOW_SIMPLIFY_M = 6.0


def tiles_dir(area: Area) -> Path:
    return Path("out") / area.name / "tiles"


def pyramid_version(paths: list[Path], columns: int) -> str:
    """Return a short hash of everything that decides the tile bytes."""
    digest = hashlib.blake2b(f"{TILE_PX}:{TILE_SUFFIX}:{columns}".encode(), digest_size=5)
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def search_index(area: Area, x_offset: float, y_offset: float) -> list[dict]:
    """Return OSM names with their canvas positions, one entry per name and place."""
    a, b, d, e = PROJECTION.matrix
    pois = gpd.read_file(derived_path(area), layer="pois")
    landmarks = landmark_positions(area)
    entries = {}
    for row in pois.itertuples():
        x, y = row.geometry.x, row.geometry.y
        px = round(a * x + b * y + x_offset)
        py = round(d * x + e * y + y_offset)
        if row.name in landmarks:
            continue
        key = (row.name, px // 200, py // 200)
        kind = row.kind or ""
        entries[key] = {
            "name": row.name,
            "kind": kind,
            "x": px,
            "y": py,
            "tier": _tier(row.name, kind),
        }
    for name, (x, y) in landmarks.items():
        px = round(a * x + b * y + x_offset)
        py = round(d * x + e * y + y_offset)
        entries[(name, "landmark")] = {
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
    a, b, d, e = PROJECTION.matrix
    ways = gpd.read_file(derived_path(area), layer="waterways")
    lines = []
    for row in ways.itertuples():
        parts = (
            row.geometry.geoms if row.geometry.geom_type == "MultiLineString" else [row.geometry]
        )
        for part in parts:
            points = [
                [round(a * x + b * y + x_offset), round(d * x + e * y + y_offset)]
                for x, y in part.simplify(FLOW_SIMPLIFY_M).coords
            ]
            line = {"width": round(row.width_m), "points": points}
            if row.waterway == "river" and isinstance(row.name, str) and len(points) > 1:
                line["name"] = row.name
            lines.append(line)
    return lines


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


def _build_pyramid(area: Area, view: str, target: Path, manifest: dict) -> str:
    """Write one view's tiles and return its version."""
    columns, rows = manifest["columns"], manifest["rows"]
    paths = [
        frames_dir(area, view) / f"{row:03d}_{column:03d}.png"
        for row in range(rows)
        for column in range(columns)
    ]
    images = [pyvips.Image.new_from_file(str(path), access="sequential") for path in paths]
    joined = pyvips.Image.arrayjoin(images, across=columns)
    version = pyramid_version(paths, columns)
    pyramid = target / PYRAMID_DIR / version
    # A build stopped partway through leaves an unfinished pyramid; start it again.
    shutil.rmtree(pyramid, ignore_errors=True)
    pyramid.mkdir(parents=True)
    joined.dzsave(
        str(pyramid / area.name),
        tile_size=TILE_PX,
        overlap=0,
        suffix=TILE_SUFFIX,
        depth="onepixel",
    )
    print(f"{view} {pyramid}: {joined.width} x {joined.height}")
    return version


def _view_entry(area: Area, view: str, target: Path) -> dict:
    """Build one view's pyramid and return what the viewer needs to place it."""
    manifest = json.loads(manifest_path(area, view).read_text())
    return {
        "pyramid": _build_pyramid(area, view, target, manifest),
        "matrix": manifest["matrix"],
        "x_offset": manifest["x_offset"],
        "y_offset": manifest["y_offset"],
    }


def _write_indexes(area: Area, target: Path, views: dict) -> None:
    # Search and flow are written in the default view, which is planned but not rendered;
    # the viewer converts them for the views it shows.
    manifest = json.loads(manifest_path(area).read_text())
    entries = search_index(area, manifest["x_offset"], manifest["y_offset"])
    (target / "search.json").write_text(json.dumps(entries, ensure_ascii=False))
    (target / "credits.json").write_text(json.dumps(landmark_credits(), ensure_ascii=False))
    flow = flow_lines(area, manifest["x_offset"], manifest["y_offset"])
    (target / "flow.json").write_text(json.dumps(flow))
    (target / "manifest.json").write_text(json.dumps({**manifest, "views": views}))
    print(f"{len(entries)} search entries")


def tile(area: Area) -> None:
    target = tiles_dir(area)
    if target.exists():
        shutil.rmtree(target)
    if not manifest_path(area).exists():
        plan_view(area, load_scene(area), DEFAULT_VIEW)
    views = {view: _view_entry(area, view, target) for view in RENDERED_VIEWS}
    _write_indexes(area, target, views)


def _past(deadline: float | None) -> bool:
    return deadline is not None and time.time() >= deadline


def build(area: Area, only: list[str] | None = None, deadline: float | None = None) -> bool:
    """Render and tile one view at a time, then delete its frames, so the disk never holds
    more than the finished tiles and one view's frames. Returns whether the map is built.

    Stopped, it picks up at the first frame that is not on disk. Past the deadline, an epoch
    time, no frame and no pyramid starts; a pyramid already being written is finished.
    """
    target = tiles_dir(area)
    target.mkdir(parents=True, exist_ok=True)
    record = target / VIEWS_RECORD
    views = json.loads(record.read_text()) if record.exists() else {}
    scene = None
    for view in only or RENDERED_VIEWS:
        if view in views:
            continue
        if _past(deadline):
            return False
        if scene is None:
            scene = load_scene(area)
            np.save(trees_path(area), scene.trees)
        if not _render_view(area, scene, view, deadline=deadline) or _past(deadline):
            print(f"{view}: stopped at the deadline; the next run carries on from here")
            return False
        views[view] = _view_entry(area, view, target)
        record.write_text(json.dumps(views, indent=2) + "\n")
        shutil.rmtree(frames_dir(area, view))
    finished = all(view in views for view in RENDERED_VIEWS)
    if finished:
        if not manifest_path(area).exists():
            plan_view(area, scene or load_scene(area), DEFAULT_VIEW)
        _write_indexes(area, target, {view: views[view] for view in RENDERED_VIEWS})
    return finished
