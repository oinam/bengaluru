# CLAUDE.md

An isometric pixel-art map of Bengaluru, rendered procedurally from free, openly licensed
data. It is the second city after the Manipur map (`~/dev/manipur`, live at
https://manipur.oinam.com), and it starts from that project's pipeline and lessons.

**Status: Phase 0, with its go/no-go open.** The pipeline is in and the test patch
renders; Brajeshwar has yet to say whether the frame reads as Bengaluru. Read
`docs/PLAN.md` first; it is the brief, and its Status section says where things stand.
`docs/RESEARCH.md` is the prior art, `docs/DECISIONS.md` is what has been settled,
`docs/DATA.md` is the register of every source we use, and `docs/PICKUP.md` holds the
prompts for each session.

## The three rules

1. **No pixels from photographs.** Nothing in the output may derive from satellite or
   aerial imagery, Google/Esri/Bing tiles, Street View, or photogrammetry. Open rasters
   (WorldCover, DEM, canopy height) may *drive* the renderer (land cover class, elevation,
   tree density) but are never sampled for color or texture. Landmark sprites may be drawn
   from reference photos only when those photos are on Wikimedia Commons under CC BY,
   CC BY-SA, CC0, or public domain, and the sprite is a drawing, not a filtered photo.
2. **License-clean, or it does not go in.** Every source gets a row in `docs/DATA.md`
   with license, URL, download date, and what we use it for, before the first line of
   code touches it. If you are unsure of a license, stop and ask.
3. **Deterministic and regenerable.** Same inputs, same seed, same output. The map must
   rebuild from `data/raw/` with one command. No hand-edited pixels in the pipeline
   output; manual art lives in `assets/sprites/` as named source files.

## Who decides what

Brajeshwar owns the look: palette, projection, tile vocabulary, which landmarks get
sprites, what the site is called, and its domain. You propose by rendering options into
`out/` as PNGs and asking; you do not pick. Everything else (data plumbing, renderer
internals, tiling, viewer code) is yours to decide and record in `docs/DECISIONS.md`.

## How to work here

A spare-time project done in short sessions. Small tasks, each ending in something
visible: every session leaves a new PNG in `out/` that Brajeshwar can look at in ten
seconds. If a task cannot produce a picture, it is probably too big; split it.

Do not start Phase N+1 while Phase N has an open go/no-go. Phases and exit criteria are
in `docs/PLAN.md`.

Prefer boring tools, the same ones as the Manipur map: Python with `uv`,
GeoPandas/Shapely/Rasterio/pyproj for data, NumPy + Pillow for the renderer, libvips for
the tile pyramid, vanilla TypeScript + OpenSeadragon for the viewer, Cloudflare Workers
and R2 for hosting, and mise to pin the tools. No framework unless a decision says so.

Bengaluru is about eight times the Manipur map's Imphal area. Keep renders, tiles, and
downloads off the internal disk.

**Heavy work runs at night.** Builds, renders of the central or BBMP areas, tiling,
uploads, and large downloads start at 23:00 IST and stop at 04:00, while Brajeshwar
sleeps. Do not start one outside that window; give it to the night's work instead:
`mise run night [area]` does nothing outside the window and stops when it closes, and a
launchd agent starts it at 23:00. A test patch frame or build takes seconds and runs
whenever asked. The reasoning is in `docs/DECISIONS.md`.

## Commands

mise pins uv and runs each command below as a task: `mise tasks` lists them, and
`mise run <task> [area]` runs one, for example `mise run detail vidhana-soudha`. The
areas are `vidhana-soudha` (the test patch), `central`, and `bbmp`.

On this Mac, `out/` is a link to `/Volumes/2021OCT-5TB/Scratch/bengaluru/out` and
`data/raw/` is a link to `/Volumes/2021OCT-5TB/Scratch/bengaluru/raw`, so renders, tiles,
and downloads stay off the internal disk and the checkout holds only code and derived
data. The drive must be plugged in for anything that fetches, prepares, or renders. Do
not replace the links with folders; the reasoning is in `docs/DECISIONS.md`.

```
mise install && mise run setup                  # installs the pinned tools, then the Python environment
uv sync                                         # installs the pinned Python 3.12 environment
uv run bengaluru fetch   --area vidhana-soudha  # downloads into data/raw/<area>/; shared files into data/raw/_*/
uv run bengaluru plan    --area vidhana-soudha  # writes a top-down check to out/<area>/
uv run bengaluru prepare --area vidhana-soudha  # writes data/derived/<area>.gpkg and stats
uv run bengaluru render  --area vidhana-soudha  # writes flat frame and full renders to out/<area>/
uv run bengaluru swatches --area vidhana-soudha # writes the candidate palette sheet to out/<area>/
uv run bengaluru detail  --area vidhana-soudha  # writes one near-final 2048 px frame per detail view to out/<area>/
uv run bengaluru frames  --area vidhana-soudha  # renders the four views as seamless 2048 px frames
uv run bengaluru build   --area vidhana-soudha  # renders and tiles the four views one at a time; resumes at the first missing frame
uv run bengaluru tile    --area vidhana-soudha  # builds each view's Deep Zoom pyramid and the search index from frames on disk
uv run python tools/four_views.py [area]        # lays the four built views side by side in one PNG in out/<area>/
mise run night [area]                           # the night's work: fetch, prepare, and build inside 23:00 to 04:00; nothing outside it
uv run bengaluru night --area vidhana-soudha --window 14:00-14:05   # the same with another window, for testing
mise run schedule-on                            # installs the launchd agent that starts `mise run night` at 23:00; logs to logs/night.log
mise run schedule-off                           # removes the agent
uv run pytest                                   # runs the tests
uv run ruff check . && uv run ruff format --check .   # lints and checks Python formatting
```

`frames` and `tile` came over from the Manipur pipeline and have not been run on their
own here yet. Add each new command as it lands and keep this list current.

The render pool starts its workers afresh, and each one imports the script that started
it. A one-off script that renders frames must be a file with an `if __name__ ==
"__main__":` guard, never code piped to `python -`, which respawns workers without end.

## Git

Work directly on `main`; no phase branches, no merging. Commit often, small, with
messages that say what changed in the picture. Never force-push. Do not push unless
asked. Remote: `git@github.com:oinam/bengaluru.git`. Whether a push deploys is an open
decision in `docs/PLAN.md`.

## /odo

The usual Oinam convention, once Brajeshwar creates the files:

- Queue: `~/_/Oinam/1-Projects/devCommands/bengaluru.md`
- Log:   `~/_/Oinam/1-Projects/devLogs/bengaluru.md`

## Things that are explicitly parked

AI restyling of the render with an image model (the Pixel Chennai and Isometric Mumbai
route). It needs a GPU Brajeshwar does not have yet, and its cost grows with area. Do not
build toward it or let it shape the architecture; the procedural map must stand on its
own.
