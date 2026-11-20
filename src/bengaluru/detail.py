"""Near-final styling, for one frame or a whole area, a frame at a time."""

import datetime as dt
import hashlib
import itertools
import json
import math
import multiprocessing
import shutil
import time
import zlib
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import shapely
import shapely.affinity
from affine import Affine
from PIL import Image, ImageDraw
from pyproj import Transformer
from rasterio.features import rasterize
from shapely.affinity import affine_transform
from shapely.geometry import LineString, Point
from shapely.geometry.polygon import orient
from shapely.ops import substring

from bengaluru.areas import Area
from bengaluru.fetch import raw_dir
from bengaluru.osm import load_features
from bengaluru.palettes import BLOSSOM, LIGHTS, PALETTE, SLOT, SLOTS, lookup
from bengaluru.prepare import METRIC_CRS, derived_path
from bengaluru.render import (
    LINED_ROADS,
    PROJECTION_B,
    ROAD_ORDER,
    ROAD_SLOTS,
    SEED,
    Layers,
    Projection,
    Viewport,
    centered_viewport,
    full_viewport,
    load_layers,
    parts,
)

# Areas whose detail frame is centered somewhere other than their own center, as (lon, lat).
CROP_CENTERS: dict[str, tuple[float, float]] = {}
CROP_PX = 2048
PROJECTION = PROJECTION_B
# The chosen projection turned in 15 degree steps, named for the turn from the default.
# The names and the 15 degree steps come from the Manipur map, whose viewer reads them.
VIEWS = {str(turn): (45.0 + turn) % 360 for turn in range(0, 360, 15)}
# The views the site shows: north up first, then each quarter turn clockwise.
RENDERED_VIEWS = ("315", "45", "135", "225")
# The frame links, search, and flow lines are written in. It is planned, not rendered.
DEFAULT_VIEW = "0"
# The views the detail frame is drawn in: north up, as the site opens, and the 45 degree turn.
DETAIL_VIEWS = ("315", "0")
SPRITE_DIR = Path("assets/sprites")
LANDMARKS_PATH = Path("assets/landmarks.json")
TRANSPARENT = 255
# Kept in a view's frame folder: a hash of what its frames were drawn from.
FINGERPRINT = "FINGERPRINT"

_EXTRA = (
    *(f"roof_shade_{index}" for index in range(6)),
    "canopy_light",
    "canopy_dark",
    "water_light",
    "water_dark",
    "shadow_built",
    *BLOSSOM,
    *(f"{name}_light" for name in BLOSSOM),
    "window_glow",
    "window_glow_shade",
    "lamp",
    "lamp_shade",
    "lamp_deck",
)
DETAIL_SLOT = {**SLOT, **{name: len(SLOTS) + index for index, name in enumerate(_EXTRA)}}

GROUND_CLASSES = ("tree", "shrub", "grass", "built", "bare", "wetland")
# WorldCover classes drawn as another: open water is OSM's to draw, and what it calls
# cropland in this city is open grass, not fields.
DRAWN_AS = {"water": "wetland", "crop": "grass"}
SPECKLE = {
    "tree": "canopy_dark",
    "shrub": "tree",
    "grass": "shrub",
    "built": "bare",
    "bare": "shadow_built",
    "wetland": "grass",
}
SHADOW = {
    "tree": "canopy_dark",
    "shrub": "tree",
    "grass": "shrub",
    "built": "shadow_built",
    "bare": "shadow_built",
    "wetland": "shrub",
    "water": "water_dark",
    "road_major": "background",
    "road_minor": "road_major",
    "road_track": "shadow_built",
    "road_line": "road_minor",
    "water_dark": "background",
    "water_light": "water",
    "canopy_dark": "background",
    "shadow_built": "road_minor",
    "lamp": "lamp_shade",
}
# What shines at night, by the light it shines with. By day each is the color of what it
# stands on: a window on a sunlit wall or a shaded one, a lamp on a footpath in sun or shade
# or on a flyover's parapet.
GLOW = {
    "window_glow": "window",
    "window_glow_shade": "window",
    "lamp": "lamp",
    "lamp_shade": "lamp",
    "lamp_deck": "lamp",
}
BY_DAY = {
    "window_glow": "road_major",
    "window_glow_shade": "background",
    "lamp": "road_track",
    "lamp_shade": "shadow_built",
    "lamp_deck": "wall_lit",
}
# A frame is kept as the map every hour and season shares, and as these, each a picture of
# the same size holding only its own pixels, for the viewer to lay over the map. The bloom
# is clear elsewhere. The lights are black elsewhere, to be added as light is, and so the
# tiler can pool them as it shrinks them, which a clear part would spoil.
LAYERS = ("bloom", "lights")
CLEAR_LAYERS = ("bloom",)
# Of a hundred windows, how many have someone home at night.
WINDOWS_LIT_PERCENT = 42
LAMP_EVERY_M = 30.0
TREE_ODDS = {
    "tree": 0.72,
    "shrub": 0.18,
    "wetland": 0.08,
    "grass": 0.04,
    "built": 0.03,
    "crop": 0.01,
}
TREE_SPACING_M = 6.5
# The canopy radii the tree sprites are drawn in, and how many shapes of tree there are.
RADIUS_PX = (6, 7, 8, 9, 10, 12)
TREE_SHAPES = 12
# Flowering trees stand in groves, as avenues and parks plant them: of the squares this
# wide, this share is in bloom with one kind of tree, and in those this share of the
# trees flowers. The map shows every kind in bloom at once, which no month does.
GROVE_M = 100.0
GROVES_IN_BLOOM = 0.13
TREES_IN_BLOOM = 0.5
MAJOR_ROADS = [name for name, slot in ROAD_SLOTS.items() if slot == "road_major"]
SUN_U, SUN_D = 0.94, -0.34
# Bengaluru builds flat concrete terraces. Of its small rectangular buildings this share
# keeps a pitched roof, and of its flat roofs this share is bare concrete, not a color.
PITCHED_PERCENT = 9
CONCRETE_PERCENT = 85
# Roof colors by palette slot: the ones a tin roof comes in, and bare concrete.
TIN_ROOFS = (0, 1, 2, 3, 5)
CONCRETE_ROOF = 4
LOW_HOUSE_MAX_M2 = 160
LOW_HOUSE_MAX_M = 4.4
VERANDA_M = 1.5
VERANDA_INNER_M = 2.6
VERANDA_OUTER_M = 2.1
WATER_TANK_MIN_M2 = 25
SHADOW_PER_HEIGHT = 0.75
STOREY_M = 3.2
BLUR_RADIUS_PX = 16
FOOTPATH_M = 1.8
RAIL_BED_M = 4.4
RAIL_TIE_EVERY_M = 4.0
# The metro's viaduct: the top of its deck, the deck's depth, half the width under one
# track, and the distance between piers.
VIADUCT_M = 9.0
VIADUCT_DECK_M = 1.8
VIADUCT_HALF_M = 2.6
VIADUCT_SPAN_M = 24.0
# A road's flyover: the depth of its deck, the height of its parapets, the distance between
# its piers, and the clear height under which a span stands on a wall, as a ramp does, and
# not on piers. A deck this wide or wider stands on two columns, each this far in from an
# edge, where they show from the side; a narrower one stands on one.
FLYOVER_DECK_M = 1.5
FLYOVER_PARAPET_M = 1.0
FLYOVER_SPAN_M = 24.0
FLYOVER_WALL_M = 3.0
FLYOVER_TWIN_M = 10.0
FLYOVER_COLUMN_IN_M = 1.5
# Two decks within this height of each other, where they overlap, are one stretch of road:
# carriageways side by side, or a ramp joining. No parapet stands between them.
FLYOVER_BESIDE_M = 2.5
LANDMARK_CLEARING_M = 16.0
CEMETERY_ROW_M = 5.5
CEMETERY_GRAVE_M = 4.0
FRAME_PX = 2048
# Wider than the tallest building's lift, the ground blur, and any sprite, so frames join exactly.
APRON_PX = 256
WORKERS = 6


def _mix(first: str, second: str, amount: float) -> str:
    a = bytes.fromhex(first.lstrip("#"))
    b = bytes.fromhex(second.lstrip("#"))
    return "#" + bytes(round(x + (y - x) * amount) for x, y in zip(a, b, strict=True)).hex()


def detail_colors() -> dict[str, str]:
    """Extend the monsoon palette with shades derived from its own colors."""
    colors = dict(PALETTE)
    for index in range(6):
        colors[f"roof_shade_{index}"] = _mix(PALETTE[f"roof_{index}"], PALETTE["background"], 0.32)
    colors["canopy_light"] = _mix(PALETTE["grass"], PALETTE["crop"], 0.35)
    colors["canopy_dark"] = _mix(PALETTE["tree"], PALETTE["background"], 0.5)
    colors["water_light"] = _mix(PALETTE["water"], "#ffffff", 0.42)
    colors["water_dark"] = _mix(PALETTE["water"], PALETTE["background"], 0.42)
    colors["shadow_built"] = _mix(PALETTE["bare"], PALETTE["background"], 0.38)
    for name, color in BLOSSOM.items():
        colors[name] = color
        colors[f"{name}_light"] = _mix(color, "#ffffff", 0.4)
    for name, by_day in BY_DAY.items():
        colors[name] = colors[by_day]
    return colors


def detail_lookup() -> bytes:
    """Return the palette of a picture on its own: by day, with every tree in flower."""
    return lookup(detail_colors(), DETAIL_SLOT)


def base_lookup() -> bytes:
    """Return the palette of the map every hour and season shares: by day, no tree in flower."""
    colors = detail_colors()
    for name in BLOSSOM:
        colors[name] = colors["shrub"]
        colors[f"{name}_light"] = colors["canopy_light"]
    return lookup(colors, DETAIL_SLOT)


def layer_colors(layer: str) -> dict[str, str]:
    """Return the slots a layer shows, each with its color there."""
    if layer == "lights":
        return {name: LIGHTS[light] for name, light in GLOW.items()}
    colors = detail_colors()
    return {name: colors[name] for kind in BLOSSOM for name in (kind, f"{kind}_light")}


def hash_field(xs: np.ndarray, ys: np.ndarray, salt: int) -> np.ndarray:
    """Return deterministic noise in [0, 1) anchored to global pixel coordinates."""
    value = (xs.astype("int64").astype("uint64") * np.uint64(2654435761)) + (
        ys.astype("int64").astype("uint64") * np.uint64(2246822519)
    )
    value += np.uint64(salt * 3266489917 + 374761393)
    value ^= value >> np.uint64(15)
    value *= np.uint64(3266489917)
    value ^= value >> np.uint64(13)
    return (value & np.uint64(65535)).astype("float32") / 65536.0


def _global_grid(view: Viewport) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.mgrid[0 : view.height, 0 : view.width]
    return xs - int(view.x_offset), ys - int(view.y_offset)


def _matrix(view: Viewport) -> tuple[float, ...]:
    a, b, d, e = PROJECTION.matrix
    return (a, b, d, e, view.x_offset, view.y_offset)


def _burn(shapes: list, view: Viewport, fill: int = 0) -> np.ndarray:
    matrix = _matrix(view)
    placed = [
        (affine_transform(geometry, matrix), value)
        for geometry, value in shapes
        if geometry is not None and not geometry.is_empty
    ]
    if not placed:
        return np.full((view.height, view.width), fill, dtype="uint8")
    return rasterize(
        placed,
        out_shape=(view.height, view.width),
        transform=Affine.identity(),
        fill=fill,
        dtype="uint8",
    )


def _box_blur(array: np.ndarray, radius: int) -> np.ndarray:
    """Return a box blur of the array, computed from a summed-area table."""
    table = np.zeros((array.shape[0] + 1, array.shape[1] + 1), dtype="float64")
    table[1:, 1:] = array.cumsum(0).cumsum(1)
    height, width = array.shape
    rows = np.arange(height)
    cols = np.arange(width)
    top = np.clip(rows - radius, 0, height)
    bottom = np.clip(rows + radius + 1, 0, height)
    left = np.clip(cols - radius, 0, width)
    right = np.clip(cols + radius + 1, 0, width)
    total = (
        table[bottom[:, None], right[None, :]]
        - table[top[:, None], right[None, :]]
        - table[bottom[:, None], left[None, :]]
        + table[top[:, None], left[None, :]]
    )
    area = (bottom - top)[:, None] * (right - left)[None, :]
    return (total / area).astype("float32")


def _paint_ground(layers: Layers, view: Viewport) -> np.ndarray:
    """Soften WorldCover's 10 m cells into rounded, speckled ground."""
    shapes = []
    for row in layers.ground.itertuples():
        name = DRAWN_AS.get(row.ground, row.ground)
        if name in GROUND_CLASSES:
            shapes.append((row.geometry, GROUND_CLASSES.index(name) + 1))
    labels = _burn(shapes, view)
    # Each pixel takes the class that fills most of the ground around it.
    chosen = np.stack(
        [
            _box_blur((labels == index + 1).astype("float32"), BLUR_RADIUS_PX)
            for index in range(len(GROUND_CLASSES))
        ]
    ).argmax(axis=0)
    inside = _burn([(layers.patch, 1)], view).astype(bool)

    canvas = np.full((view.height, view.width), DETAIL_SLOT["background"], dtype="uint8")
    base = np.array([DETAIL_SLOT[name] for name in GROUND_CLASSES], dtype="uint8")
    canvas[inside] = base[chosen[inside]]
    speckle = np.array([DETAIL_SLOT[SPECKLE[name]] for name in GROUND_CLASSES], dtype="uint8")
    xs, ys = _global_grid(view)
    chance = 0.05 + hash_field(xs // 9, ys // 9, 12) * 0.17
    marked = inside & (hash_field(xs, ys, 13) < chance)
    canvas[marked] = speckle[chosen[marked]]
    return canvas


def _paint_cemetery(canvas: np.ndarray, part: gpd.GeoDataFrame, view: Viewport) -> None:
    """Draw mown grass, a clipped hedge, and rows of grave markers."""
    mask = _burn([(geometry, 1) for geometry in part.geometry], view).astype(bool)
    canvas[mask] = DETAIL_SLOT["grass"]
    interior = mask.copy()
    for axis, shift in ((0, 3), (0, -3), (1, 3), (1, -3)):
        interior &= np.roll(mask, shift, axis=axis)
    canvas[mask & ~interior] = DETAIL_SLOT["tree"]
    for geometry in part.geometry:
        for polygon in parts(geometry):
            center, u, v, length, width = _ground_axes(polygon)
            usable = polygon.buffer(-3.0)
            shapely.prepare(usable)
            along = np.arange(-length / 2, length / 2, CEMETERY_GRAVE_M)
            across = np.arange(-width / 2, width / 2, CEMETERY_ROW_M)
            grid_u, grid_v = np.meshgrid(along, across)
            xs = center[0] + u[0] * grid_u.ravel() + v[0] * grid_v.ravel()
            ys = center[1] + u[1] * grid_u.ravel() + v[1] * grid_v.ravel()
            inside = shapely.contains_xy(usable, xs, ys)
            for x, y in zip(xs[inside], ys[inside], strict=True):
                col, row = _project(view, x, y, 0)
                if 2 <= col < view.width - 2 and 2 <= row < view.height - 2:
                    canvas[row - 1, col - 1 : col + 2] = DETAIL_SLOT["wall_lit"]
                    canvas[row, col - 1 : col + 2] = DETAIL_SLOT["wall_shade"]


def _paint_surfaces(canvas: np.ndarray, surfaces: gpd.GeoDataFrame, view: Viewport) -> None:
    cemeteries = surfaces[surfaces.kind == "cemetery"]
    if not cemeteries.empty:
        _paint_cemetery(canvas, cemeteries, view)
    for kind, slot in (("pitch", "grass"), ("paved", "road_minor")):
        part = surfaces[surfaces.kind == kind]
        mask = _burn([(geometry, 1) for geometry in part.geometry], view).astype(bool)
        canvas[mask] = DETAIL_SLOT[slot]


def _water_geometry(layers: Layers) -> list:
    rivers = layers.waterways.geometry.buffer(layers.waterways.width_m / 2)
    return [*layers.water.geometry.values, *rivers.intersection(layers.patch).values]


def _paint_water(canvas: np.ndarray, layers: Layers, view: Viewport) -> None:
    water = _water_geometry(layers)
    banks = [(shapely.intersection(g.buffer(2.5), layers.patch), 1) for g in water]
    canvas[_burn(banks, view).astype(bool)] = DETAIL_SLOT["bare"]
    wet = _burn([(g, 1) for g in water], view).astype(bool)
    canvas[wet] = DETAIL_SLOT["water"]

    xs, ys = _global_grid(view)
    ripple = (ys % 6 == 0) & (xs % 11 < 6) & (hash_field(xs // 11, ys, 21) < 0.3)
    canvas[wet & ripple] = DETAIL_SLOT["water_light"]
    above = np.roll(wet, 2, axis=0)
    above[:2, :] = False
    canvas[wet & ~above] = DETAIL_SLOT["water_dark"]


def _dashes(line: LineString, on_m: float = 4.0, off_m: float = 6.0) -> list:
    parts = []
    position = 0.0
    while position < line.length:
        parts.append(substring(line, position, min(position + on_m, line.length)).buffer(0.45))
        position += on_m + off_m
    return parts


def _paint_roads(canvas: np.ndarray, layers: Layers, view: Viewport) -> None:
    roads = layers.roads.explode(index_parts=False)
    roads = roads[roads.geometry.geom_type == "LineString"]
    if "raised" in roads:
        # A flyover's road is its deck, drawn among the buildings.
        roads = roads[~roads.raised.astype(bool)]
    major = roads[roads.road_class.isin(MAJOR_ROADS)]
    walks = major.geometry.buffer(major.width_m / 2 + FOOTPATH_M, cap_style="flat")
    walk_mask = _burn([(g.intersection(layers.patch), 1) for g in walks], view).astype(bool)
    canvas[walk_mask] = DETAIL_SLOT["road_track"]

    shapes = []
    for road_class in ROAD_ORDER:
        part = roads[roads.road_class == road_class]
        slot = DETAIL_SLOT[ROAD_SLOTS.get(road_class, "road_minor")]
        bodies = part.geometry.buffer(part.width_m / 2, cap_style="flat")
        shapes.extend((g.intersection(layers.patch), slot) for g in bodies)
    burned = _burn(shapes, view)
    painted = burned > 0
    canvas[painted] = burned[painted]

    majors = burned == DETAIL_SLOT["road_major"]
    interior = majors.copy()
    for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
        interior &= np.roll(majors, shift, axis=axis)
    canvas[majors & ~interior] = DETAIL_SLOT["road_minor"]

    lined = roads[roads.road_class.isin(LINED_ROADS)]
    marks = [(g.intersection(layers.patch), 1) for line in lined.geometry for g in _dashes(line)]
    canvas[_burn(marks, view).astype(bool)] = DETAIL_SLOT["road_line"]
    _paint_lamps(canvas, major, view)


def _paint_lamps(canvas: np.ndarray, major: gpd.GeoDataFrame, view: Viewport) -> None:
    """Stand a street lamp on the footpath every so often along each major road, on
    alternate sides. By day a lamp is the footpath's own color, so only the night shows it.
    """
    for line, width in zip(major.geometry, major.width_m, strict=True):
        count = int(line.length // LAMP_EVERY_M)
        if count < 1:
            continue
        along = (np.arange(count) + 0.5) * LAMP_EVERY_M
        here = shapely.get_coordinates(shapely.line_interpolate_point(line, along))
        ahead = shapely.get_coordinates(shapely.line_interpolate_point(line, along + 1.0))
        heading = ahead - here
        heading /= np.maximum(np.linalg.norm(heading, axis=1, keepdims=True), 1e-9)
        aside = np.where(np.arange(count) % 2, 1.0, -1.0) * (width / 2 + FOOTPATH_M / 2)
        x, y = _screen(view, here[:, 0] - heading[:, 1] * aside, here[:, 1] + heading[:, 0] * aside)
        x, y = np.rint(x).astype(int), np.rint(y).astype(int)
        for dx, dy in ((0, 0), (1, 0), (0, -1), (1, -1)):
            px, py = x + dx, y + dy
            inside = (px >= 0) & (px < view.width) & (py >= 0) & (py < view.height)
            px, py = px[inside], py[inside]
            footpath = canvas[py, px] == DETAIL_SLOT["road_track"]
            canvas[py[footpath], px[footpath]] = DETAIL_SLOT["lamp"]


def _paint_rails(canvas: np.ndarray, rails: gpd.GeoDataFrame, patch, view: Viewport) -> None:
    """Draw track on the ground: a bed of ballast, its ties, and the line of the rails."""
    lines = rails.explode(index_parts=False).geometry
    lines = [line for line in lines if line.geom_type == "LineString"]
    if not lines:
        return
    beds = [
        (line.buffer(RAIL_BED_M / 2, cap_style="flat").intersection(patch), 1) for line in lines
    ]
    canvas[_burn(beds, view).astype(bool)] = DETAIL_SLOT["road_track"]
    ties = [
        (substring(line, at, at + 1.0).buffer(1.6, cap_style="flat").intersection(patch), 1)
        for line in lines
        for at in np.arange(0.0, line.length, RAIL_TIE_EVERY_M)
    ]
    canvas[_burn(ties, view).astype(bool)] = DETAIL_SLOT["shadow_built"]
    tracks = [(line.buffer(0.5, cap_style="flat").intersection(patch), 1) for line in lines]
    canvas[_burn(tracks, view).astype(bool)] = DETAIL_SLOT["background"]


def _turn() -> tuple[float, float]:
    """Return the cosine and sine of the view's rotation."""
    angle = math.radians(PROJECTION.rotation_deg)
    return math.cos(angle), math.sin(angle)


def _sun_offset(length: float) -> tuple[float, float]:
    """Return the world offset of a shadow of the given ground length."""
    cos, sin = _turn()
    return (
        (SUN_U * cos - SUN_D * sin) * length,
        (SUN_U * sin + SUN_D * cos) * length,
    )


def _depth(x: float, y: float) -> float:
    return PROJECTION.depth(x, y)


def _project(view: Viewport, x: float, y: float, z: float) -> tuple[int, int]:
    a, b, d, e = PROJECTION.matrix
    return (
        round(a * x + b * y + view.x_offset),
        round(d * x + e * y + view.y_offset - z * PROJECTION.lift),
    )


def _hash(seed: int, text: str, modulo: int) -> int:
    return zlib.crc32(f"{seed}:{text}".encode()) % modulo


def _normal(p: np.ndarray, q: np.ndarray) -> tuple[float, float]:
    """Return the outward normal of a counterclockwise edge in the view frame (u, depth)."""
    dx, dy = q - p
    cos, sin = _turn()
    return (cos * dy - sin * dx, -sin * dy - cos * dx)


def _windows(draw, view, p, q, top, lit, shutters: bool) -> None:
    length = float(np.linalg.norm(q - p))
    count = int(length / 3.0)
    if count < 1:
        return
    color = DETAIL_SLOT["road_major"] if lit else DETAIL_SLOT["background"]
    glow = DETAIL_SLOT["window_glow" if lit else "window_glow_shade"]
    start = 0
    if shutters:
        shutter = DETAIL_SLOT["road_minor"] if lit else DETAIL_SLOT["road_major"]
        for index in range(count):
            t0 = (index + 0.15) / count
            t1 = (index + 0.85) / count
            a = p + (q - p) * t0
            b = p + (q - p) * t1
            draw.polygon(
                [
                    _project(view, *a, 0.2),
                    _project(view, *b, 0.2),
                    _project(view, *b, 2.5),
                    _project(view, *a, 2.5),
                ],
                fill=shutter,
            )
        start = 1
    storey = start
    while 1.7 + STOREY_M * storey + 1.0 < top:
        z = 1.7 + STOREY_M * storey
        for index in range(count):
            point = p + (q - p) * ((index + 0.5) / count)
            x, y = _project(view, *point, z)
            home = _hash(SEED, f"{point[0]:.1f}/{point[1]:.1f}/{storey}", 100) < WINDOWS_LIT_PERCENT
            draw.rectangle([x - 1, y - 2, x, y], fill=glow if home else color)
        storey += 1


def _paint_walls(draw, view, ring, top, gable_top, shutters, windows) -> None:
    """Draw camera-facing walls; ring is counterclockwise and closed."""
    edges = []
    for index in range(len(ring) - 1):
        p, q = ring[index], ring[index + 1]
        normal_u, normal_depth = _normal(p, q)
        length = float(np.linalg.norm(q - p))
        if normal_depth < 0 and length > 0:
            edges.append((-_depth(*((p + q) / 2)), index, p, q, normal_u < 0))
    outline = DETAIL_SLOT["background"]
    edges.sort(key=lambda edge: edge[0])
    visible = {edge[1] for edge in edges}
    for _, index, p, q, lit in edges:
        fill = DETAIL_SLOT["wall_lit" if lit else "wall_shade"]
        quad = [
            _project(view, *p, 0),
            _project(view, *q, 0),
            _project(view, *q, top),
            _project(view, *p, top),
        ]
        draw.polygon(quad, fill=fill)
        apex = gable_top.get(index) if gable_top else None
        if apex is not None:
            middle = (p + q) / 2
            draw.polygon(
                [
                    _project(view, *p, top),
                    _project(view, *q, top),
                    _project(view, *middle, apex),
                ],
                fill=fill,
            )
        if windows:
            _windows(draw, view, p, q, top, lit, shutters)
        draw.line([_project(view, *p, 0), _project(view, *q, 0)], fill=outline)
    count = len(ring) - 1
    for index in range(count):
        if (index in visible) != ((index - 1) % count in visible):
            draw.line(
                [_project(view, *ring[index], 0), _project(view, *ring[index], top)], fill=outline
            )


def _classify(area: float, height: float, rectangular: bool, building_id: str, seed: int) -> str:
    if area >= 600 and height < 9.5:
        return "shed" if rectangular else "flat"
    if height >= 11:
        return "block"
    if 100 <= area < 600 and rectangular and _hash(seed, building_id + "s", 100) < 45:
        return "shop"
    if rectangular and _hash(seed, building_id + "p", 100) < PITCHED_PERCENT:
        return "house"
    return "flat"


def _long_side_corners(polygon) -> np.ndarray:
    """Return the footprint's rectangle corners, starting along a long side."""
    corners = np.array(shapely.minimum_rotated_rectangle(polygon).exterior.coords)[:4]
    if np.linalg.norm(corners[1] - corners[0]) < np.linalg.norm(corners[2] - corners[1]):
        corners = np.roll(corners, -1, axis=0)
    return corners


def _paint_pitched(draw, view, polygon, height, slot, shade, windows, ribbed) -> None:
    a, b, c, d = _long_side_corners(polygon)
    width = float(np.linalg.norm(c - b))
    rise = float(np.clip(width * 0.2, 0.8, 3.0))
    eave = max(2.4, height - rise)
    ridge = eave + rise
    left, right = (a + d) / 2, (b + c) / 2

    ring = [a, b, c, d, a]
    area2 = sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(4))
    if area2 < 0:
        ring.reverse()
    closed = np.array(ring)
    # Short edges carry the gables; in the reversed ring they stay at odd positions.
    gables = dict.fromkeys((1, 3), ridge)
    _paint_walls(draw, view, closed, eave, gables, False, windows)

    outline = DETAIL_SLOT["background"]
    faces = [(a, b, right, left), (d, c, right, left)]
    faces.sort(key=lambda face: -_depth(*((face[0] + face[1]) / 2)))
    for near0, near1, top1, top0 in faces:
        outward = (near0 + near1) / 2 - (left + right) / 2
        cos, sin = _turn()
        facing_left = cos * outward[0] + sin * outward[1] < 0
        fill = slot if facing_left else shade
        draw.polygon(
            [
                _project(view, *near0, eave),
                _project(view, *near1, eave),
                _project(view, *top1, ridge),
                _project(view, *top0, ridge),
            ],
            fill=fill,
            outline=outline,
        )
        if ribbed and facing_left:
            span = float(np.linalg.norm(near1 - near0))
            for step in range(1, int(span / 1.6)):
                t = step / int(span / 1.6)
                draw.line(
                    [
                        _project(view, *(near0 + (near1 - near0) * t), eave),
                        _project(view, *(top0 + (top1 - top0) * t), ridge),
                    ],
                    fill=shade,
                )


def _paint_low_house(draw, view, polygon, height, slot, shade) -> None:
    """Draw a low tin house with a veranda along its near long side."""
    _paint_pitched(draw, view, polygon, min(height, LOW_HOUSE_MAX_M), slot, shade, True, True)
    a, b, c, d = _long_side_corners(polygon)
    if _depth(*((a + b) / 2)) > _depth(*((c + d) / 2)):
        a, b, c, d = c, d, a, b
    out = (a - d) / np.linalg.norm(a - d) * VERANDA_M
    draw.polygon(
        [
            _project(view, *a, VERANDA_INNER_M),
            _project(view, *b, VERANDA_INNER_M),
            _project(view, *(b + out), VERANDA_OUTER_M),
            _project(view, *(a + out), VERANDA_OUTER_M),
        ],
        fill=shade,
        outline=DETAIL_SLOT["background"],
    )
    for t in np.linspace(0.08, 0.92, 4):
        post = a + (b - a) * t + out
        draw.line(
            [_project(view, *post, 0), _project(view, *post, VERANDA_OUTER_M)],
            fill=DETAIL_SLOT["wall_shade"],
        )


def _courtyard_box(image, view, polygon, height) -> tuple[int, int, int, int] | None:
    """Return the part of the image the footprint's holes cover, from the ground to the roof."""
    points = [
        _project(view, x, y, z)
        for hole in polygon.interiors
        for x, y in hole.coords
        for z in (0, height)
    ]
    if not points:
        return None
    xs, ys = zip(*points, strict=True)
    box = (
        max(min(xs) - 1, 0),
        max(min(ys) - 1, 0),
        min(max(xs) + 2, image.width),
        min(max(ys) + 2, image.height),
    )
    return box if box[0] < box[2] and box[1] < box[3] else None


def _paint_courtyards(image, view, polygon, height, behind, box, shutters, windows) -> None:
    """Open the roof over the footprint's holes, down to what stood there before it.

    `behind` is the image inside `box` before the building was drawn. Through each opening
    go the inner walls that face the camera and, below them, the courtyard's floor.
    """
    local = Viewport(behind.width, behind.height, view.x_offset - box[0], view.y_offset - box[1])
    opening = Image.new("L", behind.size, 0)
    floor = Image.new("L", behind.size, 0)
    for hole in polygon.interiors:
        ImageDraw.Draw(opening).polygon(
            [_project(local, x, y, height) for x, y in hole.coords], fill=255
        )
        ImageDraw.Draw(floor).polygon([_project(local, x, y, 0) for x, y in hole.coords], fill=255)
    layer = Image.new(image.mode, behind.size, DETAIL_SLOT["wall_shade"])
    layer.paste(behind, (0, 0), floor)
    walls = ImageDraw.Draw(layer)
    for hole in polygon.interiors:
        # A hole's ring runs clockwise, so the walls drawn are the ones that face into it.
        _paint_walls(walls, local, np.array(hole.coords), height, None, shutters, windows)
    image.paste(layer, (box[0], box[1]), opening)


def _paint_flat(image, draw, view, polygon, height, slot, shade, kind, building_id, seed) -> None:
    polygon = orient(polygon, 1.0)
    ring = np.array(polygon.exterior.coords)
    shutters, windows = kind == "shop", kind in ("flat", "shop", "block")
    box = _courtyard_box(image, view, polygon, height)
    behind = image.crop(box) if box else None
    _paint_walls(draw, view, ring, height, None, shutters, windows)
    outline = DETAIL_SLOT["background"]
    points = [_project(view, x, y, height) for x, y in ring]
    draw.polygon(points, fill=DETAIL_SLOT["wall_lit"], outline=outline)
    inner = polygon.buffer(-0.7, join_style="mitre")
    if not inner.is_empty and inner.geom_type == "Polygon":
        draw.polygon(
            [_project(view, x, y, height) for x, y in inner.exterior.coords],
            fill=slot,
            outline=shade,
        )
    if behind is not None:
        _paint_courtyards(image, view, polygon, height, behind, box, shutters, windows)
    for hole in polygon.interiors:
        draw.line([_project(view, x, y, height) for x, y in hole.coords], fill=outline)
    if polygon.area >= WATER_TANK_MIN_M2 and _hash(seed, building_id + "t", 3) < 2:
        center = polygon.representative_point()
        x, y = _project(view, center.x, center.y, height)
        draw.rectangle([x - 2, y - 6, x + 2, y - 1], fill=DETAIL_SLOT["background"])
        draw.line([(x - 2, y - 6), (x + 2, y - 6)], fill=DETAIL_SLOT["roof_shade_1"])


def _ground_axes(polygon):
    """Return (center, long unit vector, short unit vector, length, width) of the footprint."""
    corners = np.array(shapely.minimum_rotated_rectangle(polygon).exterior.coords)[:4]
    side_a, side_b = corners[1] - corners[0], corners[2] - corners[1]
    length_a, length_b = float(np.linalg.norm(side_a)), float(np.linalg.norm(side_b))
    if length_a < length_b:
        side_a, side_b, length_a, length_b = side_b, side_a, length_b, length_a
    return corners.mean(axis=0), side_a / length_a, side_b / length_b, length_a, length_b


# Landmark footprints get their own painter here, named by `style` in assets/landmarks.json.
# None yet: Brajeshwar picks the landmarks in Phase 2.
STYLE_PAINTERS: dict = {}


def _paint_building(image, draw, view, polygon, height, building_id, seed, style=None) -> None:
    if style:
        STYLE_PAINTERS[style["style"]](draw, view, polygon, height)
        return
    area = polygon.area
    envelope = shapely.minimum_rotated_rectangle(polygon).area
    rectangular = envelope > 0 and area / envelope >= 0.85 and not polygon.interiors
    kind = _classify(area, height, rectangular, building_id, seed)
    index = _hash(seed, building_id, 6)
    if kind in ("house", "shed"):
        index = TIN_ROOFS[index % len(TIN_ROOFS)]
    elif _hash(seed, building_id + "c", 100) < CONCRETE_PERCENT:
        index = CONCRETE_ROOF
    slot = DETAIL_SLOT[f"roof_{index}"]
    shade = DETAIL_SLOT[f"roof_shade_{index}"]
    if kind == "house" and area < LOW_HOUSE_MAX_M2:
        _paint_low_house(draw, view, polygon, height, slot, shade)
    elif kind in ("house", "shed"):
        _paint_pitched(draw, view, polygon, height, slot, shade, kind == "house", True)
    else:
        _paint_flat(image, draw, view, polygon, height, slot, shade, kind, building_id, seed)


def _paint_span(draw, view, piece: LineString, deck) -> None:
    """Draw one span of a viaduct: its pier, the side of its deck, the deck, and the track."""
    pier = piece.interpolate(0.5, normalized=True)
    x, foot = _project(view, pier.x, pier.y, 0)
    _, head = _project(view, pier.x, pier.y, VIADUCT_M - VIADUCT_DECK_M)
    draw.rectangle([x - 1, head, x + 1, foot], fill=DETAIL_SLOT["wall_shade"])
    draw.line([(x - 1, head), (x - 1, foot)], fill=DETAIL_SLOT["wall_lit"])
    top = [_project(view, x, y, VIADUCT_M) for x, y in deck.exterior.coords]
    under = [_project(view, x, y, VIADUCT_M - VIADUCT_DECK_M) for x, y in deck.exterior.coords]
    side = shapely.MultiPoint(top + under).convex_hull
    if side.geom_type == "Polygon":
        draw.polygon(list(side.exterior.coords), fill=DETAIL_SLOT["wall_shade"])
    draw.polygon(top, fill=DETAIL_SLOT["wall_lit"])
    track = [_project(view, x, y, VIADUCT_M) for x, y in piece.coords]
    draw.line(track, fill=DETAIL_SLOT["road_major"])


@dataclass(frozen=True)
class Deck:
    """One span of a flyover. The center line and the two edges have a row for each point
    along the span; the center's rows are x, y, the deck's height there, and the distance
    along the whole flyover. Each edge has a parapet where it is open."""

    center: np.ndarray
    left: np.ndarray
    right: np.ndarray
    road_class: str
    width_m: float
    footprint: shapely.Polygon
    left_open: np.ndarray
    right_open: np.ndarray

    @property
    def middle(self) -> np.ndarray:
        return self.center[len(self.center) // 2]

    @property
    def on_wall(self) -> bool:
        """Tell a span too low to pass under, which stands on a wall and not on a pier."""
        return self.middle[2] - FLYOVER_DECK_M < FLYOVER_WALL_M


def _paint_deck(draw, view, deck: Deck) -> None:
    """Draw one span of a flyover: its columns or its walls, the sides of its deck, the
    road, its lane line, and its parapets."""
    x, y, top, along = deck.center.T
    under = np.zeros_like(top) if deck.on_wall else top - FLYOVER_DECK_M
    lit, shade = DETAIL_SLOT["wall_lit"], DETAIL_SLOT["wall_shade"]
    if not deck.on_wall:
        at = len(top) // 2
        middle = deck.center[at, :2]
        twin = deck.width_m >= FLYOVER_TWIN_M
        out = 1 - FLYOVER_COLUMN_IN_M / (deck.width_m / 2) if twin else 0.0
        for edge in (deck.left, deck.right) if twin else (deck.left,):
            stands = middle + (edge[at] - middle) * out
            column, foot = _project(view, *stands, 0)
            _, head = _project(view, *stands, under[at])
            draw.rectangle([column - 1, head, column + 1, foot], fill=shade)
            draw.line([(column - 1, head), (column - 1, foot)], fill=lit)

    def lifted(edge: np.ndarray, heights: np.ndarray) -> list[tuple[int, int]]:
        return [_project(view, *point, z) for point, z in zip(edge, heights, strict=True)]

    left, right = lifted(deck.left, top), lifted(deck.right, top)
    for edge, above in ((deck.left, left), (deck.right, right)):
        draw.polygon(above + lifted(edge, under)[::-1], fill=shade)
    road = ROAD_SLOTS.get(deck.road_class, "road_minor")
    draw.polygon(left + right[::-1], fill=DETAIL_SLOT[road])
    if deck.road_class in LINED_ROADS:
        # In step with the dashes of a road on the ground.
        for start in np.arange(math.ceil(along[0] / 10.0) * 10.0, along[-1], 10.0):
            ends = (start, min(start + 4.0, along[-1]))
            dash = [
                _project(view, *(np.interp(at, along, values) for values in (x, y, top)))
                for at in ends
            ]
            draw.line(dash, fill=DETAIL_SLOT["road_line"])
    sides = ((deck.left, left, deck.left_open), (deck.right, right, deck.right_open))
    for edge, below, stands in sides:
        above = lifted(edge, top + FLYOVER_PARAPET_M)
        for at in np.flatnonzero(stands[:-1] & stands[1:]):
            piece = [below[at], below[at + 1], above[at + 1], above[at]]
            draw.polygon(piece, fill=lit)
    # A lamp on the parapet of each span, on alternate sides, as on the footpaths below.
    at = len(top) // 2
    edge, _, stands = sides[int(along[at] // FLYOVER_SPAN_M) % 2]
    if road == "road_major" and stands[at]:
        lamp_x, lamp_y = _project(view, *edge[at], top[at] + FLYOVER_PARAPET_M)
        draw.rectangle([lamp_x, lamp_y - 1, lamp_x + 1, lamp_y], fill=DETAIL_SLOT["lamp_deck"])


def _tree_sprite(
    radius: int, seed: int, blossom: str | None = None
) -> tuple[Image.Image, Image.Image, int]:
    """Return (sprite, mask, crown_center_y) for a shaded canopy with a short trunk.

    A tree in blossom wears its flowers where the sun falls and stays green in the shade.
    """
    lit, lightest = (blossom, f"{blossom}_light") if blossom else ("shrub", "canopy_light")
    width = 2 * radius + 3
    crown_h = int(radius * 1.7)
    height = crown_h + 6
    rng = np.random.default_rng(seed)
    cx, cy = (width - 1) / 2, radius * 0.85 + 1
    lumps = [
        (
            cx + rng.uniform(-0.55, 0.55) * radius,
            cy + rng.uniform(-0.45, 0.45) * radius,
            radius * rng.uniform(0.45, 0.72),
        )
        for _ in range(9)
    ]
    lumps.append((cx, cy, radius * 0.72))
    ys, xs = np.mgrid[0:height, 0:width]
    field = np.zeros(xs.shape, dtype="float32")
    for lump_x, lump_y, lump_r in lumps:
        distance = ((xs - lump_x) ** 2 + ((ys - lump_y) / 0.88) ** 2) / lump_r**2
        field = np.maximum(field, 1.0 - distance)
    crown = field > 0
    sprite = np.full(xs.shape, DETAIL_SLOT["canopy_dark"], dtype="uint8")
    light = (-(xs - cx) * 0.55 - (ys - cy) * 0.83) / radius + field * 0.35
    jitter = hash_field(xs + seed, ys, 31) * 0.26
    sprite[light + jitter > 0.05] = DETAIL_SLOT["tree"]
    sprite[light + jitter > 0.42] = DETAIL_SLOT[lit]
    sprite[light + jitter > 0.78] = DETAIL_SLOT[lightest]
    trunk = (np.abs(xs - cx) <= 1) & (ys > crown_h - 2)
    mask = crown | trunk
    sprite[trunk & ~crown] = DETAIL_SLOT["background"]
    return (
        Image.fromarray(sprite),
        Image.fromarray(mask.astype("uint8") * 255),
        height,
    )


def _tree_points(
    layers: Layers,
    surfaces: gpd.GeoDataFrame,
    tree_rows: list[LineString],
    seed: int,
    rails: gpd.GeoDataFrame | None = None,
) -> np.ndarray:
    """Return (x, y, variant) for trees, placed the same way whatever the crop."""
    left, bottom, right, top = layers.patch.bounds
    columns = np.arange(left, right, TREE_SPACING_M)
    rows = np.arange(bottom, top, TREE_SPACING_M)
    grid_x, grid_y = np.meshgrid(columns, rows)
    rng = np.random.default_rng(seed + 7)
    x = grid_x.ravel() + rng.uniform(-2.6, 2.6, grid_x.size)
    y = grid_y.ravel() + rng.uniform(-2.6, 2.6, grid_x.size)
    roll = rng.uniform(0, 1, grid_x.size)
    variant = rng.integers(0, TREE_SHAPES, grid_x.size)

    keep = np.zeros(x.size, dtype=bool)
    for row in layers.ground.itertuples():
        odds = TREE_ODDS.get(row.ground, 0.0)
        if odds:
            shapely.prepare(row.geometry)
            inside = shapely.contains_xy(row.geometry, x, y)
            keep |= inside & (roll < odds)

    extra = []
    for line in tree_rows:
        for distance in np.arange(0.0, line.length, 8.0):
            point = line.interpolate(float(distance))
            if layers.patch.contains(point):
                extra.append((point.x, point.y, int(distance) % TREE_SHAPES))
    array = np.column_stack([x[keep], y[keep], variant[keep]]).astype("float64")
    if extra:
        array = np.vstack([array, np.array(extra, dtype="float64")])
    if not len(array):
        return np.empty((0, 3))

    blocked = np.concatenate(
        [
            np.asarray(_water_geometry(layers), dtype=object),
            layers.roads.geometry.buffer(layers.roads.width_m / 2 + 1.5).values.to_numpy(),
            layers.buildings.geometry.buffer(1.8).values.to_numpy(),
            surfaces.geometry.values.to_numpy(),
            *(
                []
                if rails is None
                else [rails.geometry.buffer(RAIL_BED_M / 2 + 1.5).values.to_numpy()]
            ),
        ]
    )
    blocked = blocked[~shapely.is_missing(blocked) & ~shapely.is_empty(blocked)]
    hits, _ = shapely.STRtree(blocked).query(
        shapely.points(array[:, 0], array[:, 1]), predicate="intersects"
    )
    free = np.ones(len(array), dtype=bool)
    free[hits] = False
    return array[free]


@dataclass
class Scene:
    """Everything that is computed once per area and shared by its frames."""

    layers: Layers
    surfaces: gpd.GeoDataFrame
    trees: np.ndarray
    sprites: list
    landmarks: list[dict]
    seed: int
    indexes: dict[str, shapely.STRtree]
    styles: dict[str, dict]
    # Track on the ground, and the viaducts cut into spans of (track, deck).
    rails: gpd.GeoDataFrame
    spans: list[tuple[LineString, shapely.Polygon]]
    # The flyovers, cut into spans.
    decks: list[Deck]
    # Every raised span, the viaducts' and then the flyovers': the x, y, and height of its
    # middle, and for a span that crosses over lower ones, their numbers.
    aloft: np.ndarray
    under: dict[int, list[int]]
    # The derived data to read each frame's buildings from, when they are not held in memory.
    buildings_from: Path | None = None


def empty_surfaces() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"kind": []}, geometry=[], crs=METRIC_CRS)


def empty_rails() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"rail": [], "elevated": []}, geometry=[], crs=METRIC_CRS)


def empty_flyovers() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"road_class": [], "width_m": []}, geometry=[], crs=METRIC_CRS)


def flyover_decks(flyovers: gpd.GeoDataFrame, patch) -> list[Deck]:
    """Cut each flyover into spans, each drawn at its own depth among the buildings.

    The edges are worked out along the whole flyover, so two spans meet edge to edge
    around a bend. A span whose middle is outside the patch is left out.
    """
    spans = []
    for number, row in enumerate(flyovers.itertuples()):
        points = shapely.get_coordinates(row.geometry, include_z=True)
        xy = points[:, :2]
        steps = np.diff(xy, axis=0)
        lengths = np.hypot(*steps.T)
        if len(xy) < 2 or not lengths.all():
            continue
        heading = steps / lengths[:, None]
        # Each point's edges are set off across the mean of the headings into and out of
        # it, and farther at a bend, so the deck keeps its width.
        before, after = np.vstack([heading[:1], heading]), np.vstack([heading, heading[-1:]])
        mean = before + after
        size = np.hypot(*mean.T)[:, None]
        mean = np.where(size > 1e-6, mean / np.maximum(size, 1e-6), after)
        reach = row.width_m / 2 / np.maximum((mean * after).sum(axis=1), 0.5)
        across = np.column_stack([-mean[:, 1], mean[:, 0]]) * reach[:, None]
        along = np.concatenate([[0.0], np.cumsum(lengths)])
        center = np.column_stack([points, along])
        ends = np.arange(FLYOVER_SPAN_M, along[-1] - FLYOVER_SPAN_M / 2, FLYOVER_SPAN_M)
        bounds = np.unique([0, *np.searchsorted(along, ends), len(xy) - 1])
        for first, last in itertools.pairwise(bounds):
            part = slice(first, last + 1)
            if not shapely.contains_xy(patch, *xy[(first + last) // 2]):
                continue
            footprint = LineString(xy[part]).buffer(row.width_m / 2, cap_style="flat")
            edges = (xy + across)[part], (xy - across)[part]
            spans.append((number, center[part], *edges, row.road_class, row.width_m, footprint))
    parapets = _open_edges(spans)
    return [Deck(*span[1:], *stands) for span, stands in zip(spans, parapets, strict=True)]


def _open_edges(spans: list[tuple]) -> list[tuple[np.ndarray, np.ndarray]]:
    """Tell, for each span, where along its left edge and its right a parapet stands:
    wherever the edge is not inside the deck of another flyover at about its own height."""
    if not spans:
        return []
    flyover = np.array([span[0] for span in spans])
    height = np.array([span[1][:, 2].mean() for span in spans])
    counts = [len(span[1]) for span in spans]
    owner = np.repeat(np.arange(len(spans)), counts)
    inside = []
    for side in (2, 3):
        points = np.vstack([span[side] for span in spans])
        at = np.concatenate([span[1][:, 2] for span in spans])
        tree = shapely.STRtree([span[6] for span in spans])
        point, other = tree.query(shapely.points(points), predicate="within")
        beside = (flyover[other] != flyover[owner[point]]) & (
            np.abs(height[other] - at[point]) < FLYOVER_BESIDE_M
        )
        covered = np.zeros(len(points), dtype=bool)
        covered[point[beside]] = True
        inside.append(np.split(~covered, np.cumsum(counts)[:-1]))
    return list(zip(*inside, strict=True))


def _crossings(footprints: list, heights: np.ndarray) -> dict[int, list[int]]:
    """Return, for each raised span that crosses over lower ones, the lower ones' numbers.

    One span is over another where their footprints share ground and it clears the other
    by a deck's depth; two spans side by side at one height are neither over the other.
    """
    if not footprints:
        return {}
    shapes = np.array(footprints, dtype=object)
    upper, lower = shapely.STRtree(shapes).query(shapes, predicate="intersects")
    clear = heights[upper] - heights[lower] >= FLYOVER_DECK_M
    upper, lower = upper[clear], lower[clear]
    shared = shapely.area(shapely.intersection(shapes[upper], shapes[lower])) > 1.0
    under = defaultdict(list)
    for high, low in zip(upper[shared], lower[shared], strict=True):
        under[int(high)].append(int(low))
    return dict(under)


def viaduct_spans(rails: gpd.GeoDataFrame) -> list[tuple[LineString, shapely.Polygon]]:
    """Cut the raised track into spans, each drawn at its own depth among the buildings."""
    spans = []
    for line in rails.explode(index_parts=False).geometry:
        if line.geom_type != "LineString":
            continue
        for start in np.arange(0.0, line.length, VIADUCT_SPAN_M):
            piece = substring(line, start, min(start + VIADUCT_SPAN_M, line.length))
            deck = piece.buffer(VIADUCT_HALF_M, cap_style="flat")
            if piece.geom_type == "LineString" and deck.geom_type == "Polygon":
                spans.append((piece, deck))
    return spans


def load_landmarks() -> list[dict]:
    to_metric = Transformer.from_crs(4326, METRIC_CRS, always_xy=True)
    landmarks = []
    for path in sorted(SPRITE_DIR.glob("*.json")):
        sidecar = json.loads(path.read_text())
        x, y = to_metric.transform(sidecar["placed_at"]["lon"], sidecar["placed_at"]["lat"])
        sprite = np.asarray(Image.open(SPRITE_DIR / sidecar.get("sprite", f"{path.stem}.png")))
        landmarks.append(
            {
                "x": x,
                "y": y,
                "sprite": sprite,
                "anchor": sidecar["anchor_px"],
                "clearing": sidecar.get("clearing_m", LANDMARK_CLEARING_M),
            }
        )
    return landmarks


def load_styles() -> dict[str, dict]:
    """Return footprint landmark styles, keyed by the building they replace."""
    styles = {}
    for entry in json.loads(LANDMARKS_PATH.read_text()):
        for building_id in entry["replaces"]:
            styles[building_id] = entry
    return styles


def compute_trees(
    layers: Layers,
    surfaces: gpd.GeoDataFrame,
    tree_rows: list[LineString],
    landmarks: list[dict],
    seed: int,
    rails: gpd.GeoDataFrame | None = None,
) -> np.ndarray:
    trees = _tree_points(layers, surfaces, tree_rows, seed, rails)
    for landmark in landmarks:
        distance = np.hypot(trees[:, 0] - landmark["x"], trees[:, 1] - landmark["y"])
        trees = trees[distance > landmark["clearing"]]
    return trees


def build_scene(
    layers: Layers,
    tree_rows: list[LineString] | None = None,
    landmarks: list[dict] | None = None,
    surfaces: gpd.GeoDataFrame | None = None,
    seed: int = SEED,
    trees: np.ndarray | None = None,
    styles: dict[str, dict] | None = None,
    rails: gpd.GeoDataFrame | None = None,
    flyovers: gpd.GeoDataFrame | None = None,
) -> Scene:
    tree_rows = tree_rows or []
    landmarks = landmarks or []
    surfaces = empty_surfaces() if surfaces is None else surfaces
    rails = empty_rails() if rails is None else rails
    styles = styles or {}
    if trees is None:
        trees = compute_trees(layers, surfaces, tree_rows, landmarks, seed, rails)
        cleared = layers.buildings[layers.buildings.building_id.isin(list(styles))]
        for row in cleared.itertuples():
            clearing = styles[row.building_id].get("clearing_m")
            if clearing and len(trees):
                inside = shapely.contains_xy(
                    row.geometry.buffer(clearing), trees[:, 0], trees[:, 1]
                )
                trees = trees[~inside]
    # Exploded so a frame only touches the ground fragments it can see.
    ground = layers.ground.explode(index_parts=False).reset_index(drop=True)
    local = Layers(
        layers.patch, ground, layers.water, layers.waterways, layers.roads, layers.buildings
    )
    frames = {
        "ground": ground,
        "water": layers.water,
        "waterways": layers.waterways,
        "roads": layers.roads,
        "buildings": layers.buildings,
        "surfaces": surfaces,
    }
    raised = rails.elevated.astype(bool)
    grounded = rails[~raised].reset_index(drop=True)
    spans = viaduct_spans(rails[raised])
    frames["rails"] = grounded
    indexes = {name: shapely.STRtree(frame.geometry.values) for name, frame in frames.items()}
    indexes["spans"] = shapely.STRtree([deck for _, deck in spans])
    decks = flyover_decks(empty_flyovers() if flyovers is None else flyovers, layers.patch)
    indexes["decks"] = shapely.STRtree([deck.footprint for deck in decks])
    middles = [piece.interpolate(0.5, normalized=True) for piece, _ in spans]
    aloft = np.array(
        [
            *((middle.x, middle.y, VIADUCT_M) for middle in middles),
            *((*deck.middle[:2], deck.center[:, 2].mean()) for deck in decks),
        ]
    ).reshape(-1, 3)
    footprints = [*(deck for _, deck in spans), *(deck.footprint for deck in decks)]
    under = _crossings(footprints, aloft[:, 2])
    # Every shape in green first, then again in each blossom, in BLOSSOM's order.
    sprites = [
        _tree_sprite(RADIUS_PX[index % 6], seed + index, blossom)
        for blossom in (None, *BLOSSOM)
        for index in range(TREE_SHAPES)
    ]
    return Scene(
        local,
        surfaces,
        trees,
        sprites,
        landmarks,
        seed,
        indexes,
        styles,
        grounded,
        spans,
        decks,
        aloft,
        under,
    )


def _view_quad(view: Viewport) -> shapely.Polygon:
    """Return the ground area that the view's rectangle covers."""
    a, b, d, e = PROJECTION.matrix
    det = a * e - b * d
    corners = []
    for sx, sy in ((0, 0), (view.width, 0), (view.width, view.height), (0, view.height)):
        px, py = sx - view.x_offset, sy - view.y_offset
        corners.append(((e * px - b * py) / det, (-d * px + a * py) / det))
    return shapely.Polygon(corners)


def _select(frame: gpd.GeoDataFrame, index: shapely.STRtree, quad) -> gpd.GeoDataFrame:
    return frame.iloc[np.unique(index.query(quad, predicate="intersects"))]


def _read_buildings(path: Path, quad: shapely.Polygon) -> gpd.GeoDataFrame:
    """Read the buildings a view can see from the derived data, through its spatial index."""
    frame = pyogrio.read_dataframe(
        path, layer="buildings", bbox=quad.bounds, columns=["building_id", "height_m"]
    )
    seen = shapely.intersects(np.asarray(frame.geometry.values), quad)
    return frame[seen].sort_values("building_id")


def _local_layers(scene: Scene, quad: shapely.Polygon) -> Layers:
    """Return only the features a view can see."""
    layers = scene.layers
    if scene.buildings_from:
        buildings = _read_buildings(scene.buildings_from, quad)
    else:
        buildings = _select(layers.buildings, scene.indexes["buildings"], quad)
    return Layers(
        layers.patch,
        _select(layers.ground, scene.indexes["ground"], quad),
        _select(layers.water, scene.indexes["water"], quad),
        _select(layers.waterways, scene.indexes["waterways"], quad),
        _select(layers.roads, scene.indexes["roads"], quad),
        buildings,
    )


def _screen(view: Viewport, x, y):
    a, b, d, e = PROJECTION.matrix
    return a * x + b * y + view.x_offset, d * x + e * y + view.y_offset


def _visible_landmarks(scene: Scene, view: Viewport) -> list[dict]:
    landmarks = []
    for landmark in scene.landmarks:
        sx, sy = _screen(view, landmark["x"], landmark["y"])
        if -200 < sx < view.width + 200 and -200 < sy < view.height + 200:
            landmarks.append(landmark)
    return landmarks


# What an item of the scene is, which picks its painter.
BUILDING, TREE, LANDMARK, SPAN, DECK = range(5)


def _add_buildings(items: list, shadows: list, scene: Scene, local: Layers) -> None:
    for row in local.buildings.itertuples():
        style = scene.styles.get(row.building_id)
        height = style.get("height_m", row.height_m) if style else row.height_m
        for part in parts(row.geometry):
            polygon = part
            if style and "scale" in style:
                factor = style["scale"]
                polygon = shapely.affinity.scale(part, factor, factor, origin="centroid")
            dx, dy = _sun_offset(height * SHADOW_PER_HEIGHT)
            moved = shapely.affinity.translate(polygon, dx, dy)
            shadows.append((shapely.convex_hull(shapely.union(polygon, moved)), 1))
            center = polygon.centroid
            items.append((-_depth(center.x, center.y), row.building_id, BUILDING, polygon, height))


def _drawn_depth(scene: Scene, number: int) -> float:
    """Return the depth a raised span is drawn at: its own, or just nearer than the lower
    spans it crosses over, so that it is drawn after them."""
    x, y, _ = scene.aloft[number]
    lower = [_drawn_depth(scene, low) - 0.01 for low in scene.under.get(number, ())]
    return min([_depth(x, y), *lower])


def _add_spans(items: list, shadows: list, scene: Scene, quad: shapely.Polygon) -> None:
    dx, dy = _sun_offset(VIADUCT_M * SHADOW_PER_HEIGHT)
    for index in np.unique(scene.indexes["spans"].query(quad, predicate="intersects")):
        piece, deck = scene.spans[index]
        shadows.append((shapely.affinity.translate(deck, dx, dy), 1))
        items.append((-_drawn_depth(scene, index), f"span/{index:07d}", SPAN, piece, deck))


def _add_decks(items: list, shadows: list, scene: Scene, quad: shapely.Polygon) -> None:
    for index in np.unique(scene.indexes["decks"].query(quad, predicate="intersects")):
        deck = scene.decks[index]
        dx, dy = _sun_offset(float(deck.center[:, 2].mean()) * SHADOW_PER_HEIGHT)
        shadow = shapely.affinity.translate(deck.footprint, dx, dy)
        if deck.on_wall:
            # No light passes under a wall.
            shadow = shapely.convex_hull(shapely.union(deck.footprint, shadow))
        shadows.append((shadow, 1))
        depth = _drawn_depth(scene, len(scene.spans) + index)
        items.append((-depth, f"deck/{index:07d}", DECK, deck, None))


def _blossoms(trees: np.ndarray, seed: int) -> np.ndarray:
    """Return for each tree 0 if it is green, or the number of its blossom, from 1."""
    x, y = trees[:, 0] * 10, trees[:, 1] * 10
    tree = hash_field(x, y, seed + 43)
    # Each tree finds its grove from a spot a little off its own, so a grove's edge is ragged.
    east = trees[:, 0] + (hash_field(x, y, seed + 45) - 0.5) * GROVE_M / 2
    north = trees[:, 1] + (hash_field(x, y, seed + 47) - 0.5) * GROVE_M / 2
    grove = hash_field(east // GROVE_M, north // GROVE_M, seed + 41)
    kind = 1 + (grove / GROVES_IN_BLOOM * len(BLOSSOM)).astype("int64")
    return np.where((grove < GROVES_IN_BLOOM) & (tree < TREES_IN_BLOOM), kind, 0)


def _add_trees(items: list, shadows: list, scene: Scene, view: Viewport) -> None:
    trees = scene.trees
    screen_x, screen_y = _screen(view, trees[:, 0], trees[:, 1])
    nearby = (
        (screen_x > -40)
        & (screen_x < view.width + 40)
        & (screen_y > -40)
        & (screen_y < view.height + 60)
    )
    seen = trees[nearby]
    for (x, y, variant), blossom in zip(seen, _blossoms(seen, scene.seed), strict=True):
        index = int(variant)
        radius_m = RADIUS_PX[index % 6] / PROJECTION.lift * 0.95
        dx, dy = _sun_offset(radius_m * 0.9)
        shadows.append((Point(x + dx, y + dy).buffer(radius_m * 0.9, quad_segs=4), 1))
        sprite = index + TREE_SHAPES * int(blossom)
        items.append((-_depth(x, y), f"tree/{x:.2f}/{y:.2f}", TREE, (x, y), sprite))


def _add_landmarks(items: list, shadows: list, landmarks: list[dict]) -> None:
    for landmark in landmarks:
        dx, dy = _sun_offset(12.0)
        foot = Point(landmark["x"], landmark["y"]).buffer(4.5)
        shadow = shapely.convex_hull(shapely.union(foot, shapely.affinity.translate(foot, dx, dy)))
        shadows.append((shadow, 1))
        items.append((-_depth(landmark["x"], landmark["y"]), "landmark", LANDMARK, landmark, 0))


def _darken_shadows(canvas: np.ndarray, shadows: list, view: Viewport) -> None:
    mask = _burn(shadows, view).astype(bool)
    remap = np.arange(256, dtype="uint8")
    for name, darker in SHADOW.items():
        remap[DETAIL_SLOT[name]] = DETAIL_SLOT[darker]
    inside = mask & (canvas != DETAIL_SLOT["background"])
    canvas[inside] = remap[canvas[inside]]


def _paint_items(image: Image.Image, items: list, scene: Scene, view: Viewport) -> None:
    """Draw buildings, trees, spans, and sprites from the back of the scene to the front."""
    draw = ImageDraw.Draw(image)
    items.sort(key=lambda item: (item[0], item[1]))
    for _, label, kind, payload, extra in items:
        if kind == BUILDING:
            style = scene.styles.get(label)
            _paint_building(image, draw, view, payload, extra, label, scene.seed, style)
        elif kind == TREE:
            sprite, sprite_mask, height = scene.sprites[extra]
            x, y = _project(view, payload[0], payload[1], 0)
            image.paste(sprite, (x - sprite.width // 2, y - height + 1), sprite_mask)
        elif kind == SPAN:
            _paint_span(draw, view, payload, extra)
        elif kind == DECK:
            _paint_deck(draw, view, payload)
        else:
            art = payload["sprite"]
            x, y = _project(view, payload["x"], payload["y"], 0)
            left = x - payload["anchor"][0]
            top = y - payload["anchor"][1]
            paste_mask = Image.fromarray(((art != TRANSPARENT).astype("uint8")) * 255)
            image.paste(Image.fromarray(art), (left, top), paste_mask)


def render_detail(scene: Scene, view: Viewport) -> np.ndarray:
    """Return a uint8 array of palette slots."""
    quad = _view_quad(view)
    if not quad.intersects(scene.layers.patch):
        return np.full((view.height, view.width), DETAIL_SLOT["background"], dtype="uint8")
    local = _local_layers(scene, quad)
    surfaces = _select(scene.surfaces, scene.indexes["surfaces"], quad)
    landmarks = _visible_landmarks(scene, view)

    canvas = _paint_ground(local, view)
    _paint_surfaces(canvas, surfaces, view)
    for landmark in landmarks:
        clearing = Point(landmark["x"], landmark["y"]).buffer(landmark["clearing"] * 0.6)
        canvas[_burn([(clearing, 1)], view).astype(bool)] = DETAIL_SLOT["bare"]
    _paint_water(canvas, local, view)
    _paint_roads(canvas, local, view)
    _paint_rails(canvas, _select(scene.rails, scene.indexes["rails"], quad), local.patch, view)

    items: list = []
    shadows: list = []
    _add_buildings(items, shadows, scene, local)
    _add_spans(items, shadows, scene, quad)
    _add_decks(items, shadows, scene, quad)
    _add_trees(items, shadows, scene, view)
    _add_landmarks(items, shadows, landmarks)
    _darken_shadows(canvas, shadows, view)

    image = Image.fromarray(canvas)
    _paint_items(image, items, scene, view)
    return np.asarray(image, dtype="uint8").copy()


def _load_tree_rows(area: Area) -> list[LineString]:
    rows = [
        f.geometry
        for f in load_features(raw_dir(area) / "osm.json")
        if f.tags.get("natural") == "tree_row" and f.geometry.geom_type == "LineString"
    ]
    if not rows:
        return []
    return list(gpd.GeoSeries(rows, crs=4326).to_crs(METRIC_CRS).values)


def _load_or(area: Area, layer: str, empty) -> gpd.GeoDataFrame:
    """Read a layer that only some areas have, or make an empty one."""
    path = derived_path(area)
    if layer not in pyogrio.list_layers(path)[:, 0]:
        return empty()
    return gpd.read_file(path, layer=layer)


def trees_path(area: Area) -> Path:
    return Path("data/derived") / f"{area.name}_trees.npy"


def _load_layers_without_buildings(area: Area) -> Layers:
    path = derived_path(area)
    names = ("patch", "ground", "water", "waterways", "roads")
    frames = {name: gpd.read_file(path, layer=name) for name in names}
    patch = frames.pop("patch").geometry.iloc[0]
    nothing = gpd.GeoDataFrame({"building_id": [], "height_m": []}, geometry=[], crs=METRIC_CRS)
    return Layers(patch=patch, buildings=nothing, **frames)


def load_scene(
    area: Area, use_cached_trees: bool = False, buildings_by_frame: bool = False
) -> Scene:
    """Load what every frame of the area shares.

    A city's buildings take gigabytes in every process that holds them, so a render
    worker passes `buildings_by_frame` and reads each frame's buildings as it draws it.
    That needs the cached trees: placing trees needs every building.
    """
    layers = _load_layers_without_buildings(area) if buildings_by_frame else load_layers(area)
    surfaces = _load_or(area, "surfaces", empty_surfaces)
    landmarks = load_landmarks()
    trees = np.load(trees_path(area)) if use_cached_trees else None
    scene = _build_area_scene(area, layers, surfaces, landmarks, trees)
    if buildings_by_frame:
        scene.buildings_from = derived_path(area)
    return scene


def _build_area_scene(area, layers, surfaces, landmarks, trees) -> Scene:
    # Tree rows only matter while placing trees, and finding them parses all of the area's
    # OSM, a gigabyte for the central area; with the trees already placed they are skipped.
    return build_scene(
        layers,
        _load_tree_rows(area) if trees is None else [],
        landmarks,
        surfaces,
        trees=trees,
        styles=load_styles(),
        rails=_load_or(area, "rails", empty_rails),
        flyovers=_load_or(area, "flyovers", empty_flyovers),
    )


def _save_indexed(slots: np.ndarray, path: Path, palette: bytes, **options) -> None:
    image = Image.fromarray(slots, mode="P")
    image.putpalette(palette)
    # Written beside the target and renamed, so a frame on disk is always a whole frame.
    partial = path.with_name(path.name + ".part")
    image.save(partial, format="PNG", optimize=True, **options)
    partial.replace(path)


def save_slots(slots: np.ndarray, path: Path) -> None:
    """Write a picture to look at on its own: by day, with every tree in flower."""
    _save_indexed(slots, path, detail_lookup())


def layer_path(path: Path, layer: str) -> Path:
    """Return where a frame's layer is kept: beside the frame, in a folder of the layer's name."""
    return path.parent / layer / path.name


def save_frame(slots: np.ndarray, path: Path) -> None:
    """Write a frame of the map, and each of its layers.

    The frame itself is written last, so a frame on disk has its layers.
    """
    empty = DETAIL_SLOT["background"]
    for layer in LAYERS:
        colors = layer_colors(layer)
        shown = np.zeros(256, dtype=bool)
        shown[[DETAIL_SLOT[name] for name in colors]] = True
        palette = lookup({**dict.fromkeys(DETAIL_SLOT, "#000000"), **colors}, DETAIL_SLOT)
        clear = {"transparency": bytes(shown * np.uint8(255))} if layer in CLEAR_LAYERS else {}
        target = layer_path(path, layer)
        target.parent.mkdir(exist_ok=True)
        own = np.where(shown[slots], slots, empty).astype("uint8")
        _save_indexed(own, target, palette, **clear)
    _save_indexed(slots, path, base_lookup())


def detail(area: Area) -> None:
    """Render one frame of the area in each detail view."""
    scene = load_scene(area)
    print(f"{area.name}: {len(scene.layers.buildings)} buildings, {len(scene.trees)} trees")
    to_metric = Transformer.from_crs(4326, METRIC_CRS, always_xy=True)
    x, y = to_metric.transform(*CROP_CENTERS.get(area.name, area.center))
    target = Path("out") / area.name
    target.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for name in DETAIL_VIEWS:
        started = time.perf_counter()
        use_view(name)
        view = centered_viewport(PROJECTION, x, y, CROP_PX, CROP_PX)
        output = target / f"{stamp}_detail-{name}.png"
        save_slots(render_detail(scene, view), output)
        print(f"{output}: {time.perf_counter() - started:.1f}s")


def view_projection(view: str) -> Projection:
    return replace(PROJECTION_B, rotation_deg=VIEWS[view])


def use_view(view: str) -> None:
    """Point every painter in this process at one view."""
    global PROJECTION  # noqa: PLW0603
    PROJECTION = view_projection(view)


def frames_dir(area: Area, view: str = DEFAULT_VIEW) -> Path:
    name = "frames" if view == DEFAULT_VIEW else f"frames-{view}"
    return Path("out") / area.name / name


def manifest_path(area: Area, view: str = DEFAULT_VIEW) -> Path:
    name = "manifest.json" if view == DEFAULT_VIEW else f"manifest-{view}.json"
    return Path("out") / area.name / name


def frame_path(directory: Path, column: int, row: int) -> Path:
    return directory / f"{row:03d}_{column:03d}.png"


def frames_fingerprint(area: Area, canvas: Viewport | None = None) -> str:
    """Return a hash of what decides a view's frames: the data, the canvas, and the renderer.

    Without a canvas it is the same for every view, and tells whether a built view is stale.
    """
    stat = derived_path(area).stat()
    digest = hashlib.blake2b(f"{canvas}:{stat.st_size}:{stat.st_mtime_ns}".encode(), digest_size=8)
    package = Path(__file__).parent
    drawing = [package / name for name in ("detail.py", "render.py", "palettes.py")]
    sources = [*drawing, LANDMARKS_PATH, *SPRITE_DIR.glob("*")]
    for path in sorted(sources):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def open_frames_dir(directory: Path, fingerprint: str) -> None:
    """Make a view's frame folder, emptying it first if its frames came from other inputs."""
    record = directory / FINGERPRINT
    if directory.exists() and not (record.exists() and record.read_text() == fingerprint):
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)
    record.write_text(fingerprint)


def missing_cells(directory: Path, cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [
        (column, row) for column, row in cells if not frame_path(directory, column, row).exists()
    ]


def frame_view(canvas: Viewport, column: int, row: int) -> Viewport:
    """Return a frame's view, including its apron, cut from the global canvas."""
    return Viewport(
        FRAME_PX + 2 * APRON_PX,
        FRAME_PX + 2 * APRON_PX,
        canvas.x_offset - column * FRAME_PX + APRON_PX,
        canvas.y_offset - row * FRAME_PX + APRON_PX,
    )


def render_frame(scene: Scene, canvas: Viewport, column: int, row: int) -> np.ndarray:
    slots = render_detail(scene, frame_view(canvas, column, row))
    return slots[APRON_PX:-APRON_PX, APRON_PX:-APRON_PX]


_worker: dict = {}


def _init_worker(area: Area, canvas: Viewport, view: str, deadline: float | None) -> None:
    use_view(view)
    scene = load_scene(area, use_cached_trees=True, buildings_by_frame=True)
    _worker.update(scene=scene, canvas=canvas, area=area, view=view, deadline=deadline)


def _render_and_save(cell: tuple[int, int]) -> bool:
    """Draw one frame and return True, or return False without drawing once past the deadline."""
    deadline = _worker["deadline"]
    if deadline is not None and time.time() >= deadline:
        return False
    column, row = cell
    slots = render_frame(_worker["scene"], _worker["canvas"], column, row)
    save_frame(slots, frame_path(frames_dir(_worker["area"], _worker["view"]), column, row))
    return True


def frame_grid(canvas: Viewport) -> tuple[int, int]:
    return math.ceil(canvas.width / FRAME_PX), math.ceil(canvas.height / FRAME_PX)


def frames(area: Area, only: list[tuple[int, int]] | None = None) -> None:
    """Render every view of the area as a grid of frames and write its manifests."""
    started = time.perf_counter()
    scene = load_scene(area)
    np.save(trees_path(area), scene.trees)
    print(f"{area.name}: {len(scene.trees)} trees")
    plan_view(area, scene, DEFAULT_VIEW)
    for view in RENDERED_VIEWS:
        _render_view(area, scene, view, only)
    print(f"done in {time.perf_counter() - started:.0f}s")


def plan_view(area: Area, scene: Scene, view: str) -> None:
    """Write a view's manifest, its canvas and frame grid, without rendering a frame."""
    projection = view_projection(view)
    canvas = full_viewport(projection, scene.layers)
    columns, rows = frame_grid(canvas)
    manifest_path(area, view).parent.mkdir(parents=True, exist_ok=True)
    manifest_path(area, view).write_text(
        json.dumps(
            {
                "area": area.name,
                "projection": projection.name,
                "pixels_per_meter": 2.0,
                "rotation_deg": projection.rotation_deg,
                "ground_scale": projection.ground_scale,
                "matrix": list(projection.matrix),
                "x_offset": canvas.x_offset,
                "y_offset": canvas.y_offset,
                "canvas_width": columns * FRAME_PX,
                "canvas_height": rows * FRAME_PX,
                "frame_px": FRAME_PX,
                "columns": columns,
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )


def _render_view(
    area: Area,
    scene: Scene,
    view: str,
    only: list[tuple[int, int]] | None = None,
    deadline: float | None = None,
) -> bool:
    """Draw the view's frames that are not on disk yet and return whether all of them now are.

    Past the deadline, an epoch time, no new frame starts; the ones being drawn finish.
    """
    started = time.perf_counter()
    projection = view_projection(view)
    canvas = full_viewport(projection, scene.layers)
    columns, rows = frame_grid(canvas)
    directory = frames_dir(area, view)
    open_frames_dir(directory, frames_fingerprint(area, canvas))
    every = [(column, row) for row in range(rows) for column in range(columns)]
    cells = only or missing_cells(directory, every)
    print(f"{view}: {columns} x {rows} frames, {len(cells)} to draw", flush=True)
    if cells:
        context = multiprocessing.get_context("spawn")
        with context.Pool(WORKERS, _init_worker, (area, canvas, view, deadline)) as pool:
            drawn = 0
            for count, done in enumerate(pool.imap_unordered(_render_and_save, cells), 1):
                drawn += done
                if done and (drawn % 10 == 0 or count == len(cells)):
                    print(
                        f"{drawn}/{len(cells)} frames, {time.perf_counter() - started:.0f}s",
                        flush=True,
                    )
    plan_view(area, scene, view)
    return not missing_cells(directory, every)
