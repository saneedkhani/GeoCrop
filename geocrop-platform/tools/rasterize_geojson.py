"""Fallback: rasterize a prototype result GeoJSON back onto the CDL grid.

Only used if re-training is not possible. The raster is then derived from the
vector output, which STATUS.md must say.

Usage:
    python tools/rasterize_geojson.py GEOJSON REFERENCE_TIF OUT_TIF PROPERTY
"""
import json
import sys

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom


def main() -> int:
    gj_path, ref_path, out_path, prop = sys.argv[1:5]
    gj = json.load(open(gj_path))
    names = sorted({f["properties"][prop] for f in gj["features"]})
    code = {n: i + 1 for i, n in enumerate(names)}
    with rasterio.open(ref_path) as ref:
        prof = ref.profile.copy()
        shapes = ((transform_geom("EPSG:4326", ref.crs, f["geometry"]), code[f["properties"][prop]])
                  for f in gj["features"])
        arr = rasterize(shapes, out_shape=(ref.height, ref.width), transform=ref.transform, fill=0, dtype="uint8")
    prof.update(dtype="uint8", count=1, nodata=0, compress="deflate")
    with rasterio.open(out_path, "w", **prof) as dst:
        dst.write(arr, 1)
    json.dump({"class_names": names}, open(out_path + ".classes.json", "w"))
    print(f"Wrote {out_path} with {len(names)} classes, {int((arr > 0).sum()):,} pixels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
