import OpenSeadragon from "openseadragon";

import { TILE_BASE } from "./tiles";

// The metro, drawn over the map: each track in its line's color, dashed where the line
// is being built and faint where it runs underground, with a dot and a name at each
// station. Open track sits on the viaduct the map already draws.

type Level = "tunnel" | "ground" | "raised";

interface Line {
  colour: string | null;
  open: boolean;
  level: Level;
  points: [number, number][];
}

interface Station {
  name: string;
  x: number;
  y: number;
  open: boolean;
  level: Level;
}

interface Metro {
  raised_px: number;
  lines: Line[];
  stations: Station[];
}

// A line in the open view's image pixels, with the box that holds it.
interface Track extends Line {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

const METRO_INDEX = `${TILE_BASE}metro.json`;
// The metro shows unless the visitor turned it off.
const SHOWN_KEY = "metro";
// Drawn from the ground up, so a viaduct crosses over a tunnel.
const LEVELS: Level[] = ["tunnel", "ground", "raised"];
const CASING = "#1f2a2e";
const PAPER = "#ffffff";
// For a line whose route gives no color.
const PLAIN = "#f0ece2";
const TUNNEL_ALPHA = 0.5;
// A line is this wide in map pixels, and never thinner than this on screen.
const WIDTH_MAP_PX = 3;
const MIN_WIDTH_PX = 2.5;
const STATION_MAP_PX = 5;
const MIN_STATION_PX = 3;
const MAX_STATION_PX = 7;
// Below this the whole network is on screen and the names would crowd it.
const NAMES_MIN_IMAGE_ZOOM = 0.15;
const NAME_PX = 12;

function wantsMetro(): boolean {
  try {
    return localStorage.getItem(SHOWN_KEY) !== "off";
  } catch {
    return true;
  }
}

function saveChoice(shown: boolean): void {
  try {
    localStorage.setItem(SHOWN_KEY, shown ? "on" : "off");
  } catch {
    // The choice lasts for this visit only.
  }
}

export function startMetro(
  viewer: OpenSeadragon.Viewer,
  toggle: HTMLInputElement,
  toImage: (x: number, y: number) => [number, number],
): { refresh: () => void } {
  const source = (viewer.drawer as unknown as { canvas: HTMLCanvasElement }).canvas;
  const canvas = document.createElement("canvas");
  canvas.className = "metro";
  source.after(canvas);
  const context = canvas.getContext("2d");
  const font = getComputedStyle(document.body).fontFamily;

  let metro: Metro | null = null;
  let tracks: Track[] = [];
  let stations: Station[] = [];
  let shown = wantsMetro();
  toggle.checked = shown;

  function trace(track: Track, scale: number, originX: number, originY: number): void {
    if (!context) {
      return;
    }
    context.beginPath();
    for (const [index, [x, y]] of track.points.entries()) {
      if (index) {
        context.lineTo(originX + x * scale, originY + y * scale);
      } else {
        context.moveTo(originX + x * scale, originY + y * scale);
      }
    }
    context.stroke();
  }

  function draw(): void {
    if (!context) {
      return;
    }
    if (canvas.width !== source.width || canvas.height !== source.height) {
      canvas.width = source.width;
      canvas.height = source.height;
    }
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!shown || !metro || !viewer.world.getItemCount()) {
      return;
    }
    const zoom = viewer.viewport.viewportToImageZoom(viewer.viewport.getZoom(true));
    const density = source.width / source.clientWidth;
    const scale = zoom * density;
    const origin = viewer.viewport.imageToViewerElementCoordinates(new OpenSeadragon.Point(0, 0));
    const originX = origin.x * density;
    const originY = origin.y * density;
    const left = -originX / scale;
    const top = -originY / scale;
    const right = left + canvas.width / scale;
    const bottom = top + canvas.height / scale;
    const width = Math.max(MIN_WIDTH_PX, WIDTH_MAP_PX * zoom) * density;

    context.lineJoin = "round";
    const inView = tracks.filter(
      (track) =>
        track.right > left && track.left < right && track.bottom > top && track.top < bottom,
    );
    for (const level of LEVELS) {
      const here = inView.filter((track) => track.level === level);
      context.globalAlpha = level === "tunnel" ? TUNNEL_ALPHA : 1;
      // Every casing before any color, so one track's edge never cuts across its twin.
      context.setLineDash([]);
      context.lineCap = "round";
      context.strokeStyle = CASING;
      context.lineWidth = width + 2 * density;
      for (const track of here) {
        trace(track, scale, originX, originY);
      }
      context.lineWidth = width;
      for (const track of here) {
        context.strokeStyle = track.colour ?? PLAIN;
        context.lineCap = track.open ? "round" : "butt";
        context.setLineDash(track.open ? [] : [width * 2, width * 1.5]);
        trace(track, scale, originX, originY);
      }
    }
    context.globalAlpha = 1;
    context.setLineDash([]);

    const radius =
      Math.min(MAX_STATION_PX, Math.max(MIN_STATION_PX, STATION_MAP_PX * zoom)) * density;
    const named = zoom >= NAMES_MIN_IMAGE_ZOOM;
    const taken: { left: number; right: number; y: number }[] = [];
    context.font = `600 ${String(NAME_PX * density)}px ${font}`;
    context.textBaseline = "middle";
    for (const station of stations) {
      if (station.x < left || station.x > right || station.y < top || station.y > bottom) {
        continue;
      }
      const x = originX + station.x * scale;
      const y = originY + station.y * scale;
      context.beginPath();
      context.arc(x, y, radius, 0, 2 * Math.PI);
      context.fillStyle = station.open ? PAPER : CASING;
      context.strokeStyle = station.open ? CASING : PAPER;
      context.lineWidth = 1.5 * density;
      context.fill();
      context.stroke();
      if (!named) {
        continue;
      }
      // A name gives way to one already written where it would sit.
      const start = x + radius + 4 * density;
      const end = start + context.measureText(station.name).width;
      const height = NAME_PX * density * 1.3;
      if (
        taken.some(
          (other) => start < other.right && end > other.left && Math.abs(y - other.y) < height,
        )
      ) {
        continue;
      }
      taken.push({ left: start, right: end, y });
      context.strokeStyle = CASING;
      context.lineWidth = 3 * density;
      context.strokeText(station.name, start, y);
      context.fillStyle = PAPER;
      context.fillText(station.name, start, y);
    }
  }

  // Into the open view's pixels, after loading or turning the map. What is raised moves
  // up onto the viaduct's deck, by the same lift in every view.
  function refresh(): void {
    if (!metro) {
      return;
    }
    const lift = (level: Level) => (level === "raised" ? (metro?.raised_px ?? 0) : 0);
    tracks = metro.lines.map((line) => {
      const points = line.points.map(([x, y]): [number, number] => {
        const [viewX, viewY] = toImage(x, y);
        return [viewX, viewY - lift(line.level)];
      });
      const xs = points.map(([x]) => x);
      const ys = points.map(([, y]) => y);
      return {
        ...line,
        points,
        left: Math.min(...xs),
        top: Math.min(...ys),
        right: Math.max(...xs),
        bottom: Math.max(...ys),
      };
    });
    stations = metro.stations.map((station) => {
      const [x, y] = toImage(station.x, station.y);
      return { ...station, x, y: y - lift(station.level) };
    });
    draw();
  }

  toggle.addEventListener("change", () => {
    shown = toggle.checked;
    saveChoice(shown);
    draw();
  });
  viewer.addHandler("update-viewport", draw);
  viewer.addHandler("resize", draw);

  fetch(METRO_INDEX, { cache: "no-cache" })
    .then((response) => response.json())
    .then((loaded: Metro) => {
      if (loaded.lines.length) {
        metro = loaded;
        // The switch appears only once there is a metro to switch.
        toggle.closest("label")?.removeAttribute("hidden");
        refresh();
      }
    })
    .catch(() => {
      // A map built before the metro was added has no index for it, and shows none.
    });

  return { refresh };
}
