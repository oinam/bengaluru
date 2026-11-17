"""Command line entry point: `bengaluru <stage> --area <name>`."""

import argparse
from collections.abc import Callable

from bengaluru.areas import Area, get_area


def run_fetch(area: Area) -> None:
    from bengaluru.fetch import fetch

    fetch(area)


def run_plan(area: Area) -> None:
    from bengaluru.plan import plan

    plan(area)


def run_prepare(area: Area) -> None:
    from bengaluru.prepare import prepare

    prepare(area)


def run_render(area: Area) -> None:
    from bengaluru.render import render

    render(area)


def run_swatches(area: Area) -> None:
    from bengaluru.render import swatches

    swatches(area)


def run_detail(area: Area) -> None:
    from bengaluru.detail import detail

    detail(area)


def run_frames(area: Area) -> None:
    from bengaluru.detail import frames

    frames(area)


def run_build(area: Area) -> None:
    from bengaluru.tile import build

    build(area)


def run_night(names: list[str], window: str | None) -> None:
    from bengaluru.night import NIGHT_AREAS, NIGHT_WINDOW, night

    night([get_area(name) for name in names or NIGHT_AREAS], window or NIGHT_WINDOW)


def run_tile(area: Area) -> None:
    from bengaluru.tile import tile

    tile(area)


STAGES: dict[str, Callable[[Area], None]] = {
    "fetch": run_fetch,
    "plan": run_plan,
    "prepare": run_prepare,
    "render": run_render,
    "swatches": run_swatches,
    "detail": run_detail,
    "frames": run_frames,
    "tile": run_tile,
    "build": run_build,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="bengaluru")
    commands = parser.add_subparsers(dest="stage", required=True)
    for stage in STAGES:
        commands.add_parser(stage).add_argument("--area", required=True)
    # The night's work takes areas in the order to build them, and a window; the defaults
    # are the ones in docs/DECISIONS.md.
    night = commands.add_parser("night")
    night.add_argument("--area", action="append", default=[])
    night.add_argument("--window", metavar="HH:MM-HH:MM")
    args = parser.parse_args()
    if args.stage == "night":
        run_night(args.area, args.window)
    else:
        STAGES[args.stage](get_area(args.area))
