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
Brajeshwar's permission once: one sudoers line that lets his account schedule or cancel a
wake without a password, and nothing else. He installs it; nothing in the project can.

The permission is Mac-wide, `/etc/sudoers.d/claude-wake`, not this project's. Brajeshwar
asked for one that any project's scheduled work can use instead of one to remember per
project, and a sudoers rule belongs to the account anyway. `docs/WAKE.md` has the line,
how to install and remove it, why it stays that narrow, and how a project uses it. The
project's own `launchd/bengaluru-wake.sudoers`, an hour old and never installed, is gone.

After installing it, `mise run night` sets the first wake. Then the chain keeps itself
going: every run of
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

To take the permission away: `sudo rm /etc/sudoers.d/claude-wake`. `mise run
schedule-off` removes the agent but leaves any wake already set, at most one.

## 2026-11-17 — Build all of it, starting today

Brajeshwar, in the morning: the point is the map of the whole city, so go ahead and build
it, and set the nightly work to keep building and rendering it. That is the go on
Phase 0's question, and it starts Phase 1 and Phase 3 together: the central area first,
then the BBMP box.

For this one day he lifted the night-only rule for six hours, 07:40 to 13:40, while he
was at the office. The rule stands for every other day.

So the order of the plan changed. Session 2, measuring the city on a sample and showing
three tree treatments, did not happen first; the central build is the measurement, and
its numbers are in `docs/PLAN.md`. The look is still Manipur's, unchanged, and still
Brajeshwar's to change: anything he changes is drawn again by the next night's work.

## 2026-11-17 — The night builds central, then the whole city, and again when anything changes

`mise run night`, and so the 23:00 agent, now works through `central` and then `bbmp`
(`NIGHT_AREAS` in `src/bengaluru/night.py`); `mise run night <area>` still does one. Each
area is fetched and prepared if it has not been, then built view by view until the window
closes, and the next night carries on at the first missing frame.

Each built view records what it was drawn from: the derived data's size and time, and
the three files that decide pixels (`detail.py`, `render.py`, `palettes.py`) with the
landmarks and sprites. A view whose record differs from today's is built again. So a
change to the renderer or the data made during the day reaches the map overnight, with
no command to remember. The viewer keeps showing the old pyramids until all four views
of an area are new, then the old ones are deleted.

The frames' own fingerprint is the same record plus the canvas. It used to hash every
file in the package, which would have thrown away a night's frames for a change to the
command line.

## 2026-11-17 — Railways, the metro's viaducts, and what is underground

Three fixes to what Phase 0 listed as wrong, all in how the data is read, none in the
look:

- OSM maps the stations under the road as buildings. A building tagged
  `location=underground`, with a negative `layer`, or with `building:levels=0` is left
  out. In the test patch that is six, among them the station that sat on Ambedkar Veedhi.
- The pipeline read no railways. Track in the open (`railway` of `rail`, `subway`,
  `light_rail`, or `narrow_gauge`, not in a tunnel) is now a `rails` layer. On the ground
  it is drawn as a bed of ballast with ties and a dark line.
- A viaduct (`bridge=viaduct`, or any bridge on the metro) is drawn as a deck 9 m up on
  piers 24 m apart, each span sorted among the buildings around it. A railway's ordinary
  bridge over a road or a drain stays at track level. A detected footprint that sits
  mostly on a viaduct is dropped as the viaduct itself.

The deck's height, width, and colors are first guesses from the palette's existing wall
and road colors; they are Brajeshwar's to change. Flyovers for roads are still drawn flat.

## 2026-11-17 — The viewer

`web/` is the Manipur map's viewer, copied as it stood on 2026-11-17, without what is
Imphal's: the aircraft and their timetable, the Sangai, the weather, the Worker, and the
deploy script. It keeps OpenSeadragon, search, labels, the four views with north up
first, the water, the Go to panel, the help, and the credits. `mise run dev [area]`
serves it at http://localhost:8655 on `out/<area>/tiles`.

What is different from Manipur's:

- **Links carry latitude and longitude**, `#zoom/lat/lon` and `/view` when turned, not
  canvas pixels. Manipur's links broke when its canvas grew and needed a table of old
  frames; this map's canvas will grow from central to BBMP, and a rebuild may move it.
- **Only the names in view get an element.** The city has tens of thousands of named
  places; Imphal's few thousand each had one. The smallest names wait for a closer zoom
  than in Manipur.
- **The Go to list is spots, not names from the search index.** A first list, taken from
  OSM's own positions; Brajeshwar picks the real one.

Not decided here, and carried over from Manipur only as placeholders: the rendered map's
license in the credits (CC BY-SA 4.0), the footer's wording, and the palette of the page.
Nothing is deployed, and there is no domain yet.

## 2026-11-17 — What the city's size changed in the pipeline

Central is 75 times the test patch and BBMP four times central. Three things that were
fine on the patch were not on the city, and each is changed in how the work is done, not
in what comes out:

- **`prepare` tests a footprint against the pieces of water, road, and viaduct, not
  their union.** Joining every major road into one polygon and intersecting each
  footprint with it ran for 16 minutes on central without finishing. Each footprint is
  now clipped by only the pieces it touches, and the clippings are joined per footprint,
  so overlapping pieces still count once. Central takes 3 min 48 s; the test patch
  drops the same footprints as before.
- **A render worker reads each frame's buildings from the derived file.** Six workers
  each holding the city's buildings came to 11 GB on central. The GeoPackage's spatial
  index gives a frame its buildings in well under a second, and the frames are the same
  pixel for pixel as with everything in memory.
- **A worker with its trees already placed does not parse the area's OSM again.** The
  tree rows were the last reason it did.

With these a worker stays at 1.0 to 1.6 GB whatever the area, and BBMP builds on this
Mac with half its memory free.

## 2026-11-17 — The viewer opens on the whole city

BBMP was built by 11:42 on 2026-11-17, so `mise run dev` and `mise run build` now take
`bbmp` when no area is named; `mise run dev central` still serves the central build.
The night keeps both areas: central is the quick one, 22 minutes, and shows a change
to the drawing code before the two and a half hours of BBMP are spent on it. Whether
central is worth keeping once the look settles is open.

`tools/four_views.py` draws each view at most 4,608 px wide. At a fixed quarter scale
central's sheet was 18,504 px wide and 317 MB, and BBMP's would have been twice that.

## 2026-11-17 — A hole in a footprint is a courtyard, not a lid

Manipur's renderer drew a footprint's holes as dark plates at roof height, which was
enough for Imphal's few. Here the holes are the stadium bowls and the courtyards of the
buildings a resident looks for first: 44 buildings in the test patch, 389 in central.
The roof is now opened over each hole. What was drawn there before the building, ground
and anything farther back, shows through as the floor, and the hole's far walls are
drawn down to it with the building's own wall colors and windows. Nothing new is added
to the palette or the building types.

This changes `detail.py`, so every built view is stale and is drawn again: central the
same day, BBMP from the same day into the night.

## 2026-11-17 — bengaluru.oinam.com, deployed on push

Brajeshwar chose `bengaluru.oinam.com` and asked for the site to deploy when `main` is
pushed. It is the Manipur map's arrangement, less its Worker code:

- **The viewer is a Worker of static assets only**, `bengaluru` in the Oinam account,
  with the domain attached by Wrangler (`web/wrangler.jsonc`). There is no server code,
  since this map has no aircraft feed.
- **GitHub Actions deploys it** (`.github/workflows/ci.yml`): lint and tests, then
  `pnpm run deploy`, on every push to `main`, with a Cloudflare API token as a
  repository secret. So a push is a publication, and `CLAUDE.md` says so.
- **The tiles and their indexes are on R2**, bucket `bengaluru-tiles`, served from
  `bengaluru-tiles.oinam.com`, one level under `oinam.com` for the same certificate
  reason as Manipur's. GitHub cannot render the map; `tools/upload_tiles.py` sends the
  pyramids from this Mac with rclone, and the index files last, which is what switches
  the live map over.
- **Only BBMP goes online.** Central is inside it and stays a local build.
- **`--prune` is new.** R2's free 10 GB is shared with Manipur's 3.8 GB, and each
  rebuild of BBMP is another 4 GB of pyramids under new names. After the index files
  are up, `--prune` removes the pyramids the manifest no longer names. It is not the
  default: it deletes from R2, so it runs when asked.
- **The bucket's CORS rules are a file**, `web/r2-cors.json`, so the bucket can be made
  again from the repository. The viewer reads tile pixels for the water and fetches the
  indexes, both across origins.

The upload is not part of the night's work. Sending the index files publishes, and
that waits for Brajeshwar's word, as a push does.

## 2026-11-17 — Going live with the first build, and what a domain move touches

Brajeshwar asked to push and see `bengaluru.oinam.com` working the same afternoon, with
BBMP's courtyards half redrawn. The upload now publishes what the manifest on disk
names, which is always one whole build, and sends ahead the pyramids of views finished
since; before, it refused to publish until every view was current. So the first build,
with the lids, went live on 2026-11-17, and the courtyards follow when the night has
finished them and the upload is run again, with `--prune` to take the first build off
R2.

He may move these maps to a domain of their own. The domain is named in five places,
and nowhere else: the route in `web/wrangler.jsonc`, the tile base in the `deploy` script
of `web/package.json`, the bucket in `tools/upload_tiles.py`, the origin in
`web/r2-cors.json`, and the prose of `CLAUDE.md` and these docs. Links into the map are
`#zoom/lat/lon`, so they survive a move.

He also asked whether the maps' tiles can share one place, `cdn-tiles.oinam.com/manipur`
and `/bengaluru`. They can: R2 keeps a separate cached copy of a tile for each asking
origin, so one bucket can allow several sites (checked on `bengaluru-tiles`). An empty
bucket `cdn-tiles` with that domain exists, made on 2026-11-17, and nothing uses it
yet. Moving in needs a token for that bucket, a prefix in each map's upload and tile
base, and a session in the Manipur repository, and it is better done once the domain
question above is settled, since the tiles' domain would move with it. The cost of
sharing is that one token then writes every map's tiles.

## 2026-11-18 — The airport, and bounds that move

Brajeshwar asked for Kempegowda International Airport on the map. It lies north of the
BBMP box: OpenStreetMap bounds the airport at 13.1838–13.2113 N, 77.6759–77.7366 E. A
map here is one rectangle, so the `bbmp` area's north edge moved from 13.14 to 13.23 N
across its whole width, which leaves about 2 km of ground beyond the airport's fence and
stops short of Devanahalli town. The area keeps its name, since its folders, its
pyramids' file names, and the viewer all carry it. Yelahanka Air Force Station, which
the old edge cut through, is now whole. The airfield is drawn as HAL's already is, from
OSM's runways, taxiways, and aprons, and the terminals are plain buildings from their
footprints. Live aircraft were looked at and set aside by him for now; adsb.lol heard
ten aircraft within 75 km of the airport on one query that morning, five of them on the
ground there, against none at Imphal.

Moving an edge showed that the night never fetched or prepared an area twice: it looked
only for `SOURCES.txt` and the stats file. Now `fetch` writes the bounds it fetched to
`data/raw/<area>/bounds.json`, last, and the night fetches again when they differ from
the area's, and prepares again when the stats are older than the fetch. The build
already drew every view again when the prepared data changed. The three areas on disk
got their `bounds.json` by hand that morning, with the bounds they were fetched for.
The taller area needs a second Open Buildings cell, `3bb1`, 274 MB.

## 2026-11-18 — The repository is public: what was checked

Brajeshwar made `oinam/bengaluru` public, so the site's links to it work, and asked that
the code be formatted and linted and its security looked after.

- **Format and lint.** Nothing needed changing: `ruff check`, `ruff format --check`, the
  tests, and the viewer's `tsc`, ESLint, and Prettier all passed, and CI runs them on
  every push. Ruff's security rules, run once by hand, flag only test asserts and the
  argument-list calls to `rclone`, `pmset`, and `sudo`.
- **Secrets.** `.env` was never committed, the history holds no key or token, and
  GitHub's secret scanning, turned on that day with push protection, found none. The
  Cloudflare account ID in `web/wrangler.jsonc` and `tools/upload_tiles.py` is an
  identifier, not a secret.
- **The workflow.** Its jobs now get read-only access to the repository, where GitHub's
  default here was write, and each action is pinned to a commit instead of a tag that
  can be moved, since `deploy` holds the Cloudflare token. A pull request from a fork
  runs lint and tests without secrets, and a first-time contributor's run waits for
  approval. Updating an action is now a deliberate edit of its commit.
- **Dependencies.** `pip-audit` found nothing in the Python lock. `pnpm audit` found ten
  advisories against Vite 7.1.12, all in its dev server, which is the one on this Mac;
  Vite is now 7.3.7. Two remain with no fix to take, in `minimatch` and `picomatch`
  under `typescript-eslint`: both are slow-pattern bugs in a linter that reads only our
  own files.
- **The site.** It sends `X-Content-Type-Options: nosniff` and a referrer policy. It
  has no accounts, cookies, or forms, and the viewer writes names from the search index
  as text, never as HTML. A content security policy was left out: it would name the
  tiles' domain in one more place, and a wrong one blanks the map on a push with no
  way to try it first.

Not done, and his to ask for: a rule on GitHub that blocks force-pushes to `main`, and
a `SECURITY.md` saying where to report a problem.

## 2026-11-18 — English only, for now

Brajeshwar's call, after the notes on Isometric Bengaluru in `docs/RESEARCH.md` proposed
Kannada names in search and labels: no Kannada, the map stays in English for now. The
data would allow it later (`name:kn` is on most named places, stations, and roads in
OpenStreetMap), so this is a choice about the map, not a limit of its sources.

## 2026-11-18 — The look: terraces and lawns

Brajeshwar saw little between the four looks in
`out/central/20261117-091959_look-options.png` and said to pick one. Picked: C.

- **Roofs.** Of the small rectangular buildings, nine in a hundred keep a pitched roof
  (`PITCHED_PERCENT`); the rest are flat. Of the flat roofs, 85 in a hundred are bare
  concrete (`CONCRETE_PERCENT`) and the rest keep a color. Before, 72 in a hundred were
  pitched tin in red, orange, and blue, which is Imphal.
- **Cropland is grass.** WorldCover's cropland inside the city is the Race Course, the
  golf course, and Palace Grounds, so it is drawn as grass and the paddy fields with
  their bunds are gone from the renderer. The same rule draws the farmland around the
  airport as grass, which is plainer than it is; fields there want a pattern of their
  own, not Manipur's paddy.
- **Not taken: the gray ground (D).** Gray between the buildings sits too close to the
  concrete roofs and the walls, and the city loses its blocks. The sandy ground stays.

Before and after are in `out/central/20261118-131533_look-c-before-after.png`. The
change makes every built view stale, so the night of the 18th draws both areas again.

The night now builds `bbmp` first and `central` after it. The site shows `bbmp`, and a
night that runs short should run short on the area nobody is looking at.

## 2026-11-18 — An AI-painted layer will be tried; satellite imagery will not

Brajeshwar's call, after the cost comparisons in `docs/RESEARCH.md`: no email to NSIL
about Cartosat imagery, and a trial of an AI-painted layer instead. This lifts the
parking of that route in `CLAUDE.md`. It is a trial on the test patch, by Pixel
Chennai's method, with our own render as the only thing the model is shown; the steps,
costs, and what is his to do are in `docs/PLAN.md`. The code-drawn map stays the base
and the painted tiles sit beside it, so nothing here changes the pipeline yet.

The same day he set two ideas aside: flowering-tree palettes, and Kannada names.

## 2026-11-18 — No force-pushes to main, and where to report a problem

At Brajeshwar's word, GitHub now holds a ruleset on `oinam/bengaluru`, "main: no
force-pushes": it blocks force-pushes to, and deletion of, the default branch, for
everyone, with no bypass. An ordinary push is untouched. Deletion is in it because
deleting `main` and pushing it again is a force-push by another road.

`SECURITY.md` asks for reports in private through brajeshwar.com. GitHub's private
vulnerability reporting, which would add a "Report a vulnerability" button to the
repository, is a setting of its own and was not turned on.

## 2026-11-18 — The metro is a layer in the viewer

Brajeshwar liked the metro drawn in its lines' colors with station names, the first
lesson from Isometric Bengaluru in `docs/RESEARCH.md`. It is a layer the viewer draws
over the map, not something rendered into the tiles, so it can be switched off and
costs no render.

- **Where the lines come from.** OpenStreetMap's route relations name the track of each
  line and carry its name and color. `fetch` now keeps those relations, as tags and
  member ids alone, from Overpass and from the Geofabrik extract. `prepare` writes two
  layers, `metro` and `stations`, and `tile` writes them as `metro.json` beside
  `flow.json`, in the default view's pixels like it.
- **Open or being built** is the route's word, not the track's: a route in service makes
  its track open whatever the way is tagged, because the relations are kept current and
  the ways are not. Track being built is dashed. Lines only proposed (Orange, Red) have
  no route of the kind kept, and are left out.
- **Gaps are OpenStreetMap's.** Track no route names is not drawn: depots, crossovers,
  and a few stretches a mapper has yet to add to a relation, about 2 km of the Blue
  Line among them. The fix for those is upstream.
- **Colors are OpenStreetMap's too**: `#e542de`, `#009933`, `yellow`, `#FF49A7`, `blue`.
  The viewer uses them as given.
- **Height.** Open track on a viaduct is lifted onto the deck the map draws, by
  `raised_px`, the same in every view. Track in a tunnel is drawn faint, on the ground
  above it. Track being built is drawn on the ground, since the map draws no viaduct
  under it yet.
- **In the viewer** the layer is on unless switched off in Settings, where "Metro
  lines" appears only when the map has a `metro.json` with lines in it. Station names
  show from an image zoom of 0.15. A station's name can appear twice close in, once
  from this layer and once from the search labels; left so.
- **Not done:** opening dates and the timeline. Fifteen of 329 metro ways carry a date,
  so it needs a source of its own and a row in `docs/DATA.md`.

Seen on the city build with an index made by hand from the same code:
`out/bbmp/20261118-132647_metro-layer-city.jpg` and `…_metro-layer-mg-road.jpg`. The
real index is written when the night prepares and builds `bbmp` again.

## 2026-11-18 — The palette, checked for color-blind readers

Brajeshwar asked for the check. `tools/colorblind.py` draws one frame as protanopia,
deuteranopia, and tritanopia see it (Machado and others, 2009, at full severity) and
lists the colors that mean something on the map and sit less than 12 apart in L*a*b*
for some viewer. The sheet is `out/vidhana-soudha/20261118-133357_colorblind.png`.

The map holds up, and nothing was changed. Trees, grass, ground, roads, walls, and
water differ in lightness as well as hue, so they stay apart when red and green do
not: the trees turn olive and the ground stays sand. What merges:

- **Wetland** with bare ground, footpaths, and built ground for red-blind readers (6 to
  12), and with grass for blue-blind ones (6). Wetland is rare in the city.
- **Footpaths and bare ground** for everyone (2). They are nearly one color in the
  palette, which came from Manipur; a path across open ground does not show.
- **Roofs** lose their reds, which are decoration and carry no meaning.

The metro's five line colors stay apart for every viewer; the closest pair is Purple
and Pink, 36 for typical vision and 19 for blue-blind. Against the map, the Green Line
nears grass for red- and green-blind readers (9 to 10) and the Pink Line nears water
for red-blind ones (5), which is what the dark casing around every line is for.

A fix for the first two is a palette change, so it is Brajeshwar's to ask for.
He read this the same day and asked for none, so the palette stays.

## 2026-11-18 — The drawing code, tidied without moving a pixel

`detail.py`, `render.py`, and `palettes.py` were read line by line, the last of the
code to get it. Ten crops of the central area and the test patch, in all four views,
come out the same pixel for pixel before and after.

What went: wall colors and a decorator that `_paint_walls` took and nothing passed; a
second copy of the palette packer; two functions that read an optional layer, now one;
and a noise term in the ground painter that was added to every class alike, so it chose
nothing. What got a name: the roof slots for tin and concrete, the four kinds of thing
the scene sorts and paints, the view's turn, and the pieces of a multi-part geometry.

## 2026-11-18 — The license line, the Go to list, and the viaduct stay, for now

Three things went public as placeholders and were Brajeshwar's to settle: the "Rendered
map CC BY-SA 4.0" line in Credits, the 16 places in the Go to list, and the metro
viaduct drawn as a cream deck on piers. His word on all three: keep them, for now. They
are no longer open questions, and each is still his to change.

## 2026-11-18 — The AI-painted layer is parked again

Hours after choosing to try it, Brajeshwar put the painted layer off: later, and no
money now. The choice between the two routes stands, a painted layer and not satellite
imagery, but nothing is started, no key or account is asked for, and the site's "zero
cost" line stays true. The trial's steps and costs stay in `docs/PLAN.md` for when he
takes it up.

## 2026-11-18 — Flowering trees, in groves

Set aside in the morning as "no options"; in the afternoon Brajeshwar said to do it if
it needed no confirming from him. So these are picks, and his to change.

- **Three trees.** Pink tabebuia, purple jacaranda, and red gulmohar, the three the
  city is known for. Their colors are in `palettes.py` as `BLOSSOM`, picked by eye to
  stand clear of the greens and of the tin roofs' reds. Each has a lighter shade for
  where the sun falls, made the way the other shades are.
- **In groves.** Avenues and parks plant one kind together, and salt and pepper across
  the whole city read as noise. The ground is cut into 100 m squares (`GROVE_M`); 13 in
  a hundred are in bloom with one kind (`GROVES_IN_BLOOM`), and in those half the trees
  flower (`TREES_IN_BLOOM`). Each tree looks its square up from a spot up to 25 m off
  its own, so a grove has a ragged edge and not a square one. On the test patch that is
  1,963 of 30,871 trees, about one in sixteen.
- **Which trees.** Decided by a hash of the tree's position and the seed, at painting
  time, so the placed trees on disk are untouched and every view and every build
  agrees. Nothing in the data says where a flowering tree stands; the About page and
  the credits now list blossoms among what is illustrative.
- **All at once.** Tabebuia flowers from January, jacaranda in March and April, and
  gulmohar from April to June. The map shows the three together, which no month does.
- **More than 32 colors.** The drawing held to 32 palette slots, a limit that came with
  Manipur's code. Three blossoms and their light shades make 38. The table of slots is
  now `DETAIL_SLOT`, and the test that held the count at 32 now holds it under the
  slot kept for transparency.
- **Checked.** In ten crops of the central area and the test patch, every pixel that
  changed went from a lit green of a canopy to a blossom, and nothing else moved. A
  flowering tree keeps its shape, its shadow, and its green in the shade.

The picture is `out/vidhana-soudha/20261118-151452_crop-cubbon-park-in-bloom-315.png`,
with the four views of the test patch in `20261118-151447_four-views.png` beside it.
