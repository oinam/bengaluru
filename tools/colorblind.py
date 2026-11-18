"""Show the map as the three kinds of color blindness see it, and list the colors that merge.

    uv run python tools/colorblind.py [area] [lon lat]

Renders one frame of a built area, the test patch by default, and lays it beside the
same frame as seen with protanopia, deuteranopia, and tritanopia, with the palette and
the metro's line colors as swatches under each. Prints every pair of colors that must
be told apart on the map and are less than NEAR apart for some viewer. Changes nothing;
writes out/<area>/<stamp>_colorblind.png.

The simulation is Machado, Oliveira, and Fernandes (2009) at full severity, applied in
linear RGB. The distance is CIE76, the straight-line distance in L*a*b*.
"""

import datetime as dt
import itertools
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer

from bengaluru import detail
from bengaluru.areas import get_area
from bengaluru.prepare import METRIC_CRS
from bengaluru.render import centered_viewport

PANEL_PX = 1280
CAPTION_PX = 44
SWATCH_PX = 56
# Below this two flat colors side by side are hard to tell apart.
NEAR = 12.0
VISION = {
    "Typical vision": np.eye(3),
    "Protanopia, no red cones": np.array(
        [
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216],
            [-0.003882, -0.048116, 1.051998],
        ]
    ),
    "Deuteranopia, no green cones": np.array(
        [
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881],
        ]
    ),
    "Tritanopia, no blue cones": np.array(
        [
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900],
        ]
    ),
}
# The colors that mean something on the map; roofs are decoration and are left out.
MEANING = (
    "tree",
    "grass",
    "built",
    "bare",
    "wetland",
    "water",
    "road_major",
    "road_minor",
    "road_track",
    "wall_lit",
    "wall_shade",
)
# The metro's lines as OpenStreetMap colors them, which the viewer draws over the map.
METRO = {
    "Purple": "#e542de",
    "Green": "#009933",
    "Yellow": "#ffff00",
    "Pink": "#ff49a7",
    "Blue": "#0000ff",
}


def to_linear(rgb: np.ndarray) -> np.ndarray:
    srgb = rgb / 255.0
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def to_srgb(linear: np.ndarray) -> np.ndarray:
    linear = np.clip(linear, 0.0, 1.0)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    return np.rint(srgb * 255).astype("uint8")


def seen(rgb: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return colors, as an (..., 3) array of 0 to 255, the way a viewer sees them."""
    return to_srgb(to_linear(rgb.astype("float64")) @ matrix.T)


def to_lab(rgb: np.ndarray) -> np.ndarray:
    xyz = (
        to_linear(rgb.astype("float64"))
        @ np.array(
            [
                [0.4124564, 0.3575761, 0.1804375],
                [0.2126729, 0.7151522, 0.0721750],
                [0.0193339, 0.1191920, 0.9503041],
            ]
        ).T
        / np.array([0.95047, 1.0, 1.08883])
    )
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack(
        [116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])],
        axis=-1,
    )


def rgb_of(color: str) -> np.ndarray:
    return np.frombuffer(bytes.fromhex(color.lstrip("#")), dtype="uint8")


def near_pairs(colors: dict[str, str], pairs) -> list[tuple[str, str, dict[str, float]]]:
    """Return the pairs some viewer sees less than NEAR apart, with each viewer's distance."""
    found = []
    for first, second in pairs:
        apart = {
            name: float(
                np.linalg.norm(
                    to_lab(seen(rgb_of(colors[first]), matrix))
                    - to_lab(seen(rgb_of(colors[second]), matrix))
                )
            )
            for name, matrix in VISION.items()
        }
        if min(apart.values()) < NEAR:
            found.append((first, second, apart))
    return found


def sheet(frame: np.ndarray, colors: dict[str, str]) -> Image.Image:
    """Lay the frame and the swatches out once for each kind of vision."""
    height = CAPTION_PX + PANEL_PX + SWATCH_PX
    page = Image.new("RGB", (2 * PANEL_PX, 2 * height), "#1f2a2e")
    draw = ImageDraw.Draw(page)
    chips = np.array([rgb_of(color) for color in colors.values()])
    chip = PANEL_PX // len(chips)
    for index, (name, matrix) in enumerate(VISION.items()):
        left, top = (index % 2) * PANEL_PX, (index // 2) * height
        draw.text((left + 16, top + 10), name, fill="#f0ece2", font_size=22)
        page.paste(Image.fromarray(seen(frame, matrix)), (left, top + CAPTION_PX))
        for position, color in enumerate(seen(chips, matrix)):
            x = left + position * chip
            y = top + CAPTION_PX + PANEL_PX
            draw.rectangle((x, y, x + chip - 1, y + SWATCH_PX - 1), fill=tuple(color))
    return page


if __name__ == "__main__":
    area = get_area(sys.argv[1] if len(sys.argv) > 1 else "vidhana-soudha")
    lon, lat = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else area.center
    scene = detail.load_scene(area, use_cached_trees=True, buildings_by_frame=True)
    x, y = Transformer.from_crs(4326, METRIC_CRS, always_xy=True).transform(lon, lat)
    detail.use_view("315")
    view = centered_viewport(detail.PROJECTION, x, y, PANEL_PX, PANEL_PX)
    picture = Image.fromarray(detail.render_detail(scene, view), mode="P")
    picture.putpalette(detail.detail_lookup())

    palette = detail.detail_colors()
    colors = {**{name: palette[name] for name in MEANING}, **METRO}
    on_the_map = itertools.combinations(MEANING, 2)
    metro = itertools.chain(itertools.combinations(METRO, 2), itertools.product(METRO, MEANING))
    for title, pairs in (("On the map", on_the_map), ("The metro's lines", metro)):
        print(title)
        for first, second, apart in near_pairs(colors, pairs):
            distances = ", ".join(
                f"{name.split(',')[0]} {value:.0f}" for name, value in apart.items()
            )
            print(f"  {first} and {second}: {distances}")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = Path("out") / area.name / f"{stamp}_colorblind.png"
    sheet(np.asarray(picture.convert("RGB")), colors).save(output)
    print(output)
