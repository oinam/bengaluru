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

## Satellite imagery: what it would take

Read 2026-11-18, after Brajeshwar asked what stops us from using satellite images, what
buying them would cost, and whether the free ones would do. Nothing below is in use;
no source here has a row in `docs/DATA.md`.

**What stops us.** Only rule 1 in `CLAUDE.md`, which is his to change. It is there so
the map stays a drawing with a clean license, and so "no photographs or satellite images
appear in it" stays true. Satellites already shape the map at one remove: WorldCover
comes from Sentinel imagery, and Open Buildings' footprints and heights from
high-resolution imagery. A satellite photo also looks straight down, so it has roofs and
ground but no walls; it cannot become an isometric picture by itself. What it can add is
truth about color and placement: each roof's color, where trees really stand, pools,
courts, and bare ground.

**Free and open.** The map is drawn at about half a meter per pixel, and nothing free
and open comes near that.

| Source | Detail | Terms | Use to us |
|---|---|---|---|
| Copernicus Sentinel-2 | 10 m | free, full, and open; credit "Contains modified Copernicus Sentinel data [year]" | ground tone, seasonal green, how full a lake is; a pixel spans two or three houses, so not roofs |
| ISRO Bhoonidhi open data | coarser than 5 m | open to all users under the Indian Space Policy 2023 | the same, no better |
| Google, Esri, Bing, Mapbox imagery | sub-meter | free to look at, not open; Google's Map Tiles policy bars image analysis, machine interpretation, and content based on its content | none |
| Google Photorealistic 3D Tiles | 3D mesh | the same policy; coverage of Bengaluru not confirmed | none |

**Bought once, from ISRO.** NSIL sells ISRO's imagery through Bhoonidhi, by the scene,
paid in advance. Its list of 26 April 2024 prices, for Indian users outside government:

| Product | Detail | Scene | Price |
|---|---|---|---|
| Cartosat-3, pan-sharpened color | 0.45 m | 10 × 10 km | Rs 2,400 |
| Cartosat-3, orthorectified panchromatic | 0.28 m | 17 × 17 km | Rs 4,810 |
| Cartosat-2S, pan-sharpened color | 0.60 m | 9.8 × 9.8 km | Rs 6,190 |

The map with the airport is 34.7 × 44.2 km, about 1,535 km²: 16 scenes of 10 × 10 km by
area alone, and more likely 20 to 30 since scenes will not line up with it. In
Cartosat-3 color that is Rs 48,000 to 72,000 before tax. Not checked: today's prices,
whether recent cloud-free scenes cover all of it, and what the Bhoonidhi license allows.
A 2022 NRSC deck describes the base license as single-user internal use, and says
hosting the imagery on the web may cost up to three times the price; whether a map
derived from the imagery, holding none of its pixels, may be published is the question
to put to NSIL (eodata@nsilindia.co.in) in writing before buying.

**Bought once, commercially.** Resellers of Maxar, Airbus, and Planet imagery quote by
the square kilometer, and their published ranges disagree: about $8 to 18 for archive
imagery at 50 cm and $17 to 55 at 30 cm, with a 25 km² minimum (Geopera's 2026 guide).
For 1,535 km² that is roughly $12,000 to 28,000 at 50 cm and $26,000 to 84,000 at 30 cm,
before any volume discount. The base price is a single-user license for internal use;
showing imagery in public is another tier, reported at about 20% more for Maxar. It is a
one-time fee for a license, not ownership.

**Time.** Sentinel-2 as one more driver of ground tone: one or two sessions and a
night's rebuild. Roof colors and tree positions from bought imagery: the order itself,
then two to four sessions to line the scenes up with the footprints, take one color per
roof, and snap it to the palette, then a night or two to rebuild. Both are estimates.

**What changes if he does.** Rule 1 forbids sampling a raster for color, so it would
need rewording. The site's "from open data" would become open data and licensed ISRO
imagery, and its credits would say so. The map would still hold no photographic pixels.

Sources: [Bhoonidhi commercial products FAQ, 26 April 2024](https://bhoonidhi.nrsc.gov.in/imgarchive/bhoonidhi_videos_help/Commercial_Products_FAQ.pdf),
[NRSC pricing and licensing deck, 2022](https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/help/archives/BWS1_02Nov2022/5-BWS1-PricingLicensing.pdf),
[NRSC Bhoonidhi brochure 2025](https://www.nrsc.gov.in/nrscnew/assets/pdf/brochures/Bhoonidhi_Brochure_2025.pdf),
[Geopera, satellite imagery cost guide 2026](https://geopera.com/blog/satellite-imagery-cost-guide),
[Upstream Tech, commercial imagery use FAQ](https://support.upstream.tech/article/78-commercial-imagery-use-faq),
[Google Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies),
[Copernicus Data Space terms](https://dataspace.copernicus.eu/node/10).
