"""Render one place in several candidate looks, side by side, for Brajeshwar to choose from.

    uv run python tools/look_options.py central 77.5790 12.9865

Nothing here changes the map: each option swaps a piece of the renderer for this run only.
The area must have been built, so its trees are placed. Writes
out/<area>/<stamp>_look-options.png.
"""

import datetime as dt
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer

from bengaluru import detail
from bengaluru.areas import get_area
from bengaluru.prepare import METRIC_CRS
from bengaluru.render import centered_viewport

PANEL_PX = 1536
CAPTION_PX = 44
GRAY_GROUND = "#bdb9ad"


def as_built(scene):
    return scene


def gray_ground(scene):
    detail.PALETTE = {**detail.PALETTE, "built": GRAY_GROUND}
    return scene


# The terraces and lawns first shown here were taken on 2026-11-18 and are in the renderer;
# the gray ground was not.
OPTIONS = (
    ("A. As built", as_built),
    (f"B. The ground between buildings gray ({GRAY_GROUND})", gray_ground),
)

if __name__ == "__main__":
    area = get_area(sys.argv[1])
    lon, lat = float(sys.argv[2]), float(sys.argv[3])
    x, y = Transformer.from_crs(4326, METRIC_CRS, always_xy=True).transform(lon, lat)
    detail.use_view("315")
    view = centered_viewport(detail.PROJECTION, x, y, PANEL_PX, PANEL_PX)
    rows = (len(OPTIONS) + 1) // 2
    sheet = Image.new("RGB", (2 * PANEL_PX, rows * (PANEL_PX + CAPTION_PX)), "#1f2a2e")
    draw = ImageDraw.Draw(sheet)
    for index, (caption, apply) in enumerate(OPTIONS):
        scene = apply(detail.load_scene(area, use_cached_trees=True, buildings_by_frame=True))
        panel = Image.fromarray(detail.render_detail(scene, view), mode="P")
        panel.putpalette(detail.detail_lookup())
        left = (index % 2) * PANEL_PX
        top = (index // 2) * (PANEL_PX + CAPTION_PX)
        sheet.paste(panel.convert("RGB"), (left, top + CAPTION_PX))
        draw.text((left + 16, top + 10), caption, fill="#f0ece2", font_size=22)
        print(caption, np.asarray(panel).shape)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = Path("out") / area.name / f"{stamp}_look-options.png"
    sheet.save(output)
    print(output)
