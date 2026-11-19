import OpenSeadragon from "openseadragon";
import { startBloom, type Layers } from "./bloom";
import { startNight } from "./daylight";
import { startLabels, type Place } from "./labels";
import { startMetro } from "./metro";
import { startPanel } from "./panel";
import { startRivers } from "./rivers";
import { TILE_BASE } from "./tiles";
import { startWater } from "./water";
import {
  NORTH_UP_VIEW,
  convertPoint,
  northAngle,
  toImage,
  toLonLat,
  viewOrder,
  type Frame,
  type View,
} from "./views";

// A place to show: a spot on the earth, how close to stand, and which way to face.
interface Target {
  lon: number;
  lat: number;
  zoom: number;
  view: string;
}

const MANIFEST = `${TILE_BASE}manifest.json`;
const STILL_MAX_MS = 4000;
const SEARCH_INDEX = `${TILE_BASE}search.json`;
const MAX_RESULTS = 12;
const FLY_TO_IMAGE_ZOOM = 1.5;
const TILT_FULL_ZOOM = 0.1;
const TILT_NONE_ZOOM = 0.4;
const NEW_ISSUE_URL = "https://github.com/oinam/bengaluru/issues/new";
const NEAR_PLACE_MAX_PX = 800;
// Vidhana Soudha, with Cubbon Park below it.
const OPENING_VIEW: Target = { lon: 77.5906, lat: 12.9785, zoom: 0.5, view: NORTH_UP_VIEW };
const SHORTCUT_ZOOM = 0.9;
const AREA_ZOOM = 0.4;
const SUBURB_ZOOM = 0.25;
const ZOOM_STEP = 1.6;
// A key press moves the map this fraction of the screen.
const PAN_STEP = 0.15;
const PAN_KEYS: Record<string, [number, number]> = {
  ArrowUp: [0, -1],
  KeyW: [0, -1],
  ArrowDown: [0, 1],
  KeyS: [0, 1],
  ArrowLeft: [-1, 0],
  KeyA: [-1, 0],
  ArrowRight: [1, 0],
  KeyD: [1, 0],
};
// The panel's places to go to: a short name, longitude and latitude, and the zoom that
// fits the place on screen. A first list, for Brajeshwar to change. The spots are the
// centers of the places as OpenStreetMap maps them.
const SHORTCUTS: [string, number, number, number][] = [
  ["Vidhana Soudha", 77.59062, 12.97975, SHORTCUT_ZOOM],
  ["Cubbon Park", 77.59219, 12.97425, AREA_ZOOM],
  ["MG Road", 77.61008, 12.97489, SHORTCUT_ZOOM],
  ["Ulsoor Lake", 77.61917, 12.98239, AREA_ZOOM],
  ["Bangalore Palace", 77.59201, 12.9986, SHORTCUT_ZOOM],
  ["Majestic", 77.57229, 12.97805, SHORTCUT_ZOOM],
  ["KR Market", 77.57745, 12.96396, SHORTCUT_ZOOM],
  ["Lalbagh", 77.58691, 12.94886, AREA_ZOOM],
  ["Bull Temple", 77.56873, 12.94176, SHORTCUT_ZOOM],
  ["Sankey Tank", 77.57379, 13.00999, AREA_ZOOM],
  ["IISc", 77.56569, 13.0194, AREA_ZOOM],
  ["ISKCON", 77.55114, 13.00994, SHORTCUT_ZOOM],
  ["Malleswaram", 77.5669, 13.00168, SUBURB_ZOOM],
  ["Indiranagar", 77.63866, 12.97833, SUBURB_ZOOM],
  ["Koramangala", 77.62152, 12.93979, SUBURB_ZOOM],
  ["Jayanagar", 77.58015, 12.92951, SUBURB_ZOOM],
];

function byId<T extends HTMLElement>(id: string, type: new () => T): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) {
    throw new Error(`Missing element #${id}`);
  }
  return element;
}

const viewer = OpenSeadragon({
  element: byId("map", HTMLElement),
  prefixUrl: "",
  crossOriginPolicy: "Anonymous",
  drawer: "canvas",
  showNavigationControl: false,
  imageSmoothingEnabled: false,
  maxZoomPixelRatio: 8,
  minZoomImageRatio: 0.8,
  visibilityRatio: 0.4,
  animationTime: 0.6,
  springStiffness: 9,
  background: "#1f2a2e",
  // The blossom lies over the map as a second picture of the same size, so places are the same.
  silenceMultiImageWarnings: true,
} as OpenSeadragon.Options);

function imageZoomToViewport(zoom: number): number {
  return viewer.viewport.imageToViewportZoom(zoom);
}

// Links read #zoom/latitude/longitude, and /view when the map is turned from north up.
function readHash(): Target | null {
  const parts = location.hash.slice(1).split("/");
  const [zoom = NaN, lat = NaN, lon = NaN] = parts.slice(0, 3).map(Number);
  const view = parts[3] ?? NORTH_UP_VIEW;
  if (parts.length < 3 || parts.length > 4 || ![zoom, lat, lon].every(Number.isFinite)) {
    return null;
  }
  return { zoom, lat, lon, view: views[view] ? view : NORTH_UP_VIEW };
}

function goTo(x: number, y: number, imageZoom: number, immediately: boolean): void {
  const point = viewer.viewport.imageToViewportCoordinates(x, y);
  viewer.viewport.panTo(point, immediately);
  viewer.viewport.zoomTo(imageZoomToViewport(imageZoom), undefined, immediately);
}

function goToSpot(lon: number, lat: number, imageZoom: number, immediately: boolean): void {
  const [x, y] = toImage(viewData(currentView), lon, lat);
  goTo(x, y, imageZoom, immediately);
}

function viewCenter(): OpenSeadragon.Point {
  return viewer.viewport.viewportToImageCoordinates(viewer.viewport.getCenter());
}

function viewHash(): string {
  const center = viewCenter();
  const [lon, lat] = toLonLat(viewData(currentView), center.x, center.y);
  const zoom = imageZoom();
  const suffix = currentView === NORTH_UP_VIEW ? "" : `/${currentView}`;
  return `#${zoom.toFixed(3)}/${lat.toFixed(5)}/${lon.toFixed(5)}${suffix}`;
}

function writeHash(): void {
  history.replaceState(null, "", viewHash());
}

function nearestPlace(): string | null {
  const center = viewCenter();
  let nearest: string | null = null;
  let best = NEAR_PLACE_MAX_PX;
  for (const place of places) {
    const distance = Math.hypot(place.x - center.x, place.y - center.y);
    if (distance < best) {
      best = distance;
      nearest = place.name;
    }
  }
  return nearest;
}

function updateCorrectionLink(): void {
  const near = nearestPlace();
  const title = near ? `Correction near ${near}` : "Map correction";
  const body = [
    `**Map view:** ${location.origin}${location.pathname}${viewHash()}`,
    "",
    "**What is wrong or missing?**",
    "",
    "",
    "**How do you know?** (For example, you live nearby, or a public document says so.)",
    "",
    "",
    "Do not copy details from Google Maps or other proprietary maps; their licenses do not allow it.",
  ].join("\n");
  correctionLink.href = `${NEW_ISSUE_URL}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}

const correctionLink = byId("correction", HTMLAnchorElement);
const needle = byId("needle", HTMLElement);
let views: Record<string, View> = {};
// The frame search places and flow lines are written in.
let indexFrame: Frame | null = null;
let areaName = "bbmp";
let currentView = NORTH_UP_VIEW;
let pendingTarget: Target | null = null;
let still: HTMLCanvasElement | null = null;
let water: ReturnType<typeof startWater> | null = null;
let rivers: ReturnType<typeof startRivers> | null = null;
let metro: ReturnType<typeof startMetro> | null = null;
let layerKey: Layers | null = null;
let bloom: ReturnType<typeof startBloom> | null = null;
let night: ReturnType<typeof startNight> | null = null;
let marker: HTMLElement | null = null;
let labels: ReturnType<typeof startLabels> | null = null;

function showMarker(x: number, y: number): void {
  if (marker) {
    viewer.removeOverlay(marker);
  }
  marker = document.createElement("div");
  marker.className = "marker";
  viewer.addOverlay({
    element: marker,
    location: viewer.viewport.imageToViewportCoordinates(x, y),
    placement: OpenSeadragon.Placement.CENTER,
  });
}

function toCurrentView(x: number, y: number): [number, number] {
  return convertPoint(x, y, indexFrame ?? viewData(currentView), viewData(currentView));
}

function viewData(name: string): View {
  const view = views[name];
  if (!view) {
    throw new Error(`Unknown view ${name}`);
  }
  return view;
}

function placeLabelsInView(): void {
  if (Object.keys(views).length) {
    places = basePlaces.map((place) => {
      const [x, y] = toCurrentView(place.x, place.y);
      return { ...place, x, y };
    });
  }
}

function openView(target: Target): void {
  currentView = target.view;
  pendingTarget = target;
  needle.style.transform = `rotate(${String(northAngle(viewData(target.view)))}deg)`;
  placeLabelsInView();
  // Opening clears the overlays, so the marker is dropped.
  marker = null;
  viewer.open(`${TILE_BASE}pyramid/${viewData(target.view).pyramid}/${areaName}.dzi`);
}

// Keeps the last frame on screen until the next view's tiles arrive.
function holdPicture(): void {
  const source = (viewer.drawer as unknown as { canvas: HTMLCanvasElement }).canvas;
  still?.remove();
  const picture = document.createElement("canvas");
  picture.className = "still";
  picture.width = source.width;
  picture.height = source.height;
  picture.getContext("2d")?.drawImage(source, 0, 0);
  source.after(picture);
  still = picture;
  window.setTimeout(() => {
    picture.remove();
  }, STILL_MAX_MS);
}

function rotateView(step: number): void {
  const order = viewOrder(views);
  const count = order.length;
  turnTo(order[(order.indexOf(currentView) + step + count) % count]);
}

function turnTo(next: string | undefined): void {
  if (next && next !== currentView && viewer.world.getItemCount()) {
    const center = viewCenter();
    const [lon, lat] = toLonLat(viewData(currentView), center.x, center.y);
    holdPicture();
    openView({ lon, lat, zoom: imageZoom(), view: next });
  }
}

viewer.addHandler("open", () => {
  if (pendingTarget) {
    goToSpot(pendingTarget.lon, pendingTarget.lat, pendingTarget.zoom, true);
    pendingTarget = null;
  }
  viewer.world.getItemAt(0).addOnceHandler("fully-loaded-change", () => {
    still?.remove();
  });
  updateTilt();
  updateSmoothing();
  labels ??= startLabels(viewer);
  labels.show(places);
  updateCorrectionLink();
  writeHash();
  if (water) {
    water.refresh();
    rivers?.refresh();
    metro?.refresh();
  } else {
    water = startWater(viewer, byId("animation", HTMLInputElement), toCurrentView);
    rivers = startRivers(viewer, toCurrentView);
    metro = startMetro(viewer, byId("metro", HTMLInputElement), toCurrentView);
    viewer.addHandler("animation-finish", writeHash);
    viewer.addHandler("animation-finish", updateCorrectionLink);
    viewer.addHandler("animation", updateTilt);
    viewer.addHandler("animation", updateSmoothing);
    night = startNight(viewer, byId("light", HTMLSelectElement));
    bloom = layerKey && startBloom(viewer, byId("bloom", HTMLSelectElement), layerKey);
  }
  night?.refresh(viewData(currentView), areaName);
  bloom?.refresh(viewData(currentView), areaName);
});

window.addEventListener("hashchange", () => {
  const target = readHash();
  if (!target) {
    return;
  }
  if (target.view === currentView) {
    goToSpot(target.lon, target.lat, target.zoom, false);
  } else {
    openView(target);
  }
});

function imageZoom(): number {
  return viewer.viewport.viewportToImageZoom(viewer.viewport.getZoom());
}

// Pixel art shrunk with hard edges turns to speckle, so it is smoothed while the map is
// shrunk, and kept hard-edged once each map pixel covers a screen pixel or more. A zoom
// that lands on a pyramid level draws its tiles one to one, so it stays hard-edged too.
let smoothing = false;

function updateSmoothing(): void {
  const scale = Math.log2(imageZoom() * devicePixelRatio);
  const smooth = scale < 0 && Math.abs(scale - Math.round(scale)) > 0.02;
  if (smooth !== smoothing) {
    smoothing = smooth;
    viewer.drawer.setImageSmoothingEnabled(smooth);
  }
}

function updateTilt(): void {
  const amount = (TILT_NONE_ZOOM - imageZoom()) / (TILT_NONE_ZOOM - TILT_FULL_ZOOM);
  document.documentElement.style.setProperty("--tilt", String(Math.min(1, Math.max(0, amount))));
}

function bindZoom(id: string, action: () => void): void {
  byId(id, HTMLButtonElement).addEventListener("click", action);
}

function zoomBy(factor: number): void {
  viewer.viewport.zoomBy(factor).applyConstraints();
}

// Home is the opening view, near enough to read the city, in whichever way it faces now.
function goHome(): void {
  goToSpot(OPENING_VIEW.lon, OPENING_VIEW.lat, OPENING_VIEW.zoom, false);
}

function panBy(dx: number, dy: number): void {
  const bounds = viewer.viewport.getBounds();
  viewer.viewport
    .panBy(new OpenSeadragon.Point(dx * bounds.width * PAN_STEP, dy * bounds.height * PAN_STEP))
    .applyConstraints();
}

bindZoom("zoom-in", () => {
  zoomBy(ZOOM_STEP);
});
bindZoom("zoom-out", () => {
  zoomBy(1 / ZOOM_STEP);
});
bindZoom("home", goHome);
bindZoom("compass", () => {
  turnTo(NORTH_UP_VIEW);
});
byId("rotate", HTMLButtonElement).addEventListener("click", (event) => {
  rotateView(event.altKey ? -1 : 1);
});

const settingsButton = byId("settings", HTMLButtonElement);
const settingsPanel = byId("settings-panel", HTMLElement);

function showSettings(open: boolean): void {
  settingsPanel.hidden = !open;
  settingsButton.setAttribute("aria-expanded", String(open));
}

settingsButton.addEventListener("click", () => {
  showSettings(settingsPanel.hidden);
});
// Capture, because the map stops pointer events from bubbling.
document.addEventListener(
  "pointerdown",
  (event) => {
    const target = event.target;
    if (
      target instanceof Node &&
      !settingsPanel.contains(target) &&
      !settingsButton.contains(target)
    ) {
      showSettings(false);
    }
  },
  true,
);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    showSettings(false);
  }
});

const input = byId("search", HTMLInputElement);
const results = byId("results", HTMLUListElement);
let basePlaces: Place[] = [];
let places: Place[] = [];

fetch(MANIFEST, { cache: "no-cache" })
  .then((response) => response.json())
  .then((manifest: Frame & { area?: string; layers?: Layers; views: Record<string, View> }) => {
    views = manifest.views;
    layerKey = manifest.layers ?? null;
    const { matrix, x_offset, y_offset } = manifest;
    indexFrame = { matrix, x_offset, y_offset };
    areaName = manifest.area ?? areaName;
    openView(readHash() ?? OPENING_VIEW);
  })
  .catch((error: unknown) => {
    console.error("Tile manifest failed to load", error);
  });

fetch(SEARCH_INDEX, { cache: "no-cache" })
  .then((response) => response.json())
  .then((entries: Place[]) => {
    basePlaces = entries;
    places = entries;
    placeLabelsInView();
    labels?.show(places);
    if (viewer.world.getItemCount()) {
      updateCorrectionLink();
    }
  })
  .catch((error: unknown) => {
    console.error("Search index failed to load", error);
    input.placeholder = "Search is unavailable";
    input.disabled = true;
  });

byId("shortcuts", HTMLDivElement).replaceChildren(
  ...SHORTCUTS.map(([label, lon, lat, zoom]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", () => {
      // Placed on click, so it lands right in whichever view is open.
      const [x, y] = toImage(viewData(currentView), lon, lat);
      goTo(x, y, zoom, false);
      showMarker(x, y);
    });
    return button;
  }),
);
startPanel();

function renderResults(matches: Place[]): void {
  results.replaceChildren(
    ...matches.map((place) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.append(place.name);
      if (place.kind) {
        const kind = document.createElement("small");
        kind.textContent = place.kind.replaceAll("_", " ");
        button.append(kind);
      }
      button.addEventListener("click", () => {
        goTo(place.x, place.y, FLY_TO_IMAGE_ZOOM, false);
        showMarker(place.x, place.y);
        results.hidden = true;
      });
      item.append(button);
      return item;
    }),
  );
  results.hidden = matches.length === 0;
}

input.addEventListener("input", () => {
  const query = input.value.trim().toLowerCase();
  if (!query) {
    results.hidden = true;
    return;
  }
  renderResults(
    places.filter((place) => place.name.toLowerCase().includes(query)).slice(0, MAX_RESULTS),
  );
});

const helpDialog = byId("help-dialog", HTMLDialogElement);

function toggleHelp(): void {
  if (helpDialog.open) {
    helpDialog.close();
  } else {
    showSettings(false);
    helpDialog.showModal();
  }
}

byId("help", HTMLButtonElement).addEventListener("click", toggleHelp);
// A click on the backdrop lands on the dialog itself, not on its body.
helpDialog.addEventListener("click", (event) => {
  if (event.target === helpDialog) {
    helpDialog.close();
  }
});

// The map's own keys would tilt or mirror the pre-drawn view, so every key is handled here.
viewer.addHandler("canvas-key", (event) => {
  event.preventDefaultAction = true;
});

function keyAction(event: KeyboardEvent): (() => void) | null {
  const pan = PAN_KEYS[event.key] ?? PAN_KEYS[event.code];
  const target = event.target;
  // Arrow keys stay with the search results and other controls that use them.
  const onMap =
    target === document.body || (target instanceof Node && viewer.element.contains(target));
  if (pan && (onMap || event.code.startsWith("Key"))) {
    return () => {
      panBy(...pan);
    };
  }
  const byKey: Record<string, () => void> = {
    "?": toggleHelp,
    "/": () => {
      input.focus();
    },
    "+": () => {
      zoomBy(ZOOM_STEP);
    },
    "=": () => {
      zoomBy(ZOOM_STEP);
    },
    "-": () => {
      zoomBy(1 / ZOOM_STEP);
    },
    "0": goHome,
  };
  const byCode: Record<string, () => void> = {
    KeyR: () => {
      rotateView(event.shiftKey || event.altKey ? -1 : 1);
    },
    KeyN: () => {
      turnTo(NORTH_UP_VIEW);
    },
    KeyH: goHome,
    KeyI: () => {
      byId("info-collapse", HTMLButtonElement).click();
    },
  };
  return byKey[event.key] ?? byCode[event.code] ?? null;
}

// Captured, so the map's own key handling never sees a key handled here.
document.addEventListener(
  "keydown",
  (event) => {
    const target = event.target;
    const typing =
      (target instanceof HTMLInputElement && target.type !== "checkbox") ||
      target instanceof HTMLTextAreaElement;
    if (typing || event.ctrlKey || event.metaKey || (helpDialog.open && event.key !== "?")) {
      return;
    }
    const action = keyAction(event);
    if (action) {
      event.preventDefault();
      event.stopPropagation();
      action();
    }
  },
  true,
);
