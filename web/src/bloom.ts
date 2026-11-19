import OpenSeadragon from "openseadragon";

import { TILE_BASE } from "./tiles";
import type { View } from "./views";

// A flowering tree: the colors it wears on the map, and the months, from 1, it flowers in.
interface Blossom {
  colors: string[];
  months: number[];
}

// What the manifest says of the layers laid over the map.
export interface Layers {
  tile_px: number;
  bloom: Record<string, Blossom>;
}

interface Shade {
  red: number;
  green: number;
  blue: number;
  kind: string;
}

// The part of the viewer's tile download this file uses.
interface Job {
  src: string;
  userData: { image?: HTMLImageElement };
  finish: (data: HTMLCanvasElement | null, request: null, error?: string) => void;
}

// The map keeps the city's time, wherever it is read.
const CITY_TIME = "Asia/Kolkata";
// The month chosen by hand, from 1; nothing kept means the month it is in the city.
const MONTH_KEY = "bloom-month";
const MONTHS = Array.from({ length: 12 }, (_, index) =>
  new Intl.DateTimeFormat("en-US", { month: "long", timeZone: "UTC" }).format(
    Date.UTC(2000, index, 15),
  ),
);

function cityMonth(): number {
  return Number(
    new Intl.DateTimeFormat("en-US", { month: "numeric", timeZone: CITY_TIME }).format(new Date()),
  );
}

function chosenMonth(): number | null {
  try {
    const month = Number(localStorage.getItem(MONTH_KEY));
    return month >= 1 && month <= 12 ? month : null;
  } catch {
    return null;
  }
}

function saveMonth(month: number | null): void {
  try {
    if (month) {
      localStorage.setItem(MONTH_KEY, String(month));
    } else {
      localStorage.removeItem(MONTH_KEY);
    }
  } catch {
    // The choice lasts for this visit only.
  }
}

function shades(bloom: Record<string, Blossom>): Shade[] {
  return Object.entries(bloom).flatMap(([kind, blossom]) =>
    blossom.colors.map((color) => {
      const value = parseInt(color.slice(1), 16);
      return { red: value >> 16, green: (value >> 8) & 255, blue: value & 255, kind };
    }),
  );
}

// One picture holds every tree's blossom. A tile is cleared of the trees not in flower as
// it arrives: each pixel belongs to the tree whose color it is nearest.
function onlyInFlower(
  image: HTMLImageElement,
  palette: Shade[],
  inFlower: Set<string>,
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    return canvas;
  }
  context.drawImage(image, 0, 0);
  const picture = context.getImageData(0, 0, canvas.width, canvas.height);
  const data = picture.data;
  for (let index = 0; index < data.length; index += 4) {
    if (data[index + 3] === 0) {
      continue;
    }
    let nearest = "";
    let best = Infinity;
    for (const shade of palette) {
      const distance =
        ((data[index] ?? 0) - shade.red) ** 2 +
        ((data[index + 1] ?? 0) - shade.green) ** 2 +
        ((data[index + 2] ?? 0) - shade.blue) ** 2;
      if (distance < best) {
        best = distance;
        nearest = shade.kind;
      }
    }
    if (!inFlower.has(nearest)) {
      data[index + 3] = 0;
    }
  }
  context.putImageData(picture, 0, 0);
  return canvas;
}

export function startBloom(
  viewer: OpenSeadragon.Viewer,
  select: HTMLSelectElement,
  layers: Layers,
): { refresh: (view: View, area: string) => void } {
  const palette = shades(layers.bloom);
  let pyramid: string | null = null;
  let item: OpenSeadragon.TiledImage | null = null;
  // Counts the pictures asked for, so one that arrives after a newer was asked for is dropped.
  let asked = 0;

  function month(): number {
    return chosenMonth() ?? cityMonth();
  }

  function inFlower(): Set<string> {
    const now = month();
    return new Set(
      Object.entries(layers.bloom)
        .filter(([, blossom]) => blossom.months.includes(now))
        .map(([kind]) => kind),
    );
  }

  function tileSource(url: string, kinds: Set<string>): object {
    const size = viewer.world.getItemAt(0).getContentSize();
    return {
      width: size.x,
      height: size.y,
      tileSize: layers.tile_px,
      tileOverlap: 0,
      getTileUrl: (level: number, x: number, y: number) =>
        `${url}_files/${String(level)}/${String(x)}_${String(y)}.webp`,
      hasTransparency: () => true,
      downloadTileStart: (job: Job) => {
        const image = new Image();
        job.userData.image = image;
        image.crossOrigin = "anonymous";
        image.onload = () => {
          job.finish(onlyInFlower(image, palette, kinds), null);
        };
        image.onerror = image.onabort = () => {
          job.finish(null, null, "Image load aborted.");
        };
        image.src = job.src;
      },
      downloadTileAbort: (job: Job) => {
        const image = job.userData.image;
        if (image) {
          image.onload = image.onerror = image.onabort = null;
        }
      },
    };
  }

  function show(): void {
    asked += 1;
    const mine = asked;
    if (item) {
      viewer.world.removeItem(item);
      item = null;
    }
    const kinds = inFlower();
    if (!pyramid || !kinds.size || !viewer.world.getItemCount()) {
      return;
    }
    viewer.addTiledImage({
      tileSource: tileSource(pyramid, kinds),
      success: (event) => {
        const added = (event as unknown as { item: OpenSeadragon.TiledImage }).item;
        if (mine === asked) {
          item = added;
        } else {
          viewer.world.removeItem(added);
        }
      },
    });
  }

  // After the map opens or turns: opening cleared the last view's blossom with its map.
  function refresh(view: View, area: string): void {
    item = null;
    pyramid = view.bloom ? `${TILE_BASE}pyramid/${view.bloom}/${area}` : null;
    select.closest("label")?.toggleAttribute("hidden", !pyramid);
    show();
  }

  const options = [
    new Option(`This month, ${MONTHS[cityMonth() - 1] ?? ""}`, ""),
    ...MONTHS.map((name, index) => new Option(name, String(index + 1))),
  ];
  select.replaceChildren(...options);
  select.value = String(chosenMonth() ?? "");
  select.addEventListener("change", () => {
    saveMonth(Number(select.value) || null);
    show();
  });

  return { refresh };
}
