import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import shapely
from PIL import Image, ImageDraw

from bengaluru.areas import get_area
from bengaluru.detail import (
    DEFAULT_VIEW,
    FRAME_PX,
    LANDMARKS_PATH,
    RENDERED_VIEWS,
    SLOTS_32,
    STYLE_PAINTERS,
    TRANSPARENT,
    VIEWS,
    _paint_flat,
    _paint_low_house,
    _paint_pitched,
    _project,
    build_scene,
    detail_colors,
    frames_dir,
    manifest_path,
    missing_cells,
    open_frames_dir,
    render_detail,
    render_frame,
    view_projection,
)
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


def test_detail_palette_stays_within_the_limit():
    colors = detail_colors()
    assert set(colors) == set(SLOTS_32)
    assert len(SLOTS_32) <= 32
    assert sorted(SLOTS_32.values()) == list(range(len(SLOTS_32)))


def test_detail_render_is_deterministic_and_grows_trees():
    layers = sample_layers()
    view = centered_viewport(PROJECTION_B, 150, 150, 600, 600)
    scene = build_scene(layers)
    first = render_detail(scene, view)
    assert np.array_equal(first, render_detail(scene, view))
    painted = set(np.unique(first).tolist())
    assert {SLOTS_32["canopy_light"], SLOTS_32["water"], SLOTS_32["wall_lit"]} <= painted


@pytest.mark.parametrize("path", sorted(Path("assets/sprites").glob("*.png")))
def test_landmark_sprites_use_only_palette_slots_and_transparency(path):
    values = set(np.unique(np.asarray(Image.open(path))).tolist())
    assert TRANSPARENT in values
    assert values - {TRANSPARENT} <= set(SLOTS_32.values())


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
    background = SLOTS_32["grass"]
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
    ground = SLOTS_32["grass"]
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
    assert SLOTS_32["wall_lit"] in drawn[inside]
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
