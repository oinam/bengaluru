import geopandas as gpd
import numpy as np
import pyvips
from shapely.geometry import LineString, Point

from bengaluru.areas import Area
from bengaluru.detail import PROJECTION
from bengaluru.palettes import BLOSSOM, LIGHTS
from bengaluru.prepare import METRIC_CRS, derived_path, metro_path
from bengaluru.tile import (
    LAYER_TILE_PX,
    _drop_old_pyramids,
    _save_lights,
    flow_lines,
    halved_lights,
    layer_key,
    metro_index,
    pyramid_version,
    pyramids_of,
)


def test_pyramid_version_follows_the_frame_bytes(tmp_path):
    frame = tmp_path / "000_000.png"
    frame.write_bytes(b"first")
    first = pyramid_version([frame], 1)
    assert pyramid_version([frame], 1) == first
    assert pyramid_version([frame], 2) != first
    frame.write_bytes(b"second")
    assert pyramid_version([frame], 1) != first


def test_flow_lines_keep_the_drawn_direction(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    area = Area("test", 0.0, 0.0, 1.0, 1.0)
    path = derived_path(area)
    path.parent.mkdir(parents=True)
    river = LineString([(0.0, 0.0), (100.0, 0.0)])
    frame = gpd.GeoDataFrame(
        {"waterway": ["river"], "width_m": [30.0], "name": ["Test"]},
        geometry=[river],
        crs=METRIC_CRS,
    )
    frame.to_file(path, layer="waterways", driver="GPKG")

    [line] = flow_lines(area, 10.0, 20.0)

    a, _, d, _ = PROJECTION.matrix
    assert line["width"] == 30
    assert line["points"] == [[10, 20], [round(a * 100 + 10), round(d * 100 + 20)]]
    assert line["name"] == "Test"


def test_the_metro_index_carries_lines_and_stations_on_the_ground(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    area = Area("test", 0.0, 0.0, 1.0, 1.0)
    path = metro_path(area)
    path.parent.mkdir(parents=True)
    gpd.GeoDataFrame(
        {
            "line": ["Purple", "Red"],
            "colour": ["#e542de", None],
            "open": [True, False],
            "proposed": [False, True],
            "level": ["raised", "ground"],
        },
        geometry=[LineString([(0.0, 0.0), (100.0, 0.0)])] * 2,
        crs=METRIC_CRS,
    ).to_file(path, layer="metro", driver="GPKG")
    gpd.GeoDataFrame(
        {"name": ["Majestic"], "open": [True], "proposed": [False], "level": ["raised"]},
        geometry=[Point(100.0, 0.0)],
        crs=METRIC_CRS,
    ).to_file(path, layer="stations", driver="GPKG")

    index = metro_index(area, 10.0, 20.0)

    a, _, d, _ = PROJECTION.matrix
    end = [round(a * 100 + 10), round(d * 100 + 20)]
    assert index["raised_px"] > 0
    assert index["lines"] == [
        {
            "line": "Purple",
            "colour": "#e542de",
            "open": True,
            "proposed": False,
            "level": "raised",
            "points": [[10, 20], end],
        },
        {
            "line": "Red",
            "colour": None,
            "open": False,
            "proposed": True,
            "level": "ground",
            "points": [[10, 20], end],
        },
    ]
    assert index["stations"] == [
        {
            "name": "Majestic",
            "x": end[0],
            "y": end[1],
            "open": True,
            "proposed": False,
            "level": "raised",
        }
    ]


def test_the_metro_index_is_empty_where_there_is_no_metro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    index = metro_index(Area("test", 0.0, 0.0, 1.0, 1.0), 0.0, 0.0)
    assert index["lines"] == []
    assert index["stations"] == []


def test_flow_lines_name_rivers_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    area = Area("test", 0.0, 0.0, 1.0, 1.0)
    path = derived_path(area)
    path.parent.mkdir(parents=True)
    frame = gpd.GeoDataFrame(
        {"waterway": ["stream", "river"], "width_m": [4.0, 30.0], "name": ["Brook", None]},
        geometry=[LineString([(0.0, 0.0), (50.0, 0.0)]), LineString([(0.0, 9.0), (50.0, 9.0)])],
        crs=METRIC_CRS,
    )
    frame.to_file(path, layer="waterways", driver="GPKG")

    assert [line.get("name") for line in flow_lines(area, 0.0, 0.0)] == [None, None]


def test_only_the_pyramids_no_view_points_at_are_dropped(tmp_path):
    for name in ("old", "kept"):
        (tmp_path / "pyramid" / name).mkdir(parents=True)
    _drop_old_pyramids(tmp_path, {"315": {"pyramid": "kept"}})
    assert [path.name for path in (tmp_path / "pyramid").iterdir()] == ["kept"]


def test_a_view_keeps_its_layers_pyramids_with_its_map(tmp_path):
    for name in ("old", "map", "bloom", "lights"):
        (tmp_path / "pyramid" / name).mkdir(parents=True)
    views = {"315": {"pyramid": "map", "bloom": "bloom", "lights": "lights", "inputs": "old"}}
    assert pyramids_of(views) == {"map", "bloom", "lights"}
    _drop_old_pyramids(tmp_path, views)
    assert sorted(path.name for path in (tmp_path / "pyramid").iterdir()) == [
        "bloom",
        "lights",
        "map",
    ]


def test_the_layer_key_tells_each_flowering_tree_by_its_colors_and_months():
    key = layer_key()
    assert set(key["bloom"]) == set(BLOSSOM)
    for kind, blossom in key["bloom"].items():
        assert blossom["colors"][0] == BLOSSOM[kind]
        assert all(1 <= month <= 12 for month in blossom["months"])


def test_a_layer_has_its_own_pyramid_version(tmp_path):
    frame = tmp_path / "000_000.png"
    frame.write_bytes(b"same")
    assert pyramid_version([frame], 1) != pyramid_version([frame], 1, 1024, ":bloom")


WINDOW = tuple(bytes.fromhex(LIGHTS["window"].lstrip("#")))


def lit(height: int, width: int, windows: list[tuple[int, int]]) -> np.ndarray:
    """A black picture with a lit window, two pixels square, at each row and column given."""
    picture = np.zeros((height, width, 3), dtype=np.uint8)
    for row, column in windows:
        picture[row : row + 2, column : column + 2] = WINDOW
    return picture


def test_a_lone_window_fades_as_the_lights_halve_and_keeps_its_color():
    once = halved_lights(pyvips.Image.new_from_array(lit(8, 8, [(2, 4)])))
    twice = halved_lights(once)
    assert (once.width, once.height) == (4, 4)
    # Four lit pixels to one: twice their mean is past a full light, and held to one.
    assert tuple(once.numpy()[1, 2]) == WINDOW
    assert tuple(twice.numpy()[0, 1]) == tuple(round(value / 2) for value in WINDOW)
    assert once.numpy().sum() == sum(WINDOW)


def test_lights_built_close_together_stay_bright_from_afar():
    def from_afar(windows: list[tuple[int, int]]) -> int:
        lights = pyvips.Image.new_from_array(lit(8, 8, windows))
        for _ in range(3):
            lights = halved_lights(lights)
        return int(lights.numpy()[0, 0].max())

    crowded = [(row, column) for row in (0, 4) for column in (0, 4)]
    assert from_afar(crowded) == 255
    assert from_afar([(0, 0)]) < 80


def test_an_odd_picture_of_lights_halves_to_the_size_a_pyramid_expects():
    half = halved_lights(pyvips.Image.new_from_array(lit(5, 7, [(3, 5)])))
    assert (half.width, half.height) == (4, 3)
    assert half.numpy()[1:, 2:].any()


def test_the_lights_pyramid_has_every_level_down_to_one_pixel(tmp_path):
    frames = []
    for index, windows in enumerate(([(10, 10)], [(600, 300)])):
        frame = tmp_path / f"000_{index:03d}.png"
        pyvips.Image.new_from_array(lit(LAYER_TILE_PX, LAYER_TILE_PX, windows)).write_to_file(
            str(frame)
        )
        frames.append(frame)
    pyramid = tmp_path / "pyramid" / "area"
    pyramid.parent.mkdir()
    full = _save_lights(frames, 2, pyramid)
    assert (full.width, full.height) == (2 * LAYER_TILE_PX, LAYER_TILE_PX)
    files = pyramid.parent / "area_files"
    assert sorted(path.name for path in pyramid.parent.iterdir()) == ["area.dzi", "area_files"]
    assert 'Width="2048"' in pyramid.with_suffix(".dzi").read_text()
    assert sorted(int(level.name) for level in files.iterdir()) == list(range(12))
    assert sorted(path.name for path in (files / "11").iterdir()) == ["0_0.webp", "1_0.webp"]
    top = pyvips.Image.new_from_file(str(files / "11" / "1_0.webp"))
    assert tuple(top.numpy()[600, 300][:3]) == WINDOW
    half = pyvips.Image.new_from_file(str(files / "10" / "0_0.webp"))
    assert tuple(half.numpy()[5, 5][:3]) == WINDOW
    one = pyvips.Image.new_from_file(str(files / "0" / "0_0.webp"))
    assert (one.width, one.height) == (1, 1)
