import geopandas as gpd
from shapely.geometry import LineString, Point

from bengaluru.areas import Area
from bengaluru.detail import PROJECTION
from bengaluru.prepare import METRIC_CRS, derived_path, metro_path
from bengaluru.tile import _drop_old_pyramids, flow_lines, metro_index, pyramid_version


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
