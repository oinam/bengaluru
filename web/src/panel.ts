// The "Go to" panel, which opens at the bottom left, collapses to its bar, and can be
// dragged elsewhere.

// Where a dragged panel sits: its left and bottom edges, in pixels from the screen's.
interface Spot {
  left: number;
  bottom: number;
}

const COLLAPSED_KEY = "info-collapsed";
const POSITION_KEY = "info-position";
// A press that moves less than this is a click, not a drag.
const DRAG_START_PX = 4;
// The gap a dragged panel keeps from the edge of the screen.
const EDGE_PX = 8;

function element<T extends HTMLElement>(id: string, type: new () => T): T {
  const found = document.getElementById(id);
  if (!(found instanceof type)) {
    throw new Error(`Missing #${id}`);
  }
  return found;
}

function remembered(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function remember(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The panel still works; it opens in its default state next time.
  }
}

function forget(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing was kept, so there is nothing to forget.
  }
}

function startCollapse(panel: HTMLElement): void {
  const body = element("shortcuts", HTMLDivElement);
  const collapse = element("info-collapse", HTMLButtonElement);
  const setCollapsed = (collapsed: boolean) => {
    body.hidden = collapsed;
    panel.classList.toggle("collapsed", collapsed);
    const label = collapsed ? "Expand the panel" : "Collapse the panel";
    collapse.setAttribute("aria-expanded", String(!collapsed));
    collapse.setAttribute("aria-label", label);
    collapse.title = label;
    remember(COLLAPSED_KEY, String(collapsed));
  };
  collapse.addEventListener("click", () => {
    setCollapsed(!body.hidden);
  });
  setCollapsed(remembered(COLLAPSED_KEY) === "true");
}

// The panel moves by its bar, and a double click on the bar sends it back to its corner.
// It is placed by its left and bottom edges, so it still folds downward wherever it
// sits, and it is kept on screen.
function startDrag(panel: HTMLElement): void {
  const bar = element("info-bar", HTMLDivElement);
  let spot: Spot | null = null;

  const place = (left: number, bottom: number) => {
    panel.classList.add("moved");
    const limit = (value: number, most: number) =>
      Math.round(Math.max(EDGE_PX, Math.min(value, most - EDGE_PX)));
    spot = {
      left: limit(left, innerWidth - panel.offsetWidth),
      bottom: limit(bottom, innerHeight - panel.offsetHeight),
    };
    panel.style.left = `${String(spot.left)}px`;
    panel.style.bottom = `${String(spot.bottom)}px`;
  };
  const replace = () => {
    if (spot) {
      place(spot.left, spot.bottom);
    }
  };

  bar.addEventListener("pointerdown", (down) => {
    if (down.button !== 0) {
      return;
    }
    const box = panel.getBoundingClientRect();
    const drag = new AbortController();
    let dragging = false;
    // On the window, since a quick pointer leaves the bar before the drag has begun.
    addEventListener(
      "pointermove",
      (move) => {
        const dx = move.clientX - down.clientX;
        const dy = move.clientY - down.clientY;
        if (!dragging && Math.hypot(dx, dy) < DRAG_START_PX) {
          return;
        }
        if (!dragging) {
          dragging = true;
          bar.setPointerCapture(down.pointerId);
          panel.classList.add("dragging");
        }
        place(box.left + dx, innerHeight - box.bottom - dy);
      },
      { signal: drag.signal },
    );
    const end = () => {
      drag.abort();
      panel.classList.remove("dragging");
      if (!dragging) {
        return;
      }
      remember(POSITION_KEY, JSON.stringify(spot));
      // The release would otherwise count as a click on the button the drag began on.
      const swallow = new AbortController();
      addEventListener(
        "click",
        (click) => {
          click.stopPropagation();
          click.preventDefault();
        },
        { capture: true, once: true, signal: swallow.signal },
      );
      setTimeout(() => {
        swallow.abort();
      });
    };
    addEventListener("pointerup", end, { signal: drag.signal });
    addEventListener("pointercancel", end, { signal: drag.signal });
  });
  bar.addEventListener("dblclick", (event) => {
    if (event.target instanceof Element && event.target.closest("button")) {
      return;
    }
    spot = null;
    panel.classList.remove("moved");
    panel.style.left = "";
    panel.style.bottom = "";
    forget(POSITION_KEY);
  });

  try {
    const saved = JSON.parse(remembered(POSITION_KEY) ?? "null") as Spot | null;
    if (saved && Number.isFinite(saved.left) && Number.isFinite(saved.bottom)) {
      place(saved.left, saved.bottom);
    }
  } catch {
    // an unreadable position: the panel opens in its corner
  }
  // The window and collapsing both change how much room the panel has.
  addEventListener("resize", replace);
  new ResizeObserver(replace).observe(panel);
}

export function startPanel(): void {
  const panel = element("info", HTMLElement);
  startCollapse(panel);
  startDrag(panel);
}
