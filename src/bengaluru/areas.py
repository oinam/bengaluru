"""Named areas the pipeline can build. Bounding boxes come from docs/PLAN.md."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    name: str
    south: float
    west: float
    north: float
    east: float
    # A Geofabrik extract to cut OSM from; small areas use Overpass instead.
    osm_extract: str | None = None
    # Coarser height sampling keeps large areas in memory; None keeps the source's 0.5 m.
    height_res_m: float | None = None

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return (west, south, east, north) in degrees."""
        return (self.west, self.south, self.east, self.north)

    @property
    def center(self) -> tuple[float, float]:
        """Return (lon, lat) of the bounding box center."""
        return ((self.west + self.east) / 2, (self.south + self.north) / 2)


AREAS = {
    # The Phase 0 test patch: Vidhana Soudha, the High Court, and Cubbon Park, with UB City
    # and the stadiums at its edges. Tall enough that a north-up 2048 px frame is full.
    "vidhana-soudha": Area("vidhana-soudha", 12.965, 77.580, 12.990, 77.605),
    # Inside the Outer Ring Road, the Phase 1 map.
    "central": Area(
        "central",
        12.90,
        77.52,
        13.05,
        77.68,
        osm_extract="asia/india/southern-zone",
        height_res_m=2.0,
    ),
    # The BBMP area, the Phase 3 map, carried north past the city's edge to take in
    # Kempegowda International Airport, which OpenStreetMap bounds at 13.2113 N.
    "bbmp": Area(
        "bbmp",
        12.83,
        77.46,
        13.23,
        77.78,
        osm_extract="asia/india/southern-zone",
        height_res_m=2.0,
    ),
}


def get_area(name: str) -> Area:
    try:
        return AREAS[name]
    except KeyError:
        raise SystemExit(f"Unknown area {name!r}. Known areas: {', '.join(AREAS)}") from None
