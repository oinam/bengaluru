"""Lay the site's four views of an area side by side, from the finished tile pyramids.

Each view is shown whole, at a quarter of full size, labeled with the compass point at the
top of the picture. It reads only the rendered tiles, so run `bengaluru build` first.
Writes out/<area>/<stamp>_four-views.png.
"""

import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AREA = sys.argv[1] if len(sys.argv) > 1 else "vidhana-soudha"
TILE = 512
# Two levels below full size is a quarter scale.
LEVELS_DOWN = 2
GAP = 24
TITLE = 44
BACKGROUND = "#1f2a2e"


def compass(matrix: list[float]) -> str:
    """Return the compass point at the top of a view, from its ground-to-screen matrix."""
    _, _, d, e = matrix
    if abs(e) >= abs(d):
        return "north" if e < 0 else "south"
    return "west" if d > 0 else "east"


def whole_view(files: Path) -> Image.Image:
    level = max(int(path.name) for path in files.iterdir() if path.name.isdigit()) - LEVELS_DOWN
    tiles = {
        tuple(int(part) for part in path.stem.split("_")): path
        for path in (files / str(level)).glob("*.webp")
    }
    columns = max(column for column, _ in tiles) + 1
    rows = max(row for _, row in tiles) + 1
    picture = Image.new("RGB", (columns * TILE, rows * TILE), BACKGROUND)
    width = height = 0
    for (column, row), path in tiles.items():
        with Image.open(path) as tile:
            picture.paste(tile.convert("RGB"), (column * TILE, row * TILE))
            width = max(width, column * TILE + tile.width)
            height = max(height, row * TILE + tile.height)
    return picture.crop((0, 0, width, height))


def main() -> None:
    tiles = Path("out", AREA, "tiles")
    views = json.loads((tiles / "views.json").read_text())
    pictures = [
        (
            f"{compass(view['matrix'])} up",
            whole_view(tiles / "pyramid" / view["pyramid"] / f"{AREA}_files"),
        )
        for view in views.values()
    ]
    width = max(picture.width for _, picture in pictures)
    height = max(picture.height for _, picture in pictures)
    sheet = Image.new(
        "RGB", (GAP + 2 * (width + GAP), GAP + 2 * (TITLE + height + GAP)), BACKGROUND
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=26)
    for index, (label, picture) in enumerate(pictures):
        left = GAP + (index % 2) * (width + GAP)
        top = GAP + (index // 2) * (TITLE + height + GAP)
        draw.text((left, top + 4), label, fill="#e6dccb", font=font)
        sheet.paste(picture, (left, top + TITLE))
    output = Path("out", AREA, f"{dt.datetime.now():%Y%m%d-%H%M%S}_four-views.png")
    sheet.save(output, optimize=True)
    print(f"{output}: {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    main()
