# Plan

## Status

*Draft 1, 16 November 2026. Planned, not started. Brajeshwar asked for the plan so a
later session can pick it up cold; nothing is built until he says go.*

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

- Test patch, Vidhana Soudha and Cubbon Park: 12.970–12.985 N, 77.585–77.600 E
  (about 1.6 × 1.6 km)
- Central Bengaluru, inside the Outer Ring Road: about 12.90–13.05 N, 77.52–77.68 E
- BBMP area: about 12.83–13.14 N, 77.46–77.78 E
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

1. Go or not, and when. Nothing starts before this.
2. Name: "Bengaluru" or "Bangalore" on the site, and the site's title.
3. Domain, for example `bengaluru.oinam.com`, and whether a push to `main` deploys, as
   in Manipur.
4. GitHub remote, for example `oinam/bangalore-map`.
5. Reuse: copy the Manipur pipeline in (the default above), or extract a shared package
   first.
6. The look: projection, palette, and tile vocabulary, either Manipur's as is or new
   options rendered for Bengaluru.
7. Which landmarks get sprites first.
