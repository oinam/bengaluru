# CLAUDE.md

An isometric pixel-art map of Bengaluru, rendered procedurally from free, openly licensed
data. It is the second city after the Manipur map (`~/dev/manipur`, live at
https://manipur.oinam.com), and it starts from that project's pipeline and lessons.

**Status: planned, not started.** Do not build anything until Brajeshwar says go. Read
`docs/PLAN.md` first; it is the brief. `docs/RESEARCH.md` is the prior art,
`docs/DECISIONS.md` is what has been settled, `docs/DATA.md` is the register of every
source we use, and `docs/PICKUP.md` holds the prompts for each session.

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
downloads off the internal disk from the first session (see Phase 0 in `docs/PLAN.md`).

## Commands

None yet. Add each command here as it lands, as the Manipur project's `CLAUDE.md` does.

## Git

Not a repository yet. When Brajeshwar says go, the first session runs `git init` here,
works directly on `main`, and commits small, with messages that say what changed in the
picture. Never force-push. Do not push unless asked. The remote and whether a push
deploys are open decisions in `docs/PLAN.md`.

## /odo

The usual Oinam convention, once Brajeshwar creates the files:

- Queue: `~/_/Oinam/1-Projects/devCommands/bangalore.md`
- Log:   `~/_/Oinam/1-Projects/devLogs/bangalore.md`

## Things that are explicitly parked

AI restyling of the render with an image model (the Pixel Chennai and Isometric Mumbai
route). It needs a GPU Brajeshwar does not have yet, and its cost grows with area. Do not
build toward it or let it shape the architecture; the procedural map must stand on its
own.
