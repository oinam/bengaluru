"""Command line entry point: `bengaluru <stage> --area <name>`."""

import argparse
from importlib import import_module

from bengaluru.areas import get_area

# Each stage and the function that runs it, imported only when asked for, so a stage
# loads no more than it needs.
STAGES = {
    "fetch": "fetch:fetch",
    "plan": "plan:plan",
    "prepare": "prepare:prepare",
    "render": "render:render",
    "swatches": "render:swatches",
    "detail": "detail:detail",
    "frames": "detail:frames",
    "tile": "tile:tile",
    "build": "tile:build",
    "metro": "tile:refresh_metro",
}


def stage(name: str):
    module, function = STAGES[name].split(":")
    return getattr(import_module(f"bengaluru.{module}"), function)


def main() -> None:
    parser = argparse.ArgumentParser(prog="bengaluru")
    commands = parser.add_subparsers(dest="stage", required=True)
    for name in STAGES:
        commands.add_parser(name).add_argument("--area", required=True)
    # The night's work takes areas in the order to build them, and a window; the defaults
    # are the ones in docs/DECISIONS.md.
    night = commands.add_parser("night")
    night.add_argument("--area", action="append", default=[])
    night.add_argument("--window", metavar="HH:MM-HH:MM")
    args = parser.parse_args()
    if args.stage == "night":
        work = import_module("bengaluru.night")
        areas = [get_area(name) for name in args.area or work.NIGHT_AREAS]
        work.night(areas, args.window or work.NIGHT_WINDOW)
    else:
        stage(args.stage)(get_area(args.area))
