"""Cut the picture that social media shows beside a link to the site, from the finished tiles.

    uv run python tools/share_image.py [area] [lon] [lat] [halvings] [output]

The picture is the site's opening view, north up and by day, centered on the place given,
which is Vidhana Soudha unless told. Each halving shows twice as far at half the detail;
one, unless told, takes in the High Court and Cubbon Park. It reads only the rendered
tiles, so run `bengaluru build` first. Writes web/public/share.jpg, which the page's head
names.
"""

import json
import sys
from pathlib import Path

from PIL import Image
from pyproj import Transformer

from bengaluru.prepare import METRIC_CRS

AREA = sys.argv[1] if len(sys.argv) > 1 else "bbmp"
LON = float(sys.argv[2]) if len(sys.argv) > 2 else 77.5907
LAT = float(sys.argv[3]) if len(sys.argv) > 3 else 12.9797
HALVINGS = int(sys.argv[4]) if len(sys.argv) > 4 else 1
OUTPUT = Path(sys.argv[5] if len(sys.argv) > 5 else "web/public/share.jpg")
VIEW = "315"
TILE = 512
# The size Facebook, LinkedIn, X, WhatsApp, and Slack all show without cropping.
WIDTH, HEIGHT = 1200, 630
BACKGROUND = "#1f2a2e"
QUALITY = 88


def cut(files: Path, level: int, left: int, top: int) -> Image.Image:
    """Return the picture's rectangle of one level of a pyramid, from the tiles under it."""
    picture = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    for column in range(left // TILE, (left + WIDTH - 1) // TILE + 1):
        for row in range(top // TILE, (top + HEIGHT - 1) // TILE + 1):
            path = files / str(level) / f"{column}_{row}.webp"
            if column >= 0 and row >= 0 and path.exists():
                with Image.open(path) as tile:
                    picture.paste(tile.convert("RGB"), (column * TILE - left, row * TILE - top))
    return picture


if __name__ == "__main__":
    tiles = Path("out") / AREA / "tiles"
    view = json.loads((tiles / "views.json").read_text())[VIEW]
    files = tiles / "pyramid" / view["pyramid"] / f"{AREA}_files"
    x, y = Transformer.from_crs(4326, METRIC_CRS, always_xy=True).transform(LON, LAT)
    a, b, d, e = view["matrix"]
    scale = 2**HALVINGS
    center_x = (a * x + b * y + view["x_offset"]) / scale
    center_y = (d * x + e * y + view["y_offset"]) / scale
    level = max(int(path.name) for path in files.iterdir() if path.name.isdigit()) - HALVINGS
    picture = cut(files, level, round(center_x - WIDTH / 2), round(center_y - HEIGHT / 2))
    picture.save(OUTPUT, quality=QUALITY, optimize=True, progressive=True)
    print(f"{OUTPUT}: {OUTPUT.stat().st_size // 1024} KB")
