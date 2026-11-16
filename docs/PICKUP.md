# Picking this up in Claude Code

Only after Brajeshwar says go. Open this folder in Claude Code and paste the first
prompt. Each later session gets the next prompt. Every session ends with a PNG in `out/`.

## Session 1 (Phase 0): the repo and the first frame

> Read CLAUDE.md and docs/PLAN.md. We are starting Phase 0. Run `git init` and set up the
> project from the Manipur pipeline in ~/dev/manipur: copy its Python package, mise and
> uv setup, and tests, renamed for Bengaluru, and drop what is Imphal-only (aircraft,
> Sangai, phumdis, Loktak). Record the Manipur commit you started from in
> docs/DECISIONS.md. Put `out/` and `data/raw/` on the external drive the same way
> Manipur does, and record that too. Register OSM, Open Buildings v3 and 2.5D, and
> WorldCover in docs/DATA.md, reading each license again. Fetch the Vidhana Soudha test
> patch, prepare it, and render one 2048 px frame with Manipur's projection and palette
> to out/vidhana-soudha/. Then fill in the Status section of docs/PLAN.md with real
> counts: OSM vs Open Buildings footprints, how many have heights, render time, and what
> looks wrong.

## Session 2 (Phase 0 exit): measure the city

> Using the Phase 0 numbers, estimate the central and BBMP builds: buildings, canvas per
> view, frames, render time, memory peak, and disk for four views. Measure on a 2 × 2 km
> sample rather than guessing. Render the test patch with three tree treatments
> (WorldCover only, WorldCover plus OSM trees, and a canopy source if you found a
> clean-licensed one, registered first) side by side in one PNG. Do not pick; I will.

## Session 3 onward (Phase 1)

> Here is my Phase 0 decision and my notes: [...]. Set up the viewer from Manipur's web/,
> with the four views and north up by default, and build the central area one view at a
> time. Lakes, parks, the metro, and tall buildings first; show me each as a crop before
> the full build.
