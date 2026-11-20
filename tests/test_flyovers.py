import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import LineString

from bengaluru.flyovers import FLYOVER_GRADE, FLYOVER_LEVEL_M, FLYOVER_M, flyovers


def roads(*rows):
    """Make roads from (points, class, bridge, layer) rows."""
    return gpd.GeoDataFrame(
        {
            "road_class": [row[1] for row in rows],
            "width_m": [10.0] * len(rows),
            "name": [None] * len(rows),
            "bridge": [row[2] for row in rows],
            "layer": [row[3] for row in rows],
        },
        geometry=[LineString(row[0]) for row in rows],
        crs=32643,
    )


def profile(line):
    points = shapely.get_coordinates(line, include_z=True)
    along = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(points[:, :2], axis=0).T))])
    return along, points[:, 2]


def test_a_long_bridge_is_a_flyover_and_a_short_one_stays_on_the_ground():
    found, raised = flyovers(
        roads(
            ([(0, 0), (400, 0)], "trunk", True, 1),
            ([(0, 50), (30, 50)], "residential", True, 1),  # over a drain
            ([(0, 90), (400, 90)], "trunk", False, 0),
            ([(0, 120), (400, 120)], "footway", True, 1),
        )
    )
    assert raised.tolist() == [True, False, False, False]
    assert len(found) == 1
    assert found.road_class.tolist() == ["trunk"]


def test_a_flyover_climbs_from_the_ground_at_each_end_no_faster_than_a_ramp():
    found, _ = flyovers(roads(([(0, 0), (400, 0)], "trunk", True, 1)))
    along, heights = profile(found.geometry.iloc[0])
    assert heights[[0, -1]].tolist() == [0, 0]
    assert heights.max() == FLYOVER_M
    assert np.all(heights[(along > 70) & (along < 330)] == FLYOVER_M)
    assert np.all(np.abs(np.diff(heights)) <= np.diff(along) * FLYOVER_GRADE + 1e-9)


def test_a_flyover_too_short_to_reach_its_height_is_a_hump():
    found, _ = flyovers(roads(([(0, 0), (100, 0)], "primary", True, 1)))
    _, heights = profile(found.geometry.iloc[0])
    assert 4.5 < heights.max() < FLYOVER_M


def test_bridges_that_run_on_from_one_another_are_one_flyover():
    found, raised = flyovers(
        roads(
            ([(0, 0), (40, 0)], "trunk", True, 1),
            ([(240, 0), (40, 0)], "trunk", True, 1),  # drawn the other way
            ([(240, 0), (300, 0)], "trunk", True, 1),
        )
    )
    assert raised.all()
    assert len(found) == 1
    along, heights = profile(found.geometry.iloc[0])
    assert along[-1] == 300
    assert heights[[0, -1]].tolist() == [0, 0]
    assert heights.max() == FLYOVER_M


def test_a_ramp_meets_the_deck_at_the_decks_height():
    # The ramp joins the deck at a point inside the deck's own line.
    found, _ = flyovers(
        roads(
            ([(0, 0), (200, 0), (400, 0)], "trunk", True, 1),
            ([(200, 0), (200, -40)], "trunk", True, 1),
        )
    )
    assert len(found) == 3
    for line in found.geometry:
        points = shapely.get_coordinates(line, include_z=True)
        joint = points[(points[:, 0] == 200) & (points[:, 1] == 0)]
        assert joint[:, 2].tolist() == [FLYOVER_M]
    ramp = next(line for line in found.geometry if line.length == 40)
    assert sorted(profile(ramp)[1][[0, -1]]) == [0, FLYOVER_M]


def test_a_bridge_over_another_does_not_join_it_and_stands_a_level_higher():
    found, _ = flyovers(
        roads(
            ([(0, 0), (400, 0)], "trunk", True, 1),
            ([(200, -200), (200, 200)], "primary", True, 2),
        )
    )
    assert len(found) == 2
    tops = sorted(profile(line)[1].max() for line in found.geometry)
    assert tops == [FLYOVER_M, FLYOVER_M + FLYOVER_LEVEL_M]


def test_a_flyover_that_changes_level_climbs_between_them():
    found, _ = flyovers(
        roads(
            ([(0, 0), (300, 0)], "trunk", True, 1),
            ([(300, 0), (600, 0)], "trunk", True, 2),
        )
    )
    along, heights = profile(found.geometry.iloc[0])
    assert heights[np.searchsorted(along, 300)] == FLYOVER_M
    assert heights.max() == FLYOVER_M + FLYOVER_LEVEL_M
    assert np.all(np.abs(np.diff(heights)) <= np.diff(along) * FLYOVER_GRADE + 1e-9)


def test_roads_with_no_flyover_give_none():
    found, raised = flyovers(roads(([(0, 0), (400, 0)], "trunk", False, 0)))
    assert found.empty
    assert not raised.any()
