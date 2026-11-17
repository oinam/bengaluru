import OpenSeadragon from "openseadragon";

// Place names over the map. The city has tens of thousands of named places, so only the
// ones in view get an element: they are chosen again each time the map comes to rest, and
// follow the map while it moves.

export interface Place {
  name: string;
  kind: string;
  x: number;
  y: number;
  tier: number;
}

interface Shown {
  place: Place;
  element: HTMLDivElement;
}

// The image zoom at which each tier appears: areas first, the smallest places last.
const TIER_MIN_ZOOM: Record<number, number> = { 1: 0, 2: 0.18, 3: 1.2 };
const LABEL_CHAR_PX = 7;
const LABEL_HEIGHT_PX = 20;
// Places are kept in squares of this many image pixels, so a close view reads only a few.
const CELL_PX = 2048;
const MAX_LABELS = 150;

export function startLabels(viewer: OpenSeadragon.Viewer): { show: (places: Place[]) => void } {
  const source = (viewer.drawer as unknown as { canvas: HTMLCanvasElement }).canvas;
  const layer = document.createElement("div");
  layer.className = "labels";
  source.after(layer);
  const cells = new Map<string, Place[]>();
  const pool: HTMLDivElement[] = [];
  let shown: Shown[] = [];

  function candidates(zoom: number): Place[] {
    const bounds = viewer.viewport.viewportToImageRectangle(viewer.viewport.getBounds(true));
    const found: Place[] = [];
    const lastColumn = Math.floor((bounds.x + bounds.width) / CELL_PX);
    const lastRow = Math.floor((bounds.y + bounds.height) / CELL_PX);
    for (let row = Math.floor(bounds.y / CELL_PX); row <= lastRow; row++) {
      for (let column = Math.floor(bounds.x / CELL_PX); column <= lastColumn; column++) {
        for (const place of cells.get(`${column},${row}`) ?? []) {
          if (zoom >= (TIER_MIN_ZOOM[place.tier] ?? Infinity)) {
            found.push(place);
          }
        }
      }
    }
    return found.sort((a, b) => a.tier - b.tier || a.name.localeCompare(b.name) || a.x - b.x);
  }

  function position(): void {
    for (const { place, element } of shown) {
      const point = viewer.viewport.imageToViewerElementCoordinates(
        new OpenSeadragon.Point(place.x, place.y),
      );
      element.style.transform = `translate(${point.x.toFixed(1)}px, ${point.y.toFixed(1)}px) translate(-50%, -50%)`;
    }
  }

  // Areas win over places, and a name gives way to one already placed where it would sit.
  function choose(): void {
    if (!viewer.world.getItemCount()) {
      return;
    }
    const zoom = viewer.viewport.viewportToImageZoom(viewer.viewport.getZoom(true));
    const width = layer.clientWidth;
    const height = layer.clientHeight;
    const taken: { left: number; right: number; top: number; bottom: number }[] = [];
    const next: Place[] = [];
    for (const place of candidates(zoom)) {
      if (next.length >= MAX_LABELS) {
        break;
      }
      const point = viewer.viewport.imageToViewerElementCoordinates(
        new OpenSeadragon.Point(place.x, place.y),
      );
      const halfWidth = (place.name.length * LABEL_CHAR_PX) / 2;
      const box = {
        left: point.x - halfWidth,
        right: point.x + halfWidth,
        top: point.y - LABEL_HEIGHT_PX / 2,
        bottom: point.y + LABEL_HEIGHT_PX / 2,
      };
      const inside = box.right > 0 && box.left < width && box.bottom > 0 && box.top < height;
      const free = !taken.some(
        (other) =>
          box.left < other.right &&
          box.right > other.left &&
          box.top < other.bottom &&
          box.bottom > other.top,
      );
      if (inside && free) {
        taken.push(box);
        next.push(place);
      }
    }
    while (pool.length < next.length) {
      const element = document.createElement("div");
      layer.append(element);
      pool.push(element);
    }
    shown = [];
    for (const [index, element] of pool.entries()) {
      const place = next[index];
      element.hidden = !place;
      if (place) {
        element.className = `label label-${place.tier}`;
        element.textContent = place.name;
        shown.push({ place, element });
      }
    }
    position();
  }

  viewer.addHandler("update-viewport", position);
  viewer.addHandler("animation-finish", choose);
  viewer.addHandler("resize", choose);

  // The places in the open view's image pixels, after loading or turning the map.
  function show(places: Place[]): void {
    cells.clear();
    for (const place of places) {
      const key = `${Math.floor(place.x / CELL_PX)},${Math.floor(place.y / CELL_PX)}`;
      const cell = cells.get(key);
      if (cell) {
        cell.push(place);
      } else {
        cells.set(key, [place]);
      }
    }
    choose();
  }

  return { show };
}
