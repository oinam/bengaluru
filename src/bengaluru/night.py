"""The night's work: heavy jobs run while Brajeshwar sleeps and stop before he wakes."""

import datetime as dt
import subprocess
import time
from pathlib import Path

from bengaluru.areas import Area
from bengaluru.fetch import fetch, raw_dir
from bengaluru.prepare import prepare, stats_path
from bengaluru.tile import build

NIGHT_WINDOW = "23:00-04:00"
PMSET = "/usr/bin/pmset"
# Installed from launchd/bengaluru-wake.sudoers; it allows scheduling a wake and nothing else.
WAKE_RULE = Path("/etc/sudoers.d/bengaluru-wake")


def closing_time(window: str, now: dt.datetime) -> dt.datetime | None:
    """Return when the window that holds `now` closes, or None if `now` is outside it."""
    start, end = (dt.time.fromisoformat(part) for part in window.split("-"))
    closes = dt.datetime.combine(now.date(), end)
    if start <= end:
        return closes if start <= now.time() < end else None
    if now.time() >= start:
        return closes + dt.timedelta(days=1)
    return closes if now.time() < end else None


def next_opening(window: str, now: dt.datetime) -> dt.datetime:
    """Return the next time the window opens after `now`."""
    opens = dt.datetime.combine(now.date(), dt.time.fromisoformat(window.split("-", maxsplit=1)[0]))
    return opens if now < opens else opens + dt.timedelta(days=1)


def schedule_wake(opens: dt.datetime) -> None:
    """Ask the Mac to wake as the window opens; launchd then starts the work it missed.

    Every run sets the next one, and launchd runs this whenever the Mac wakes after a
    missed night, so one skipped night does not end the chain. Without the permission it
    says so, and the Mac has to be awake at the opening by other means.
    """
    if not WAKE_RULE.exists():
        print(f"night: no wake set for {opens:%H:%M}; the permission is not installed")
        return
    listed = subprocess.run([PMSET, "-g", "sched"], capture_output=True, text=True, check=False)
    if f"wake at {opens:%m/%d/%Y %H:%M:%S}" in listed.stdout:
        return
    asked = subprocess.run(
        ["sudo", "-n", PMSET, "schedule", "wake", f"{opens:%m/%d/%y %H:%M:%S}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if asked.returncode == 0:
        print(f"night: the Mac will wake at {opens:%Y-%m-%d %H:%M}")
    else:
        print(f"night: could not set a wake for {opens:%H:%M}: {asked.stderr.strip()}")


def night(area: Area, window: str = NIGHT_WINDOW) -> None:
    """Fetch, prepare, and build the area, each only if it is not done, inside the window.

    Started outside the window, as when the Mac wakes late, it does nothing. No step
    starts once the window has closed, and the build stops at its next frame.
    """
    now = dt.datetime.now()
    # Fixed before anything reads the drive, which can hold a first read for hours.
    closes = closing_time(window, now)
    print(f"night: {now:%Y-%m-%d %H:%M}, {area.name}, window {window}", flush=True)
    # A window given by hand is a test; only the real one wakes the Mac.
    if window == NIGHT_WINDOW:
        schedule_wake(next_opening(window, now))
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
