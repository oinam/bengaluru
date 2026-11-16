# Plan

## Status

*16 November 2026. Phase 0, Session 1 done: the pipeline is in, and the first frames of
the test patch are in `out/vidhana-soudha/`. Phase 0's go/no-go is open: Brajeshwar looks
at `20261116-174652_detail-315.png` (north up) and `20261116-174652_detail-0.png` (turned
45°) and says whether it reads as Bengaluru. Session 2 then measures the city.*

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

1. **The metro station is a building on the road.** OSM maps the underground Vidhana
   Soudha station as a building, and the pipeline draws it above ground, across Ambedkar
   Veedhi. Underground structures need skipping. The metro line itself is not drawn
   anywhere: the pipeline reads no railways, and here the line is in a tunnel. East of
   the park, the viaduct along MG Road is mapped as one long building and pokes out of
   the patch as a thin line.
2. **The landmarks are plain blocks.** Vidhana Soudha has no dome and a blue roof; the
   High Court is cream, not red. Expected until Phase 2, but they are what a resident
   looks for first.
3. **Courtyards and stadium bowls are gray plates at roof height.** Kanteerava Stadium's
   field is a gray lid; Vidhana Soudha's courtyards are the same.
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
2. ~~Name.~~ Bengaluru, on the site and in its title, 2026-11-16. The title's exact
   wording is still open.
3. Domain, for example `bengaluru.oinam.com`, and whether a push to `main` deploys, as
   in Manipur.
4. ~~GitHub remote.~~ `git@github.com:oinam/bengaluru.git`, 2026-11-16. Nothing is
   pushed yet.
5. ~~Reuse.~~ Copied the Manipur pipeline in, 2026-11-16.
6. The look: projection, palette, and tile vocabulary, either Manipur's as is or new
   options rendered for Bengaluru.
7. Which landmarks get sprites first.
