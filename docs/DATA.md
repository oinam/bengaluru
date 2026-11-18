# Data register

Every source used by the pipeline, recorded before first use. Add a row when you add a
source; never remove one. "Used for" must be specific.

| Source | Version / date fetched | License | URL | Used for | Attribution text |
|---|---|---|---|---|---|
| OpenStreetMap | Overpass, 2026-11-16 (`vidhana-soudha`) | ODbL 1.0 | https://www.openstreetmap.org/copyright | roads, metro and rail, the metro's route relations for its lines' names and colors, water, parks, land use, POIs, names, boundaries, buildings | "© OpenStreetMap contributors" |
| OpenStreetMap, as the Geofabrik extract `asia/india/southern-zone` | `southern-zone-261116.osm.pbf`, 533 MB, data to 2026-11-16T21:22:36Z, fetched 2026-11-17 (`central`, `bbmp`) | ODbL 1.0 | https://download.geofabrik.de/asia/india/southern-zone.html | the same as the row above, for the areas too large for Overpass | "© OpenStreetMap contributors" |
| Google Open Buildings v3 | v3, S2 level 6 cell `3baf`, 2026-11-16 (`vidhana-soudha`) | CC BY 4.0 or ODbL 1.0, user's choice; we use CC BY 4.0 | https://sites.research.google/gr/open-buildings/ | building footprints where OSM has none | "Google Open Buildings, CC BY 4.0" |
| Google Open Buildings 2.5D Temporal | v1, 2023-06-30 epoch, `gs://open-buildings-temporal-data/v1/geotiffs/3bae4_2023_06_30/`, 2026-11-16 (`vidhana-soudha`) | CC BY 4.0 or ODbL 1.0, user's choice; we use CC BY 4.0 | https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_Research_open-buildings-temporal_v1 | building heights (band 2, `building_height`, meters, 0 to 100) | "Google Open Buildings 2.5D Temporal, CC BY 4.0. Contains modified Copernicus Sentinel data" |
| ESA WorldCover 2021 | v200, tile `N12E075`, 2026-11-16 (`vidhana-soudha`) | CC BY 4.0 | https://esa-worldcover.org/en/data-access | ground class (trees, grass, built, water); never sampled for color | "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" |

Fetch dates and exact file names are written by `bengaluru fetch`, which appends to
`data/raw/<area>/SOURCES.txt` and reminds you to update this table.

## Licenses as read on 2026-11-16

Each source's own page, read on the day of the first fetch.

- **OpenStreetMap** (https://www.openstreetmap.org/copyright): "licensed under the Open
  Data Commons Open Database License". It asks for credit to OpenStreetMap and for making
  clear the data is under the ODbL, and says "If you alter or build upon our data, you
  may distribute the result only under the same license." The rendered map is a picture
  made from the data, which needs the credit; the merged building layer in
  `data/derived/` is a database built on OSM, and we do not distribute it.
- **Open Buildings v3** (https://sites.research.google/gr/open-buildings/): "shared under
  the Creative Commons Attribution (CC BY-4.0) license and the Open Data Commons Open
  Database License (ODbL) v1.0 license. As the user, you can pick which of the two
  licenses you prefer". Detections carry a confidence of 0.65 to 1.0.
- **Open Buildings 2.5D Temporal** (the Earth Engine catalog page above): the same choice
  of CC BY 4.0 or ODbL 1.0. `building_height` is meters above the terrain, 0 to 100, on
  0.5 m pixels with an effective resolution of 4 m, yearly from 2016 to 2023. It is
  derived from Copernicus Sentinel-2 data.
- **ESA WorldCover 2021 v200** (https://esa-worldcover.org/en/data-access): "provided
  free of charge, without restriction of use", under CC BY 4.0, with the attribution
  text in the table.

## Licenses as read on 2026-11-17

- **Geofabrik extract** (https://download.geofabrik.de/asia/india/southern-zone.html):
  "Data processed by Geofabrik GmbH and created by OpenStreetMap Contributors" and
  "License: ODbL 1.0". It is OpenStreetMap's data cut to a region, under OpenStreetMap's
  license and credit; Geofabrik asks for nothing more.

## Candidates

Sources the plan expects to use and has not touched yet. Each moves into the register
above, with its license read again on the day, before any code touches it.

- **Copernicus GLO-30 DEM**: Copernicus DEM license, free with attribution.
- **A tree canopy height product**: not chosen. Find one that is openly licensed for
  derivative works and confirm it with Brajeshwar before use.
- **Wikimedia Commons**: per file, CC BY, CC BY-SA, CC0, or public domain only.
