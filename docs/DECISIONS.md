# Decisions

One entry per settled question. Newest at the bottom. Proposals not yet decided live in
`PLAN.md` under "Open decisions".

## 2026-11-16 — Planned now, built later

Brajeshwar asked for a plan for a Bengaluru map in the same family as the Manipur map,
written for Claude Code to pick up, and said it is not being built yet.

## 2026-11-16 — Procedural, with the AI restyle parked

Same reasoning as the Manipur map. The AI repaint that Pixel Chennai and Isometric Mumbai
use needs a GPU and costs more with area; Brajeshwar parked it until he has a separate
machine or a cloud GPU budget. The procedural render must stand on its own.

## 2026-11-16 — Its own project

Bengaluru gets its own folder and, once started, its own repository, rather than a new
area inside the Manipur repo, which is about Manipur.

## 2026-11-16 — Go, and started from the Manipur pipeline

Brajeshwar said go the same day, through the `/odo` queue. The pipeline is a copy of the
Manipur map's, taken from `~/dev/manipur` at commit
`eb359531bef354647cc7139fcc5699b544ee34af` (its `main` on 2026-11-16), not a shared
package: two cities are too few to know what is common.

Copied: the Python package (`src/manipur` became `src/bangalore`, and the command is
`bangalore`), the tests, `pyproject.toml`, `uv.lock` (so the package versions match),
`.python-version`, `mise.toml`, `.gitignore`, and the MIT `LICENSE`. The package and
command are named for the folder and the repository, `bangalore`; what the site calls the
city is still Brajeshwar's to decide.

Dropped as Imphal-only:

- The aircraft, the Sangai, and everything under `tools/` and `web/`. The viewer and the
  tools it needs (link preview, zoom film, upload) come back in Phase 1.
- Phumdis and athaphum rings on Loktak, in `prepare` and `detail`.
- The state overview (`overview.py`), which drew Manipur.
- Every landmark: the sprites, `assets/landmarks.json` (now an empty list), the cemetery
  credit, and the twelve footprint painters written for Imphal's buildings (Kangla's gate
  and citadel, Ima Keithel, the assembly, and the rest). The mechanism stays:
  `STYLE_PAINTERS` is empty until Brajeshwar picks Bengaluru's landmarks in Phase 2, and
  the Manipur painters are there to start from at the commit above.
- The share-link history (`assets/hash_origin.json`, `link_frames`, `hash_shift`), which
  kept old Imphal links working.

Kept though it was shaped by Imphal, because Phase 0 asks what Manipur's look does to
Bengaluru: the projection, the monsoon palette, the building vocabulary (tin-roofed
houses, shophouses, sheds, blocks), paddy fields on crop land, the cemetery painter, and
the view names (`315` is north up), which the Manipur viewer reads.

Changed: the metric CRS is UTM 43N (EPSG:32643), and the seed is 1537.

## 2026-11-16 — Renders and downloads live on the external drive

As in the Manipur project, and from the first session. `out/` is a link to
`/Volumes/2021OCT-5TB/Scratch/bangalore/out` and `data/raw/` is a link to
`/Volumes/2021OCT-5TB/Scratch/bangalore/raw`. `.gitignore` names them `/out` and
`/data/raw`, without a trailing slash, because git sees a link as a file. The drive must
be plugged in for anything that fetches, prepares, or renders.

`data/derived/` stays in the checkout for now: the test patch's is a few MB. Session 2
measures what the central and BBMP areas need and moves it to the drive if it is large;
the Mac had 41 GB free on 2026-11-16.

Nothing on the drive is precious. `out/` rebuilds from `data/raw/`, and `data/raw/`
downloads again with `bangalore fetch`.

## 2026-11-16 — Shared downloads are fetched once

One Open Buildings v3 cell, S2 level 6 `3baf`, covers the test patch, the central area,
and the BBMP box, and is 569 MB compressed. Manipur streamed its cell on every fetch;
here it is kept in `data/raw/_open_buildings/`, beside the Geofabrik extract in
`data/raw/_geofabrik/`, and each area reads its rows from the file.

## 2026-11-16 — The test patch is wider than the plan's

The plan's box (12.970–12.985 N, 77.585–77.600 E, about 1.6 km square) is 1,660 m north
to south. The site's default view is north up at half scale on that axis, so a 2048 px
frame covers 2,048 m of it and the box would leave empty bands. The `vidhana-soudha`
area is 12.965–12.990 N, 77.580–77.605 E, about 2.7 km square: Vidhana Soudha, the High
Court, all of Cubbon Park, Kanteerava and Chinnaswamy stadiums, and UB City.

## 2026-11-16 — Remote

`origin` is `git@github.com:oinam/bangalore.git`, at Brajeshwar's word. Nothing is pushed
until he asks, and whether a push deploys is still open.

## 2026-11-16 — Heavy work runs at night

Brajeshwar: builds and renders run while he sleeps, starting at 23:00 IST and stopping at
04:00. This covers anything that holds the Mac for more than a few minutes: `build`,
`frames` on the central or BBMP areas, tiling, uploads, and the large downloads. A test
patch frame takes seconds and runs whenever asked.

Not built yet. What it needs, for the session that builds the first large area:

- A launchd agent that starts the night's task at 23:00, as the Manipur upload does.
- A stop at 04:00: `build` finishes the frame it is on and exits.
- Resuming by frame, not by view. `build` resumes after the last finished view today,
  and one view of a large area may not fit in five hours.
- The Mac awake and the drive plugged in. `caffeinate` keeps it awake once started; a
  sleeping Mac needs `pmset repeat wakeorpoweron` shortly before 23:00.
