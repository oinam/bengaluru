# Prior art

Read 2026-11-16. The Manipur project's `docs/RESEARCH.md` covers the wider field
(tiny.london, isometric.nyc, Pixel Singapore, Isopolis SF).

## Is there a Bengaluru map already?

No, as of 2026-11-16. The Isometric Cities directory's India page lists three maps:
Isometric Imphal (ours), Isometric Mumbai, and Pixel Chennai. A web search found no
isometric pixel-art map of Bengaluru. The nearest thing is a commissioned illustrated
map by Rod Hunt for the Bhartiya City development outside the city, which is neither
pixel art nor of the city.

## Pixel Chennai

https://pixelchennai.com/. Read from its own About text.

- Greater Chennai, about 60 km of coast. Base render 310,851 × 219,672 px; AI layer at
  twice that.
- Inputs: OpenStreetMap and Overture footprints, Google Open Buildings heights, and a
  satellite map of tree canopy, drawn by a program as a plain isometric map.
- That render is restyled by Qwen-Image-Edit-2511 on a MacBook, with a 4-step LoRA and a
  style LoRA trained from a few Nano Banana tiles.
- Two layers toggled with L, English and Tamil, road names along their course, a
  locator inset, smooth flights between places, smoothing only while zoomed out.
- Lesson for us: the base render they built is what we build. Their canopy input is
  worth copying if a clean-licensed source exists.

## Isometric Mumbai

https://isometricmumbai.com/ by Aryan Gupta. Tagged AI on Isometric Cities. Not studied
yet; read its own notes before Phase 0.

## Isometric Imphal (our first map)

https://manipur.oinam.com. Procedural, from OSM, Open Buildings, and WorldCover. Imphal
Phase 1: 262,527 buildings, 645 megapixels at 0.5 m/px, 162 frames in about 150 seconds
per view. What it learned that applies here: four 90° views rather than 24, a resumable
one-view-at-a-time build, tiles and renders on an external drive, smoothing while zoomed
out, and a preview image and film cut from the tiles.

## Isometric Cities guide

https://isometriccities.com/guide/how-to-make-an-isometric-city-map/. Sorts maps into
AI-drawn (82), rendered from open data (29), and 3D dioramas (17). For our method it
warns the result "can look like a diagram unless you add textures and landmark sprites",
and recommends three shades per color, a landmark crop as the link preview, and a short
zoom-in recording for sharing.
