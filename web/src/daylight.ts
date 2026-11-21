import OpenSeadragon from "openseadragon";

import { TILE_BASE } from "./tiles";
import type { View } from "./views";

type Choice = "" | "day" | "night";

// Vidhana Soudha, in degrees north and east.
const CITY_LAT = 12.9797;
const CITY_LON = 77.5907;
// The map keeps the city's time, wherever it is read.
const CITY_TIME = "Asia/Kolkata";
// The sun this many degrees above the horizon is full day, and this many below is night;
// dusk and dawn are the way between.
const DAY_ABOVE_DEG = 3;
const NIGHT_BELOW_DEG = -6;
const CLOCK_MS = 60_000;
// Day or night chosen by hand; nothing kept means the city's clock decides.
const LIGHT_KEY = "light";
const DEGREES = Math.PI / 180;

// How high the sun stands over the city, in degrees; below the horizon it is negative.
// The Astronomical Almanac's short formulas, good to a small part of a degree.
export function sunElevation(time: Date): number {
  const days = time.getTime() / 86_400_000 - 10_957.5;
  const meanLongitude = 280.46 + 0.9856474 * days;
  const anomaly = (357.528 + 0.9856003 * days) * DEGREES;
  const longitude =
    (meanLongitude + 1.915 * Math.sin(anomaly) + 0.02 * Math.sin(2 * anomaly)) * DEGREES;
  const tilt = (23.439 - 0.0000004 * days) * DEGREES;
  const declination = Math.asin(Math.sin(tilt) * Math.sin(longitude));
  const ascension = Math.atan2(Math.cos(tilt) * Math.sin(longitude), Math.cos(longitude));
  const siderealHours = 18.697374558 + 24.06570982441908 * days;
  const hourAngle = (siderealHours * 15 + CITY_LON) * DEGREES - ascension;
  const latitude = CITY_LAT * DEGREES;
  const height =
    Math.sin(latitude) * Math.sin(declination) +
    Math.cos(latitude) * Math.cos(declination) * Math.cos(hourAngle);
  return Math.asin(height) / DEGREES;
}

// How dark it is, from 0 by day to 1 at night, easing through dusk and dawn.
export function darkness(elevation: number): number {
  const part = (DAY_ABOVE_DEG - elevation) / (DAY_ABOVE_DEG - NIGHT_BELOW_DEG);
  const clamped = Math.min(1, Math.max(0, part));
  return clamped * clamped * (3 - 2 * clamped);
}

function chosen(): Choice {
  try {
    const kept = localStorage.getItem(LIGHT_KEY);
    return kept === "day" || kept === "night" ? kept : "";
  } catch {
    return "";
  }
}

function saveChoice(choice: Choice): void {
  try {
    if (choice) {
      localStorage.setItem(LIGHT_KEY, choice);
    } else {
      localStorage.removeItem(LIGHT_KEY);
    }
  } catch {
    // The choice lasts for this visit only.
  }
}

function cityHour(time: Date): number {
  return Number(
    new Intl.DateTimeFormat("en-US", { hour: "numeric", hourCycle: "h23", timeZone: CITY_TIME })
      .format(time)
      .replace(/\D/g, ""),
  );
}

function nameOfHour(dark: number, time: Date): string {
  if (dark < 0.05) {
    return "day";
  }
  if (dark > 0.95) {
    return "night";
  }
  return cityHour(time) < 12 ? "dawn" : "dusk";
}

export function startNight(
  viewer: OpenSeadragon.Viewer,
  select: HTMLSelectElement,
): { refresh: (view: View, area: string) => void } {
  const source = (viewer.drawer as unknown as { canvas: HTMLCanvasElement }).canvas;
  const shade = document.createElement("div");
  shade.className = "night";
  const glow = document.createElement("div");
  glow.className = "lights";
  glow.setAttribute("aria-hidden", "true");
  // Over the map and its water, and under the metro, the names, and the marker.
  const water = source.parentElement?.querySelector(".water");
  source.after(...(water ? [water] : []), shade, glow);
  // The shade multiplies what lies under it, and past the map's edge that is nothing; the
  // page's color there gives it something to darken.
  source.style.background = "var(--bg)";

  const clock = select.options[0];
  let lightsUrl: string | null = null;
  let lights: OpenSeadragon.Viewer | null = null;
  let opened: string | null = null;
  let dark = 0;
  let smooth = true;

  function follow(): void {
    if (!lights?.world.getItemCount()) {
      return;
    }
    lights.viewport.fitBounds(viewer.viewport.getBounds(true), true);
    const zoom = viewer.viewport.viewportToImageZoom(viewer.viewport.getZoom(true));
    const shrunk = zoom * devicePixelRatio < 1;
    if (shrunk !== smooth) {
      smooth = shrunk;
      lights.drawer.setImageSmoothingEnabled(shrunk);
    }
  }

  // The lights are a second map, drawn over the shade so the night does not dim them. How
  // they look from afar is settled where they are tiled, not here.
  function light(): void {
    if (!lightsUrl || dark === 0) {
      lights?.destroy();
      lights = null;
      opened = null;
      glow.replaceChildren();
      return;
    }
    if (!lights) {
      smooth = true;
      lights = OpenSeadragon({
        element: glow,
        prefixUrl: "",
        crossOriginPolicy: "Anonymous",
        drawer: "canvas",
        showNavigationControl: false,
        mouseNavEnabled: false,
        tabIndex: -1,
        animationTime: 0,
        visibilityRatio: 0,
        minZoomImageRatio: 0,
        maxZoomPixelRatio: Infinity,
        // The map's own tiles come first.
        imageLoaderLimit: 2,
      });
      lights.addHandler("open", follow);
    }
    if (opened !== lightsUrl) {
      opened = lightsUrl;
      lights.open(lightsUrl);
    }
    follow();
  }

  function update(): void {
    const now = new Date();
    const byClock = darkness(sunElevation(now));
    const choice = chosen();
    // A map tiled without its lights stays in daylight; a night with nothing lit is only dark.
    dark = !lightsUrl || choice === "day" ? 0 : choice === "night" ? 1 : byClock;
    shade.style.opacity = String(dark);
    glow.style.opacity = String(dark);
    if (clock) {
      clock.textContent = `By Bengaluru's clock: ${nameOfHour(byClock, now)} now`;
    }
    light();
  }

  // After the map opens or turns, which changes the lights' picture with the map's.
  function refresh(view: View, area: string): void {
    lightsUrl = view.lights ? `${TILE_BASE}pyramid/${view.lights}/${area}.dzi` : null;
    select.closest("label")?.toggleAttribute("hidden", !lightsUrl);
    update();
  }

  select.value = chosen();
  select.addEventListener("change", () => {
    const value = select.value;
    saveChoice(value === "day" || value === "night" ? value : "");
    update();
  });
  viewer.addHandler("update-viewport", follow);
  viewer.addHandler("resize", follow);
  window.setInterval(update, CLOCK_MS);

  return { refresh };
}
