import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import LineString

from bengaluru.osm import Feature
from bengaluru.prepare import (
    assign_heights,
    duplicate_mask,
    mostly_on_mask,
    osm_buildings,
    rails,
)


def frame(*polygons):
    return gpd.GeoDataFrame(geometry=list(polygons), crs=32643)


def test_duplicate_mask_separates_touching_from_duplicate():
    osm = frame(shapely.box(0, 0, 10, 10))
    candidates = frame(
        shapely.box(1, 1, 11, 11),  # mostly the same building
        shapely.box(9, 9, 30, 30),  # clips a corner only
        shapely.box(50, 50, 60, 60),  # unrelated
    )
    intersects, duplicate = duplicate_mask(candidates, osm)
    assert intersects.tolist() == [True, True, False]
    assert duplicate.tolist() == [True, False, False]


def test_mostly_on_mask_flags_mostly_covered_polygons():
    water = shapely.box(0, 0, 10, 10)
    candidates = frame(shapely.box(1, 1, 5, 5), shapely.box(8, 0, 18, 10))
    assert mostly_on_mask(candidates, water).tolist() == [True, False]


def test_mostly_on_mask_counts_overlapping_pieces_once():
    # Two road pieces that overlap under the footprint cover 40% of it, not 80%.
    pieces = [shapely.box(0, 0, 4, 10), shapely.box(0, 0, 4, 10), shapely.box(50, 50, 60, 60)]
    candidates = frame(shapely.box(0, 0, 10, 10), shapely.box(0, 0, 6, 10))
    assert mostly_on_mask(candidates, pieces).tolist() == [False, True]
    assert mostly_on_mask(candidates, []).tolist() == [False, False]


def test_assign_heights_prefers_tag_then_raster_then_default():
    buildings = frame(
        shapely.box(0, 0, 10, 10), shapely.box(20, 0, 30, 10), shapely.box(40, 0, 50, 10)
    )
    buildings["tagged_height"] = [12.0, np.nan, np.nan]
    result = assign_heights(buildings, np.array([5.0, 7.0, np.nan]))
    assert result["height_m"].tolist() == [12.0, 7.0, 3.5]
    assert result["height_source"].tolist() == ["osm_tag", "temporal_2023", "default"]


def test_underground_structures_are_not_buildings():
    ring = shapely.box(77.59, 12.97, 77.591, 12.971)
    tagged = [
        {"building": "yes"},
        {"building": "train_station", "location": "underground"},
        {"building": "train_station", "layer": "-1"},
        {"building": "train_station", "building:levels": "0"},
        {"building": "roof", "layer": "1"},
    ]
    features = [Feature("way", index, tags, ring) for index, tags in enumerate(tagged)]
    assert osm_buildings(features).building_id.tolist() == ["osm/way/0", "osm/way/4"]


def test_rails_keep_track_in_the_open_and_mark_viaducts():
    line = LineString([(77.59, 12.97), (77.60, 12.97)])
    tagged = [
        {"railway": "rail"},
        {"railway": "rail", "bridge": "yes"},
        {"railway": "subway", "tunnel": "yes", "layer": "-2"},
        {"railway": "subway", "bridge": "viaduct", "layer": "2"},
        {"railway": "abandoned"},
        {"railway": "platform"},
    ]
    features = [Feature("way", index, tags, line) for index, tags in enumerate(tagged)]
    tracks = rails(features)
    assert tracks.rail.tolist() == ["rail", "rail", "subway"]
    assert tracks.elevated.tolist() == [False, False, True]
