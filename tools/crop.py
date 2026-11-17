"""Render one frame of a built area centered on a place, into out/<area>/.

    uv run python tools/crop.py central lalbagh 77.58691 12.94886 [view] [size]

The area must have been built, so its trees are placed. The view is "315", north up,
unless given; the size is 2048 px.
"""

import datetime as dt
import sys
from pathlib import Path

from pyproj import Transformer

from bengaluru import detail
from bengaluru.areas import get_area
from bengaluru.prepare import METRIC_CRS
from bengaluru.render import centered_viewport

if __name__ == "__main__":
    area = get_area(sys.argv[1])
    name, lon, lat = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    view_name = sys.argv[5] if len(sys.argv) > 5 else "315"
    size = int(sys.argv[6]) if len(sys.argv) > 6 else detail.CROP_PX
    scene = detail.load_scene(area, use_cached_trees=True, buildings_by_frame=True)
    x, y = Transformer.from_crs(4326, METRIC_CRS, always_xy=True).transform(lon, lat)
    detail.use_view(view_name)
    view = centered_viewport(detail.PROJECTION, x, y, size, size)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = Path("out") / area.name / f"{stamp}_crop-{name}-{view_name}.png"
    detail.save_slots(detail.render_detail(scene, view), output)
    print(output)
