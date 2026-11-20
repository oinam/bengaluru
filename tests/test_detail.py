import json
from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import shapely
from PIL import Image, ImageDraw

from bengaluru.areas import get_area
from bengaluru.detail import (
    DEFAULT_VIEW,
    DETAIL_SLOT,
    FRAME_PX,
    LANDMARKS_PATH,
    RENDERED_VIEWS,
    STYLE_PAINTERS,
    TRANSPARENT,
    VIEWS,
    _blossoms,
    _drawn_depth,
    _paint_flat,
    _paint_low_house,
    _paint_pitched,
    _project,
    build_scene,
    detail_colors,
    frames_dir,
    layer_path,
    manifest_path,
    missing_cells,
    open_frames_dir,
    render_detail,
    render_frame,
    save_frame,
    view_projection,
)
from bengaluru.palettes import BLOSSOM
from bengaluru.render import PROJECTION_B, Layers, centered_viewport


def sample_layers():
    patch = shapely.box(0, 0, 300, 300)
    empty = gpd.GeoDataFrame({"width_m": [], "road_class": []}, geometry=[], crs=32643)
    ground = gpd.GeoDataFrame({"ground": ["tree"]}, geometry=[patch], crs=32643)
    water = gpd.GeoDataFrame(geometry=[shapely.box(10, 10, 60, 60)], crs=32643)
    buildings = gpd.GeoDataFrame(
        {"building_id": ["a", "b"], "height_m": [5.0, 14.0]},
        geometry=[shapely.box(120, 120, 134, 130), shapely.box(170, 100, 200, 130)],
        crs=32643,
    )
    return Layers(patch, ground, water, empty, empty, buildings)


def test_detail_palette_gives_every_slot_a_color_and_leaves_transparency_alone():
    colors = detail_colors()
    assert set(colors) == set(DETAIL_SLOT)
    assert sorted(DETAIL_SLOT.values()) == list(range(len(DETAIL_SLOT)))
    assert len(DETAIL_SLOT) <= TRANSPARENT


def test_some_trees_flower_in_groves_and_the_same_ones_every_time():
    rng = np.random.default_rng(3)
    trees = np.column_stack([rng.uniform(0, 3000, (20000, 2)), rng.integers(0, 12, 20000)])
    kinds = _blossoms(trees, 7)
    assert np.array_equal(kinds, _blossoms(trees, 7))
    assert np.array_equal(kinds[:500], _blossoms(trees[:500], 7))
    assert set(np.unique(kinds).tolist()) == set(range(len(BLOSSOM) + 1))
    assert 0.03 < (kinds > 0).mean() < 0.1
    # Trees in bloom stand together: most squares of the grid have none at all.
    squares = {(x // 100, y // 100) for x, y, _ in trees[kinds > 0]}
    assert len(squares) < 0.5 * 30 * 30


def test_detail_render_is_deterministic_and_grows_trees():
    layers = sample_layers()
    view = centered_viewport(PROJECTION_B, 150, 150, 600, 600)
    scene = build_scene(layers)
    first = render_detail(scene, view)
    assert np.array_equal(first, render_detail(scene, view))
    painted = set(np.unique(first).tolist())
    assert {DETAIL_SLOT["canopy_light"], DETAIL_SLOT["water"], DETAIL_SLOT["wall_lit"]} <= painted


@pytest.mark.parametrize("path", sorted(Path("assets/sprites").glob("*.png")))
def test_landmark_sprites_use_only_palette_slots_and_transparency(path):
    values = set(np.unique(np.asarray(Image.open(path))).tolist())
    assert TRANSPARENT in values
    assert values - {TRANSPARENT} <= set(DETAIL_SLOT.values())


def test_every_landmark_style_has_a_painter_and_a_reference():
    for entry in json.loads(LANDMARKS_PATH.read_text()):
        assert entry["style"] in STYLE_PAINTERS
        assert entry["replaces"]
        assert entry["references"]


def test_adjacent_frames_join_without_a_seam():
    scene = build_scene(sample_layers())
    width = 2 * FRAME_PX
    canvas = centered_viewport(PROJECTION_B, 150, 150, width, FRAME_PX)
    joined = np.hstack([render_frame(scene, canvas, 0, 0), render_frame(scene, canvas, 1, 0)])
    assert np.array_equal(joined, render_detail(scene, canvas))


def test_track_and_viaduct_join_without_a_seam():
    rails = gpd.GeoDataFrame(
        {"rail": ["rail", "subway"], "elevated": [False, True]},
        geometry=[
            shapely.LineString([(0, 80), (300, 220)]),
            shapely.LineString([(0, 220), (300, 80)]),
        ],
        crs=32643,
    )
    scene = build_scene(sample_layers(), rails=rails)
    assert len(scene.rails) == 1
    assert len(scene.spans) > 10
    width = 2 * FRAME_PX
    canvas = centered_viewport(PROJECTION_B, 150, 150, width, FRAME_PX)
    whole = render_detail(scene, canvas)
    joined = np.hstack([render_frame(scene, canvas, 0, 0), render_frame(scene, canvas, 1, 0)])
    assert np.array_equal(joined, whole)
    assert not np.array_equal(whole, render_detail(build_scene(sample_layers()), canvas))


def flyover(points, heights, road_class="trunk", width=14.0):
    line = shapely.LineString([(x, y, z) for (x, y), z in zip(points, heights, strict=True)])
    return {"road_class": road_class, "width_m": width, "geometry": line}


def deck_points(start, end, count):
    return np.linspace(start, end, count).tolist()


def test_a_flyover_stands_over_the_ground_and_joins_without_a_seam():
    layers = sample_layers()
    road = shapely.LineString([(0, 150), (300, 150)])
    roads = gpd.GeoDataFrame(
        {"width_m": [14.0], "road_class": ["trunk"], "raised": [True]}, geometry=[road], crs=32643
    )
    points = deck_points((0, 150), (300, 150), 39)
    heights = np.minimum(6.5, np.minimum(np.arange(39), np.arange(39)[::-1]) * 0.8)
    decks = gpd.GeoDataFrame([flyover(points, heights)], crs=32643)
    scene = build_scene(replace(layers, roads=roads), flyovers=decks)
    assert len(scene.decks) > 10
    assert scene.decks[0].on_wall
    assert not scene.decks[len(scene.decks) // 2].on_wall
    width = 2 * FRAME_PX
    canvas = centered_viewport(PROJECTION_B, 150, 150, width, FRAME_PX)
    whole = render_detail(scene, canvas)
    joined = np.hstack([render_frame(scene, canvas, 0, 0), render_frame(scene, canvas, 1, 0)])
    assert np.array_equal(joined, whole)
    # The road is drawn on the deck, and without the deck not at all: never on the ground.
    bare = render_detail(build_scene(replace(layers, roads=roads)), canvas)
    assert (whole == DETAIL_SLOT["road_line"]).any()
    assert (whole == DETAIL_SLOT["lamp_deck"]).any()
    assert not (bare == DETAIL_SLOT["road_line"]).any()


def test_a_span_that_crosses_over_a_lower_one_is_drawn_after_it():
    low = flyover(deck_points((0, 150), (300, 150), 39), [6.5] * 39)
    high = flyover(deck_points((150, 0), (150, 300), 39), [11.5] * 39, "primary", 12.0)
    scene = build_scene(sample_layers(), flyovers=gpd.GeoDataFrame([low, high], crs=32643))
    assert scene.under
    for upper, lowers in scene.under.items():
        assert scene.aloft[upper, 2] == 11.5
        for lower in lowers:
            assert scene.aloft[lower, 2] == 6.5
            assert _drawn_depth(scene, upper) < _drawn_depth(scene, lower)
    # Away from the crossing a span keeps its own depth.
    far = len(scene.decks) - 1
    assert far not in scene.under
    assert _drawn_depth(scene, far) == PROJECTION_B.depth(*scene.aloft[far, :2])


def test_default_view_keeps_its_paths():
    area = get_area("central")
    assert frames_dir(area).name == "frames"
    assert frames_dir(area, "90").name == "frames-90"
    assert manifest_path(area).name == "manifest.json"
    assert manifest_path(area, "270").name == "manifest-270.json"


def test_views_are_quarter_turns_of_the_chosen_projection():
    assert view_projection(DEFAULT_VIEW) == PROJECTION_B
    assert len(VIEWS) == 24
    a, b, _, _ = view_projection("0").matrix
    next_a, next_b, _, _ = view_projection("90").matrix
    assert (round(next_a, 6), round(next_b, 6)) == (round(-b, 6), round(a, 6))


def test_the_site_shows_four_quarter_turns_north_up_first():
    assert RENDERED_VIEWS[0] == "315"
    assert view_projection("315").rotation_deg == 0
    turns = [VIEWS[view] for view in RENDERED_VIEWS]
    assert turns == [0.0, 90.0, 180.0, 270.0]
    assert DEFAULT_VIEW not in RENDERED_VIEWS


def test_low_house_veranda_reaches_past_the_plain_roof():
    view = centered_viewport(PROJECTION_B, 0, 0, 200, 200)
    polygon = shapely.box(-6, -3, 6, 3)
    background = DETAIL_SLOT["grass"]
    plain = Image.new("L", (200, 200), background)
    _paint_pitched(ImageDraw.Draw(plain), view, polygon, 4.4, 1, 2, True, True)
    with_veranda = Image.new("L", (200, 200), background)
    _paint_low_house(ImageDraw.Draw(with_veranda), view, polygon, 9.0, 1, 2)
    plain_area = int((np.asarray(plain) != background).sum())
    assert int((np.asarray(with_veranda) != background).sum()) > plain_area


def test_a_courtyard_shows_the_ground_and_its_far_walls():
    view = centered_viewport(PROJECTION_B, 0, 0, 300, 300)
    block = shapely.box(-40, -40, 40, 40)
    hole = shapely.box(-25, -25, 25, 25)
    ground = DETAIL_SLOT["grass"]
    image = Image.new("L", (300, 300), ground)
    _paint_flat(
        image, ImageDraw.Draw(image), view, block.difference(hole), 9.0, 1, 2, "flat", "b", 0
    )
    solid = Image.new("L", (300, 300), ground)
    _paint_flat(solid, ImageDraw.Draw(solid), view, block, 9.0, 1, 2, "flat", "b", 0)
    drawn, lid = np.asarray(image), np.asarray(solid)

    x, y = _project(view, 0, 0, 0)
    assert drawn[y, x] == ground
    assert lid[y, x] != ground
    opening = Image.new("L", (300, 300), 0)
    points = [_project(view, x, y, 9.0) for x, y in hole.exterior.coords]
    ImageDraw.Draw(opening).polygon(points, fill=1)
    inside = np.asarray(opening).astype(bool)
    # The far inner walls take the top of the opening; the floor shows below them.
    assert 0 < int((drawn[inside] == ground).sum()) < int(inside.sum())
    assert DETAIL_SLOT["wall_lit"] in drawn[inside]
    assert np.array_equal(drawn[lid == ground], lid[lid == ground])


def test_frames_on_disk_are_not_drawn_again(tmp_path):
    directory = tmp_path / "frames-315"
    open_frames_dir(directory, "first")
    (directory / "000_001.png").write_bytes(b"frame")
    cells = [(0, 0), (1, 0), (0, 1)]
    assert missing_cells(directory, cells) == [(0, 0), (0, 1)]
    open_frames_dir(directory, "first")
    assert missing_cells(directory, cells) == [(0, 0), (0, 1)]


def test_frames_from_other_inputs_are_thrown_away(tmp_path):
    directory = tmp_path / "frames-315"
    open_frames_dir(directory, "first")
    (directory / "000_001.png").write_bytes(b"frame")
    open_frames_dir(directory, "second")
    assert missing_cells(directory, [(1, 0)]) == [(1, 0)]


def test_a_frame_is_kept_as_the_map_and_a_layer_each_for_blossom_and_lights(tmp_path):
    names = ("tree", "tabebuia", "gulmohar_light", "window_glow", "lamp_shade", "road_track")
    slots = np.array([[DETAIL_SLOT[name] for name in names]], dtype="uint8")
    path = tmp_path / "000_000.png"

    save_frame(slots, path)

    def rgb(name):
        return tuple(bytes.fromhex(detail_colors()[name].lstrip("#")))

    def pixels(source, mode):
        picture = np.asarray(Image.open(source).convert(mode))
        return [tuple(pixel) for pixel in picture.reshape(-1, len(mode)).tolist()]

    # By day, and out of season: a tree in flower is green, and a light is what it stands on.
    base = pixels(path, "RGB")
    green = [rgb("tree"), rgb("shrub"), rgb("canopy_light")]
    assert base == [*green, rgb("road_major"), rgb("shadow_built"), rgb("road_track")]
    bloom = pixels(layer_path(path, "bloom"), "RGBA")
    assert [pixel[3] for pixel in bloom] == [0, 255, 255, 0, 0, 0]
    assert [pixel[:3] for pixel in bloom[1:3]] == [rgb("tabebuia"), rgb("gulmohar_light")]
    lights = pixels(layer_path(path, "lights"), "RGB")
    assert [*lights[:3], lights[5]] == [(0, 0, 0)] * 4
    assert (0, 0, 0) not in lights[3:5]


def test_night_lights_do_not_show_by_day():
    layers = sample_layers()
    roads = gpd.GeoDataFrame(
        {"width_m": [12.0], "road_class": ["primary"]},
        geometry=[shapely.LineString([(0, 80), (300, 80)])],
        crs=32643,
    )
    scene = build_scene(replace(layers, roads=roads))
    slots = render_detail(scene, centered_viewport(PROJECTION_B, 150, 150, 600, 600))
    for lights in (("window_glow", "window_glow_shade"), ("lamp", "lamp_shade")):
        assert np.isin(slots, [DETAIL_SLOT[name] for name in lights]).any()
    colors = detail_colors()
    assert colors["window_glow"] == colors["road_major"]
    assert colors["lamp"] == colors["road_track"]
    assert colors["lamp_shade"] == colors["shadow_built"]
    assert colors["lamp_deck"] == colors["wall_lit"]
