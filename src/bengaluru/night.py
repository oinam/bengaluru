"""The night's work: heavy jobs run while Brajeshwar sleeps and stop before he wakes."""

import datetime as dt
import time
from pathlib import Path

from bengaluru.areas import Area
from bengaluru.fetch import fetch, raw_dir
from bengaluru.prepare import prepare, stats_path
from bengaluru.tile import build

NIGHT_WINDOW = "23:00-04:00"


def closing_time(window: str, now: dt.datetime) -> dt.datetime | None:
    """Return when the window that holds `now` closes, or None if `now` is outside it."""
    start, end = (dt.time.fromisoformat(part) for part in window.split("-"))
    closes = dt.datetime.combine(now.date(), end)
    if start <= end:
        return closes if start <= now.time() < end else None
    if now.time() >= start:
        return closes + dt.timedelta(days=1)
    return closes if now.time() < end else None


def night(area: Area, window: str = NIGHT_WINDOW) -> None:
    """Fetch, prepare, and build the area, each only if it is not done, inside the window.

    Started outside the window, as when the Mac wakes late, it does nothing. No step
    starts once the window has closed, and the build stops at its next frame.
    """
    now = dt.datetime.now()
    # Fixed before anything reads the drive, which can hold a first read for hours.
    closes = closing_time(window, now)
    print(f"night: {now:%Y-%m-%d %H:%M}, {area.name}, window {window}", flush=True)
    if not (Path("out").exists() and Path("data/raw").exists()):
        raise SystemExit("night: the external drive is not plugged in; nothing started")
    if closes is None:
        print("night: outside the window; nothing started")
        return
    deadline = closes.timestamp()
    steps = (
        ("fetch", raw_dir(area) / "SOURCES.txt", fetch),
        ("prepare", stats_path(area), prepare),
    )
    for name, product, run in steps:
        if product.exists():
            continue
        if time.time() >= deadline:
            print(f"night: the window closed before {name}; the next night carries on")
            return
        print(f"night: {name}", flush=True)
        run(area)
    if build(area, deadline=deadline):
        print(f"night: {area.name} is built, at {dt.datetime.now():%H:%M}")
    else:
        print(f"night: stopped when the window closed at {closes:%H:%M}; the next night carries on")
