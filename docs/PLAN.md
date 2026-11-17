# Plan

## Status

*17 November 2026. Brajeshwar said go: build the whole city. It is built. The central
area finished at 08:59 and the BBMP area at 11:42, four views each, and the viewer opens
on BBMP (`mise run dev`, http://localhost:8655). Courtyards were then opened in the
drawing code, which made every view stale: central was drawn again by 12:19, and BBMP
got two of its four views done before the day's window closed at 13:40. The night's work
at 23:00 draws the other two, about 70 minutes, and only then does the viewer change
over; until then it shows the first BBMP build, whole, with the lids. After that the
night builds a view again only when the data or the drawing code changes. Nothing is
online. The look is still Manipur's, unchanged; "What looks wrong" below is the list to
choose from, and `20261117-091959_look-options.png` in `out/central/` shows four
candidate answers to its first items. Phase 0's frames of the test patch are in
`out/vidhana-soudha/`.*

### BBMP numbers, 2026-11-17

The `bbmp` area: 12.83–13.14 N, 77.46–77.78 E, 34.7 × 34.3 km, about 1,190 km².

| | |
|---|---|
| OSM buildings | 799,662; 91 underground ones left out |
| Open Buildings v3 footprints in the box | 1,906,910 |
| of those, under 0.70 confidence | 295,547 dropped |
| duplicates of an OSM building | 526,069 dropped |
| on water, a major road, or a viaduct | 1,216, 7,790, and 79 dropped |
| Open Buildings kept | 1,076,209 |
| **Buildings drawn** | **1,875,702**, 43% from OSM and 57% from Open Buildings |
| Heights from the 2.5D raster / OSM tags / a default | 1,813,358 / 13,998 / 48,346 |
| Height, median / 95th percentile / tallest | 6.0 m / 12.2 m / 170 m, the cap |
| Railway and metro track in the open | 715 km, 248 km of it on viaducts (each track counted) |
| Trees placed | 3,501,976 |
| Named places in the search index | 77,121 |
| Canvas, each view | 71,680 × 36,864 px (69,632 wide for the two side views), 630 and 612 frames |

| Step | Time on this Mac |
|---|---|
| `fetch` | 16 min, the Geofabrik extract already on disk |
| `prepare` | 13 min, then 4 min placing the trees |
| `build`, four views rendered and tiled | 2 h 26 min: about 33 min of frames a view with six workers, 4 min tiling |
| Tiles on disk | 3.9 GB in 53,119 files |

No process went over 5.1 GB, and the Mac kept 37% to 57% of its memory free through the
build. `20261117-114341_four-views.png` in `out/bbmp/` shows the four views side by side,
and three crops beside it show Whitefield, Electronic City, and Yelahanka.

### Central numbers, 2026-11-17

The `central` area: 12.90–13.05 N, 77.52–77.68 E, 17.4 × 16.6 km, 288 km².

| | |
|---|---|
| OSM buildings | 442,807; 37 underground ones left out |
| Open Buildings v3 footprints in the box | 845,234 |
| of those, under 0.70 confidence | 145,432 dropped |
| duplicates of an OSM building | 295,120 dropped |
| on water, a major road, or a viaduct | 799, 3,446, and 42 dropped |
| Open Buildings kept | 400,395 |
| **Buildings drawn** | **842,730**, 52% from OSM and 48% from Open Buildings |
| Heights from the 2.5D raster / OSM tags / a default | 827,245 / 7,013 / 8,472 |
| Height, median / 95th percentile / tallest | 6.8 m / 12.2 m / 161.5 m |
| Railway and metro track in the open | 353 km, 116 km of it on viaducts (each track counted) |
| Trees placed | 726,961 |
| Named places in the search index | 47,809 |
| Canvas, each view | 36,864 × 18,432 px (34,816 wide for the two side views), 162 frames |

| Step | Time on this Mac |
|---|---|
| `fetch` | 19 min: the 533 MB Geofabrik extract, then 15 min cutting the area out of it |
| `prepare` | 3 min 48 s, at a peak of 4.0 GB |
| `build`, four views rendered and tiled | 22 min: about 4.5 min of frames a view with six workers, the rest tiling |
| Tiles on disk | 978 MB in 13,555 files |

The render workers hold 1.0 to 1.6 GB each whatever the area's size, since each reads
its frame's buildings from disk. `20261117-121949_four-views.png` in `out/central/` shows
the four views side by side.

### Phase 0 numbers, 2026-11-16

The `vidhana-soudha` patch: 12.965–12.990 N, 77.580–77.605 E, 2.7 × 2.8 km, 7.5 km²,
about a third of it Cubbon Park. Drawn with Manipur's projection, palette, and building
vocabulary, unchanged.

| | |
|---|---|
| OSM buildings | 6,041 |
| Open Buildings v3 footprints in the box | 13,469 |
| of those, under 0.70 confidence | 3,058 dropped |
| duplicates of an OSM building | 4,801 dropped |
| on water or on a major road | 97 dropped |
| Open Buildings kept | 5,513 |
| **Buildings drawn** | **11,435**, 52% from OSM and 48% from Open Buildings |
| Heights from the 2.5D raster | 10,846 (94.8%) |
| Heights from OSM tags | 396 (3.5%) |
| No height, so a default by footprint | 193 (1.7%) |
| Height, median / 95th percentile / tallest | 8.0 m / 16.0 m / 115 m |
| 11 m and taller, drawn as blocks | 2,585; 116 are over 30 m |
| Ground, by WorldCover | 62% built, 35% trees, 2% grass, 1% other |
| Trees placed | 30,864; OSM maps 304 single trees and 6 tree rows here |

| Step | Time on this Mac |
|---|---|
| `fetch` | 10 min, nearly all of it the one 569 MB Open Buildings cell, which is kept and covers the whole city, and four failed Overpass tries before the fifth worked |
| `plan` | 3 s |
| `prepare` | 6.5 s |
| `render`, the flat frame and the whole patch at 7,832 × 4,156 px | 1.3 s and 1.9 s |
| `detail`, one near-final 2048 px frame | 3.2 s, at a peak of 1.3 GB of memory |

Two runs of `detail` gave the same pixels. On disk: 19 MB of sources for the patch, 5 MB
derived, 3 MB of pictures.

The whole patch also builds: four views of 6,144 × 4,096 px, six frames each, rendered
and tiled in 54 s, as 565 files and 25 MB of tiles. `20261116-183612_four-views.png`
shows the four side by side.

### What looks wrong

The park, the lakes, the road layout, and the massing and heights of the buildings come
out right. These do not:

1. ~~The metro station is a building on the road, and the metro is not drawn.~~ Fixed
   on 2026-11-17: underground structures are left out, track is drawn on the ground, and
   viaducts as a deck on piers. Flyovers for roads are still flat on the ground.
2. **The landmarks are plain blocks.** Vidhana Soudha has no dome and a blue roof; the
   High Court is cream, not red. Expected until Phase 2, but they are what a resident
   looks for first.
3. ~~Courtyards and stadium bowls are gray plates at roof height.~~ Fixed on 2026-11-17:
   a hole in a footprint is an opening down to the ground, with the inner walls that
   face the viewer. Kanteerava Stadium shows its field. Before and after are in
   `out/vidhana-soudha/20261117-115500_courtyards-before-after.png`. A tree in the near
   half of a courtyard still stands in front of the wing that should hide its trunk.
4. **The roofs are Imphal's.** Mid-size buildings get red, orange, and blue pitched tin
   roofs. This part of Bengaluru is flat concrete terraces, with red tile only on the
   older bungalows.
5. **The towers are tall cream boxes** with dotted windows: UB City and the towers north
   of the park. No glass, no setbacks, no repeated storeys.
6. **Cubbon Park is one solid forest.** WorldCover calls nearly the whole park "trees",
   so the lawns, the bamboo, and the open ground around the bandstand are gone. Outside
   the park the avenue trees are thin: streets get almost none.
7. **The ground between buildings is sandy.** Manipur's color for built-up land reads as
   bare earth, which makes the office quarter look dusty.

8. **Open ground inside the city is drawn as paddy.** WorldCover calls the Race Course,
   the golf course, and some lawns "cropland", and Manipur's renderer draws cropland as
   paddy fields with bunds. Seen in the central build, 2026-11-17.

## What this is

A zoomable, searchable isometric pixel-art map of Bengaluru, in the same family and
method as the Manipur map: rendered procedurally from open data, with landmarks as drawn
sprites. It gets the geography right (every road, lake, park, and building footprint
where it really is, at its real height, with its name searchable) and draws buildings
from a small vocabulary of types, the way SimCity 2000 did.

As of 2026-11-16 nobody has made one. The Isometric Cities directory lists three Indian
maps (Imphal, Mumbai, Chennai), and a web search finds no pixel-art map of Bengaluru.

## Why this way

Pixel Chennai and Isometric Mumbai repaint a code-drawn map with an image model, which
needs a GPU and costs more the bigger the city. The Manipur map showed that the
procedural render stands on its own, and Bengaluru is better mapped than Imphal: dense
OpenStreetMap, full Open Buildings coverage with heights, many named lakes and parks.
The AI layer stays parked (see `CLAUDE.md`).

## Honest expectations

A lab piece, like the Manipur map. What it can be: the first isometric map of Bengaluru,
shared widely by people who live there. What it will not be: a photograph.

**Scale.** The main cost is size, not code. These are extrapolations from Imphal's
Phase 1 numbers (161 km² box, 262,527 buildings, 645 megapixels at 0.5 m/px, 162 frames
in about 150 seconds per view), to be replaced with measurements in Phase 0:

- The BBMP box below is about 1,200 km², about 7.5 times Imphal's.
- Buildings: a guess of 1.5 to 2 million.
- Canvas: about 5 gigapixels per view at 0.5 m/px; four views make about 20.
- Render: tens of minutes per view on this Mac, if it scales with area. Memory, not
  time, is the likelier limit, so the build must stay frame by frame and resumable, as
  the Manipur `build` command already is.
- Disk: tens of GB of tiles across four views. Plan for the external drive from day one.

**Time.** Phase 0 is a session or two, since the pipeline exists. Phase 1 is two to
four weekends, mostly waiting on renders.

**Money.** Effectively zero to build. Hosting on Cloudflare R2 costs about $0.015 per GB
a month with no download fees, so a few dollars a month at this size.

## Data sources

All free and all permit derivative works with attribution. Register each in `DATA.md`
before use; the candidates are listed there.

| Source | What we take | Notes |
|---|---|---|
| OpenStreetMap | roads, metro and rail, lakes, parks, land use, POIs, names, boundaries, some buildings | Geofabrik `india/southern-zone` extract, clipped. Far denser than Imphal. |
| Google Open Buildings v3 | footprints | fills OSM gaps; confidence threshold and IoU dedupe as in Manipur |
| Google Open Buildings 2.5D Temporal | heights | sampled per footprint |
| ESA WorldCover 2021 | ground class | parks, lakes, scrub, built-up |
| Copernicus GLO-30 DEM | terrain | the plateau is gentle; maybe only for lake basins and hillocks |
| Tree canopy height (candidate) | where trees stand and how tall | Pixel Chennai used one. Find an openly licensed product and check it before use. |
| Wikimedia Commons | landmark reference photos | per-file license, as in Manipur |

Bounding boxes, to be confirmed in Phase 0:

- Test patch, Vidhana Soudha and Cubbon Park (`vidhana-soudha`): 12.965–12.990 N,
  77.580–77.605 E (about 2.7 × 2.8 km), widened in Phase 0 so a north-up frame is full
- Central Bengaluru, inside the Outer Ring Road (`central`): about 12.90–13.05 N,
  77.52–77.68 E
- BBMP area (`bbmp`): about 12.83–13.14 N, 77.46–77.78 E
- Local metric CRS: UTM 43N, EPSG:32643

## Architecture

The Manipur pipeline, unchanged in shape: `fetch`, `prepare`, `render`, `tile`, then a
`build` that renders and tiles one view at a time and resumes if stopped. Viewer:
OpenSeadragon with search, shareable links, four 90° views with north up by default,
labels, and the Manipur viewer's later lessons (smooth while zoomed out, crisp when
zoomed in; a link-preview image; a zoom-in film for sharing).

How to reuse the Manipur code is the first decision (below). The default is to copy
its `src/manipur`, `web/`, and `tools/` in as the starting point, strip what is
Imphal-only (aircraft timetable, Sangai, phumdis, Loktak water), and record the
Manipur commit it started from. A shared package is premature with two cities.

Bengaluru-specific work:

- **Lakes** carry the map the way the Kangla moat and Loktak carry Imphal: Ulsoor,
  Sankey, Hebbal, Bellandur, Agara, Madiwala, Lalbagh's lake.
- **Trees.** Avenue trees and Cubbon Park and Lalbagh canopy are the city's signature.
  Tree placement from WorldCover alone will look wrong; a canopy source is worth finding.
- **Namma Metro** lines from OSM, elevated, drawn as viaducts. Moving trains are a later
  idea, like the planes over Imphal.
- **Tall buildings.** Bengaluru has towers Imphal lacks; the block type needs repeated
  storeys that read well at 20+ floors.

## Tile vocabulary (first cut)

Brajeshwar chooses from rendered options. Starting points: the Manipur vocabulary
(houses, shophouses, sheds, blocks) plus Bengaluru's own: flat-roofed RCC houses with
terrace water tanks, apartment blocks, glass office towers in the tech parks, and
red-tiled older houses in Basavanagudi and Malleshwaram.

Landmark candidates, for Brajeshwar to choose from and order: Vidhana Soudha, Attara
Kacheri (the High Court), the Lalbagh Glass House, Bangalore Palace, Tipu Sultan's Summer
Palace, Dodda Basavana Gudi (the Bull Temple), St. Mary's Basilica, ISKCON Rajajinagar,
Bangalore City railway station, KR Market, M. Chinnaswamy Stadium, the IISc main
building, the Kempegowda towers, UB City, and Kempegowda International Airport (well
north of the BBMP box). Each needs a Commons reference photo under a usable license.

## Phases

**Phase 0 — Feasibility (a session or two).** Set up the repo from the Manipur
pipeline, with `out/` and `data/raw/` on the external drive. Fetch the Vidhana Soudha
patch, render one 2048 px frame in the Manipur projection and palette, and write the
real counts (OSM vs Open Buildings, heights, render time) into this Status section.
Exit: Brajeshwar looks at the PNG and answers whether it reads as Bengaluru.

**Phase 1 — Central Bengaluru (2–4 weekends).** Inside the Outer Ring Road. Lakes,
parks, trees, metro, buildings, the four views, tiles, and a viewer online with search
and links. Exit: a link Brajeshwar can send to someone who lives there, who recognizes
their area.

**Phase 2 — Landmarks and polish.** Sprites for the first landmarks Brajeshwar picks,
labels, credits, link preview, zoom film. Exit: Brajeshwar is happy to post it.

**Phase 3 — BBMP.** Widen to the full box. Exit: the full build fits on disk and
finishes overnight, and the seams are invisible.

**Phase 4 — Parked.** AI restyle. Only with a GPU and appetite.

## Tripwires

Stop, or re-scope, if any of these happens:

- The Phase 0 render does not read as Bengaluru to someone who lives there.
- A single view will not render on this Mac without running out of memory, even frame
  by frame.
- Phase 1 exceeds four weekends.
- A data source's license turns out to be unclear. No gray zones.

## Open decisions for Brajeshwar

1. ~~Go or not, and when.~~ Go, 2026-11-16.
2. ~~Name.~~ "Bengaluru - 3D Isometric Map" is the site's name and title, 2026-11-16.
3. Domain, for example `bengaluru.oinam.com`, and whether a push to `main` deploys, as
   in Manipur.
4. ~~GitHub remote.~~ `git@github.com:oinam/bengaluru.git`, 2026-11-16. Nothing is
   pushed yet.
5. ~~Reuse.~~ Copied the Manipur pipeline in, 2026-11-16.
6. The look: projection, palette, and tile vocabulary, either Manipur's as is or new
   options rendered for Bengaluru.
7. Which landmarks get sprites first.
