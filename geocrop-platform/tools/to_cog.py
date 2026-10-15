"""Convert a GeoTIFF into a validated Cloud Optimized GeoTIFF (COG).

Usage:
    python tools/to_cog.py SRC DST [--categorical | --continuous]

Categorical rasters (class codes) use NEAREST overviews so classes are never
blended; continuous rasters (imagery, yield) use AVERAGE.
"""
import argparse
import sys

import rasterio
import rasterio.shutil


def convert(src: str, dst: str, categorical: bool) -> None:
    rasterio.shutil.copy(
        src, dst, driver="COG",
        COMPRESS="DEFLATE", BLOCKSIZE=512, BIGTIFF="IF_SAFER",
        OVERVIEW_RESAMPLING="NEAREST" if categorical else "AVERAGE",
        RESAMPLING="NEAREST" if categorical else "BILINEAR",
        NUM_THREADS="ALL_CPUS",
    )


def validate(path: str) -> list[str]:
    """Return a list of problems; empty means the file is a usable COG."""
    problems = []
    with rasterio.open(path) as ds:
        if ds.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") != "COG":
            problems.append("LAYOUT is not COG")
        if not ds.profile.get("tiled"):
            problems.append("not internally tiled")
        if (ds.width > 512 or ds.height > 512) and not ds.overviews(1):
            problems.append("no overviews")
        if ds.crs is None:
            problems.append("no CRS")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--categorical", action="store_true")
    g.add_argument("--continuous", action="store_true")
    a = ap.parse_args()
    convert(a.src, a.dst, categorical=a.categorical)
    problems = validate(a.dst)
    if problems:
        print(f"INVALID COG {a.dst}: {', '.join(problems)}", file=sys.stderr)
        return 1
    with rasterio.open(a.dst) as ds:
        print(f"OK {a.dst}  {ds.width}x{ds.height}  bands={ds.count}  {ds.dtypes[0]}  "
              f"overviews={ds.overviews(1)}  crs={ds.crs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
