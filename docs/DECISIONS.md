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

Copied: the Python package (`src/manipur` became `src/bengaluru`, and the command is
`bengaluru`), the tests, `pyproject.toml`, `uv.lock` (so the package versions match),
`.python-version`, `mise.toml`, `.gitignore`, and the MIT `LICENSE`. The package and
command were `bangalore` for their first hour; see "The name is Bengaluru" below.

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
`/Volumes/2021OCT-5TB/Scratch/bengaluru/out` and `data/raw/` is a link to
`/Volumes/2021OCT-5TB/Scratch/bengaluru/raw`. `.gitignore` names them `/out` and
`/data/raw`, without a trailing slash, because git sees a link as a file. The drive must
be plugged in for anything that fetches, prepares, or renders.

`data/derived/` stays in the checkout for now: the test patch's is a few MB. Session 2
measures what the central and BBMP areas need and moves it to the drive if it is large;
the Mac had 41 GB free on 2026-11-16.

Nothing on the drive is precious. `out/` rebuilds from `data/raw/`, and `data/raw/`
downloads again with `bengaluru fetch`.

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

`origin` is `git@github.com:oinam/bengaluru.git`, at Brajeshwar's word; it was
`oinam/bangalore` until the project took its name the same evening. Nothing is pushed
until he asks, and whether a push deploys is still open.

## 2026-11-16 — Heavy work runs at night

Brajeshwar: builds and renders run while he sleeps, starting at 23:00 IST and stopping at
04:00. This covers anything that holds the Mac for more than a few minutes: `build`,
`frames` on the central or BBMP areas, tiling, uploads, and the large downloads. A test
patch frame takes seconds and runs whenever asked.

Built the same evening, at Brajeshwar's go-ahead:

- **`bengaluru night --area <area>`** (`mise run night [area]`) is the night's work. It
  fetches, prepares, and builds, each only if it is not already done, and only inside the
  window. Started outside it, as when the Mac wakes late, it does nothing. The closing
  time is fixed before anything reads the drive, a lesson from Manipur's first night.
- **The build stops at 04:00.** No frame, pyramid, or step starts after the window
  closes; frames being drawn finish, which takes seconds. A pyramid that has started is
  finished, since a half-written one is no use, so tiling a large view can run past
  04:00. Session 2 measures by how much.
- **The build resumes at the first missing frame**, not the first missing view, since
  one view of a large area may not fit in five hours. A frame is written beside its
  name and renamed, so a frame on disk is a whole frame. Each view's frame folder
  records a hash of what its frames were drawn from (the derived data, the canvas, the
  package's code, and the landmark files); if that changes between nights, the view
  starts over rather than mixing two renders.
- **A launchd agent** (`launchd/com.oinam.bengaluru.night.plist`) starts `mise run night`
  at 23:00 and logs to `logs/night.log`. `mise run schedule-on` installs it and
  `mise run schedule-off` removes it. It is installed. Its area is the default in
  `mise.toml`, which is the test patch until Phase 1 changes it to `central`; the test
  patch is already built, so until then a night's run only confirms the schedule works.
- **The Mac must be awake and the drive plugged in.** Without the drive the run stops
  with a message. `caffeinate -is` holds the Mac awake from the agent's first second to
  its last, as Brajeshwar suggested: this Mac sleeps after one idle minute, and `-s`
  keeps it up on AC power where `-i` alone might not. caffeinate cannot wake a Mac that
  is already asleep; see the next entry.

Tested on the test patch, with windows a few seconds long: stopped between views, then
between a view's frames and its pyramid, then with half a view's frames on disk, and
finished on the fourth run. Every tile and index file matched an uninterrupted build
byte for byte; only libvips's own timestamp in each `vips-properties.xml` differed.

## 2026-11-16 — The name is Bengaluru

Brajeshwar: read it as Bengaluru, and rename the folder, the project references, and
the title. So everything the project is called by is `bengaluru`: the folder
(`~/dev/bengaluru`), the Python package and its command, the folder on the external
drive (`Scratch/bengaluru`), and the `/odo` queue and log.

The site's name and title are "Bengaluru - 3D Isometric Map", in Brajeshwar's words the
same evening.

The GitHub repository is `oinam/bengaluru` too. Place names keep their own spelling:
Bangalore Palace and Bangalore City railway station.

## 2026-11-16 — The night's work wakes the Mac itself, once allowed

Waking a sleeping Mac takes `pmset schedule wake`, which needs root, so it needs
Brajeshwar's permission once. `launchd/bengaluru-wake.sudoers` is that permission: one
sudoers line that lets his account run `pmset schedule wake <when>` without a password,
and nothing else. He installs it; nothing in the project can.

```
sudo install -m 440 -o root -g wheel launchd/bengaluru-wake.sudoers /etc/sudoers.d/bengaluru-wake
sudo visudo -c
mise run night
```

The last line sets the first wake. After that the chain keeps itself going: every run of
`bengaluru night` sets a wake for the next 23:00, and launchd runs the agent whenever the
Mac wakes after a missed night (it wakes at 05:58 every day anyway), so a skipped night
costs one night. The wake is at 23:00 exactly, not earlier: this Mac sleeps again after
one idle minute, and launchd starts a job it slept through the moment it wakes.

Without the permission nothing asks for it: the run says no wake is set and carries on,
and the Mac has to be awake at 23:00 by other means. `pmset repeat` is not used, because
it holds a single wake time and this Mac's is the 05:58 one.

Not known yet: whether the wake and the work hold with the lid closed. Scheduled wakes
are only dependable on AC power. Until a night proves otherwise, leave the Mac plugged
in with the lid open.

To take the permission away: `sudo rm /etc/sudoers.d/bengaluru-wake`. `mise run
schedule-off` removes the agent but leaves any wake already set, at most one.
