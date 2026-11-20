"""Find the road bridges that are flyovers, and how high each stands along its length."""

from collections import Counter, defaultdict

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import LineString

# Roads that carry traffic. A footbridge is not a flyover.
CARRIAGEWAYS = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "service",
}
# The top of a deck one level up, as most flyovers are tagged, and how much higher each
# level above that stands. OpenStreetMap gives a bridge a level, not a height.
FLYOVER_M = 6.5
FLYOVER_LEVEL_M = 5.0
FLYOVER_LEVELS = 3
# How much a deck climbs in each meter it runs. A bridge is tagged from where it leaves the
# ground, or later, so a deck starts on the ground at each open end and climbs from there.
# Real ramps are about half as steep; this keeps a short flyover from being all ramp.
FLYOVER_GRADE = 0.1
# Bridges that join into a run shorter than this stay on the ground: they cross a drain or a
# track level with their road. Of the city center's 800 runs, 700 are under 60 m and carry
# 10 km between them; the 100 longer ones carry 77 km.
FLYOVER_MIN_M = 80.0
# The farthest apart two points of a flyover's line are, so its height is known all along it.
FLYOVER_STEP_M = 8.0

COLUMNS = ("road_class", "width_m", "name")


def deck_height(layer: int) -> float:
    """Return how high a bridge's deck stands, from the level it is tagged at."""
    level = min(max(layer, 1), FLYOVER_LEVELS)
    return FLYOVER_M + (level - 1) * FLYOVER_LEVEL_M


def _keys(line: LineString) -> list[tuple[float, float]]:
    """Return a line's points, each one a name for the place two roads may share."""
    points = [(round(x, 3), round(y, 3)) for x, y in shapely.get_coordinates(line)]
    return [point for index, point in enumerate(points) if not index or point != points[index - 1]]


def _edges(lines: list[LineString]) -> list[tuple[int, list[tuple[float, float]]]]:
    """Cut each road where another meets it, and return the pieces with the road they are of.

    Roads meet only at a point they share. One that crosses over another shares none with it.
    """
    roads = [_keys(line) for line in lines]
    shared = Counter(key for keys in roads for key in keys)
    edges = []
    for road, keys in enumerate(roads):
        start = 0
        for index in range(1, len(keys)):
            if index == len(keys) - 1 or shared[keys[index]] > 1:
                edges.append((road, keys[start : index + 1]))
                start = index
    return edges


def _branch(first: int, edges: list, meeting: dict) -> list[tuple[int, bool]]:
    """Return the edges that run on from one another through `first`, with no road joining
    along the way, in order, each with whether it is walked from its start."""
    run, seen = [(first, True)], {first}
    for onward in (True, False):
        while True:
            edge, forward = run[-1] if onward else run[0]
            node = edges[edge][1][-1 if forward == onward else 0]
            others = [end for end in meeting[node] if end[0] != edge]
            if len(meeting[node]) != 2 or len(others) != 1 or others[0][0] in seen:
                break
            other, at_start = others[0]
            seen.add(other)
            step = (other, at_start == onward)
            if onward:
                run.append(step)
            else:
                run.insert(0, step)
    return run


def _along(points: np.ndarray) -> np.ndarray:
    """Return how far along its line each point is."""
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))])


def _start(branch: list[tuple[int, bool]], edges: list) -> tuple[float, float]:
    edge, forward = branch[0]
    return edges[edge][1][0 if forward else -1]


def _heights(along: np.ndarray, wanted: np.ndarray, start: float, end: float) -> np.ndarray:
    """Return a deck's height at each point: what its bridges are tagged for, but climbing no
    faster than a deck does, from the height it has to start at to the one it has to end at."""
    grade = max(FLYOVER_GRADE, abs(end - start) / max(along[-1], 1e-6))
    heights = wanted.copy()
    heights[0], heights[-1] = start, end
    steps = np.diff(along) * grade
    for index in range(1, len(heights)):
        heights[index] = min(heights[index], heights[index - 1] + steps[index - 1])
    for index in range(len(heights) - 2, -1, -1):
        heights[index] = min(heights[index], heights[index + 1] + steps[index])
    return heights


def _groups(edges: list, meeting: dict) -> list[int]:
    """Return for each edge the number of the run of joined bridges it belongs to."""
    group = list(range(len(edges)))

    def find(edge: int) -> int:
        while group[edge] != edge:
            group[edge] = group[group[edge]]
            edge = group[edge]
        return edge

    for ends in meeting.values():
        for edge, _ in ends[1:]:
            group[find(edge)] = find(ends[0][0])
    return [find(edge) for edge in range(len(edges))]


def flyovers(roads: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, np.ndarray]:
    """Return the flyovers among the roads, and which of the roads they are.

    A flyover is a line with a height at each point: a stretch of bridge between two places
    where it meets the ground or another bridge. `roads` are in meters, each with whether it
    is a `bridge` and the `layer` it is tagged at.
    """
    raised = np.zeros(len(roads), dtype=bool)
    chosen = np.flatnonzero(
        roads["bridge"].to_numpy(dtype=bool)
        & roads.road_class.isin(CARRIAGEWAYS).to_numpy()
        & (roads.geometry.geom_type == "LineString").to_numpy()
    )
    edges = _edges(list(roads.geometry.iloc[chosen]))
    meeting = defaultdict(list)
    for edge, (_, keys) in enumerate(edges):
        meeting[keys[0]].append((edge, True))
        meeting[keys[-1]].append((edge, False))
    wanted = [deck_height(int(layer)) for layer in roads["layer"].iloc[chosen]]
    lengths = [LineString(keys).length for _, keys in edges]
    groups = _groups(edges, meeting)
    run_length = Counter()
    for edge, group in enumerate(groups):
        run_length[group] += lengths[edge]

    def end_height(node: tuple[float, float]) -> float:
        # An open end is on the ground. Where bridges meet, they meet at the lowest's height.
        ends = meeting[node]
        return min(wanted[edges[edge][0]] for edge, _ in ends) if len(ends) > 1 else 0.0

    rows, lines, done = [], [], set()
    for first in range(len(edges)):
        if first in done or run_length[groups[first]] < FLYOVER_MIN_M:
            continue
        branch = _branch(first, edges, meeting)
        done.update(edge for edge, _ in branch)
        points, tagged = [_start(branch, edges)], []
        for edge, forward in branch:
            road, keys = edges[edge]
            points.extend(keys[1:] if forward else keys[-2::-1])
            tagged.extend([wanted[road]] * (len(keys) - 1))
        xy = shapely.get_coordinates(shapely.segmentize(LineString(points), FLYOVER_STEP_M))
        along = _along(xy)
        # Each point is as high as the stretch it is on, and where two meet, as the lower.
        marks, last = _along(np.array(points)), len(tagged) - 1
        before = np.clip(np.searchsorted(marks, along - 1e-6, side="left") - 1, 0, last)
        after = np.clip(np.searchsorted(marks, along + 1e-6, side="right") - 1, 0, last)
        wish = np.minimum(np.array(tagged)[before], np.array(tagged)[after])
        z = _heights(along, wish, end_height(points[0]), end_height(points[-1]))
        longest = max(branch, key=lambda step: lengths[step[0]])[0]
        source = roads.iloc[chosen[edges[longest][0]]]
        rows.append({name: source[name] for name in COLUMNS})
        lines.append(LineString(np.column_stack([xy, z])))
        raised[[chosen[edges[edge][0]] for edge, _ in branch]] = True
    if not rows:
        return empty_flyovers(roads.crs), raised
    return gpd.GeoDataFrame(rows, geometry=lines, crs=roads.crs), raised


def empty_flyovers(crs) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({name: [] for name in COLUMNS}, geometry=[], crs=crs)
