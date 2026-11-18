# Prior art

Read 2026-11-16. The Manipur project's `docs/RESEARCH.md` covers the wider field
(tiny.london, isometric.nyc, Pixel Singapore, Isopolis SF).

## Is there a Bengaluru map already?

No, as of 2026-11-16. The Isometric Cities directory's India page lists three maps:
Isometric Imphal (ours), Isometric Mumbai, and Pixel Chennai. A web search found no
isometric pixel-art map of Bengaluru. The nearest thing is a commissioned illustrated
map by Rod Hunt for the Bhartiya City development outside the city, which is neither
pixel art nor of the city.

Found 2026-11-18: Isometric Bengaluru by Vinay, published 2026-10-07. It is not a map of
the city but four isometric data pieces about it; see "Isometric Bengaluru, the data
pieces" below.

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

https://isometricmumbai.com/ by Aryan Gupta, launched 2026-11-07. Read 2026-11-18 from
the README of its repository, `flash1405/isometric-mumbai` (MIT), and its model card.

- Greater Mumbai, Colaba to Dahisar, at 0.293 m per pixel, about 5 GB of WebP tiles on a
  Cloudflare Worker and R2. Taxis, buses, and trains are simulated in the viewer.
- Control render: Google's 3D mesh is nearly flat in Mumbai, so he extrudes his own city
  in three.js from GlobalBuildingAtlas footprints, with heights from OSM, Wikidata, Open
  Buildings 2.5D, and Wikipedia's list of towers, and drapes Google's imagery, rendered
  straight down, on the roofs and the ground.
- Teacher: GPT Image redraws about 700 to 800 of those render tiles as pixel art.
- Student: a rank-32 LoRA on FLUX.2 klein 4B (Apache 2.0) learns render to art from those
  pairs, in about an hour on one rented B200. It then paints the city in about 8,000
  calls of a 1024 px tile, 4 steps, about 2.5 seconds each, in four passes so every tile
  has finished neighbors; about an hour on one B200 and eight A100s.
- About 20 landmarks are repainted by GPT Image one at a time.
- Lesson for us: the picture's detail comes from the image model and from real imagery
  under it. The second is what rule 1 forbids, and Google's Map Tiles policy bars
  content based on its content; that risk is his.

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
Cartosat-3 color that is Rs 48,000 to 72,000 before tax, about $510 to $770 at the Rs 94
to the dollar of mid-November 2026; a scene is about $26. Not checked: today's prices,
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

## What the AI-drawn maps cost

Read 2026-11-18, after Brajeshwar asked how Isometric Mumbai and Pixel Chennai are made,
why they look better than ours, and what they cost. Dollar figures are the makers' own
where quoted; the rest are arithmetic from their numbers and are marked so.

They all work the same way. A plain render of the city, the control, is repainted tile
by tile by an image model. A frontier model (GPT Image, Nano Banana) paints a few dozen
to a few hundred tiles well but is slow, costly, and uneven, so those become lessons for
a small open model, which then paints the other thousands on rented GPUs. The look comes
from the model: texture, light, windows, and roof clutter that our renderer does not
draw. Ours is their first step and stops there.

| Map | Control render | Teacher | Student and hardware | Cost |
|---|---|---|---|---|
| Isometric Mumbai | own extrusions with Google imagery draped on | about 800 GPT Image tiles | FLUX.2 klein 4B LoRA; rented B200 and A100s | maker's table: teacher $100 to 150, generation $10 to 30, training about an hour of a B200, hosting about $0; roughly $150 to 250 in all |
| Pixel Chennai | OSM and Overture extrusions with a canopy map, like ours | "a few" Nano Banana tiles | Qwen-Image-Edit-2511 LoRA with a 4-step LoRA, on the maker's MacBook | not published; a few dollars of teacher tiles and no rented GPU, so probably under $50 beyond the laptop (my estimate) |
| Isometric NYC | Google 3D tiles | about 40 pairs from Nano Banana | Qwen Image-Edit LoRA; rented H100 | fine-tune "~12 bucks"; about 40,000 tiles at "less than $3 an hour and more than 200 generations/hour", so at most about $600 of GPU (my arithmetic) |
| Isometric SF | Google 3D tiles | 1,460 Nano Banana 2 seeds | FLUX.2 klein 4B LoRA; rented H100s | about 172 H100-hours with experiments; at $2 to 4 an hour, $350 to 700 (my arithmetic) |

None of them publishes a total, and none counts the maker's time, which the NYC and SF
write-ups say was the real cost: weeks of checking seams, water, and trees by eye,
because the models cannot find their own mistakes.

**What it would mean here.** Pixel Chennai's route fits rule 1: its control render is
drawn from open data, as ours is, and no photograph of the city goes in. A view of our
map with the airport is about 3.4 gigapixels, about 3,200 tiles of 1024 px by area, and
perhaps 8,000 to 13,000 calls with the overlap the seam-free passes need (my estimate).
At 1 to 2.5 seconds a call that is 3 to 9 GPU-hours a view, so about $10 to 40 a view
and $40 to 160 for the four views, on top of $5 to 150 for the teacher's tiles depending
on how many and which model. `CLAUDE.md` parks this route because he has no GPU; rented
by the hour, the GPU is the small part. The larger costs are the ones above: the
checking by eye, and three things this project holds to that a painted layer strains.
The output is no longer the same for the same inputs unless the model, its weights, and
the hardware are pinned (rule 3). A model invents detail that is not in the data. And
the teacher's output carries its provider's terms.

Sources: [Isometric Mumbai README](https://github.com/flash1405/isometric-mumbai),
[its model card](https://huggingface.co/Flash1405/isometric-mumbai),
[launch post](https://x.com/flash1405/status/2118904458767925479),
[Isometric NYC write-up](https://cannoneyed.com/projects/isometric-nyc),
[How to make isometric cities, Justin Chavez](https://www.justinchavez.com/blog/isometric-sf-how/),
[Pixel Stanford's comparison table](https://github.com/aadityabuilds/isometric-pixxels),
[H100 rental prices, October 2026](https://neurohive.io/en/guides/cloud-gpu-pricing/).

## Isometric Bengaluru, the data pieces

https://vinaydotblog.github.io/isometric-bengaluru/, repository
`vinaydotblog/isometric-bengaluru`. Read 2026-11-18, the pages and the source, after
Brajeshwar asked what we can learn from it.

It is a different kind of thing from ours: four small isometric charts and a Delhi Metro
companion, about 200 KB of hand-written HTML, CSS, and JavaScript with three.js from a
CDN, made in one day (three commits on 2026-10-07). The layouts are schematic and say
so. The repository has no license, so its ideas are open to us and its code is not.

- Concrete Tide: land cover from 1973 to 2020 as a disc of cells, played as a film.
- Namma Metro, Layered: every opening since 2011 on a timeline that can be scrubbed and
  replayed; lines in their own colors, viaducts above a slab and tunnels glowing through
  it, lines under construction dashed; a ledger of kilometers and stations; click a line
  to hide it; three themes (night, dusk, paper).
- Monsoon Almanac: IMD normals as rain gauges, in SVG projected by hand.
- Lakhs of People: one cube per 100,000 people by census, colored by decade.

What is worth taking, most useful first:

1. **The metro as something to read.** Ours draws every track alike. Theirs gives each
   line its color, names the stations, and shows what is being built. On our map that
   is a layer in the viewer over the real viaducts, like the water's, so it needs no
   new render. Our extract lacks what it needs: line colors sit on OSM's route
   relations, which `fetch` drops, and only 15 of 329 metro ways in the central area
   carry an opening date. The relations are in the Geofabrik file already on disk;
   opening dates would need a source and a row in `docs/DATA.md`.
2. **Time.** Their best idea is the scrubber: the same picture at different dates. Once
   the lines have opening dates, "the metro in 2011, 2017, today" is the same layer with
   a slider. The Blue Line to the airport, under construction, would meet the airport
   the map is about to gain.
3. **Kannada.** Their title is ಬೆಂಗಳೂರು and every piece carries its Kannada name; Pixel
   Chennai does the same in Tamil. Our labels and search are English only. In the
   central area's OSM data, 74% of named places, 94% of stations, and 85% of named roads
   already have `name:kn`, so search and labels in both scripts need `prepare` to keep
   that tag and the viewer to offer it.
4. **A palette with a local reason.** Each piece takes its colors from something of the
   city: kumkum, Mysore silk, tabebuia blossom, the metro's line colors. Our look is
   still Manipur's. Bengaluru's flowering trees (pink tabebuia, purple jacaranda, red
   gulmohar) among our 3.5 million green ones would be the plainest way to make the map
   look like this city; it is a look decision, to be shown to Brajeshwar as options.
5. **Numbers up front.** Every piece opens with one sentence of figures ("tree cover
   fell from 68% to 3%") and offers its data as a table. Our About page states none of
   ours: 1.9 million buildings, 3.5 million trees, 715 km of track.
6. **Care in the small things.** A "read with care" note on what is schematic, palettes
   checked for color-blind readers, a tooltip on everything. We say "may be inaccurate"
   and have not checked our palette.

What does not carry over: the three.js scenes are a few thousand objects, where our map
is gigapixels of fixed tiles, and their themes repaint a scene in a frame, where a night
palette for ours is a second render of the whole city.
