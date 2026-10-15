"""Raster helpers used by the API and workers: footprint, point sampling, statistics, preprocessing."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform, transform_bounds
from shapely.geometry import box

TARGET_CRS = "EPSG:5070"   # grid the current models were trained on
TARGET_RES = 30.0


def footprint_wgs84(path: str):
    """Bounding box of a raster as a shapely polygon in EPSG:4326."""
    with rasterio.open(path) as ds:
        return box(*transform_bounds(ds.crs, "EPSG:4326", *ds.bounds, densify_pts=21))


def describe(path: str) -> dict:
    with rasterio.open(path) as ds:
        res = abs(ds.transform.a)
        return {"band_count": ds.count, "crs": str(ds.crs) if ds.crs else None, "width": ds.width,
                "height": ds.height, "dtype": ds.dtypes[0], "resolution": res, "nodata": ds.nodata}


def sample(path: str, lng: float, lat: float) -> float | None:
    """Value of band 1 at a lon/lat, or None outside the raster or on nodata."""
    with rasterio.open(path) as ds:
        xs, ys = transform("EPSG:4326", ds.crs, [lng], [lat])
        row, col = ds.index(xs[0], ys[0])
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            return None
        val = ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
        if ds.nodata is not None and val == ds.nodata:
            return None
        if isinstance(val, (np.floating, float)) and not np.isfinite(val):
            return None
        return float(val)


def categorical_stats(path: str, class_names: dict[int, str]) -> list[dict]:
    """Pixel count and area (ha) per class over the whole raster, read block by block."""
    counts: dict[int, int] = {}
    with rasterio.open(path) as ds:
        pixel_ha = abs(ds.transform.a * ds.transform.e) / 10_000 if ds.crs and ds.crs.is_projected else None
        for _, w in ds.block_windows(1):
            vals, n = np.unique(ds.read(1, window=w), return_counts=True)
            for v, c in zip(vals.tolist(), n.tolist()):
                counts[v] = counts.get(v, 0) + c
        nodata = ds.nodata
    rows = []
    for code, n in sorted(counts.items()):
        if code == nodata or code not in class_names:
            continue
        rows.append({"class_code": int(code), "class_name": class_names[code], "pixel_count": n,
                     "area_ha": round(n * pixel_ha, 2) if pixel_ha else 0.0})
    return rows


def continuous_stats(path: str) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1, masked=True).astype("float64")
        pixel_ha = abs(ds.transform.a * ds.transform.e) / 10_000 if ds.crs and ds.crs.is_projected else 0
    valid = arr.compressed()
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return {"pixel_count": 0, "area_ha": 0.0, "mean": None, "min": None, "max": None}
    return {"pixel_count": int(valid.size), "area_ha": round(valid.size * pixel_ha, 2),
            "mean": float(valid.mean()), "min": float(valid.min()), "max": float(valid.max())}


def preprocess_to_model_grid(src_path: str, dst_path: Path) -> Path:
    """Reproject an uploaded image onto the grid the models were trained on
    (EPSG:5070, 30 m, bilinear), keeping band order. Mirrors training alignment."""
    with rasterio.open(src_path) as src:
        if src.crs is None:
            raise ValueError("The image has no coordinate reference system, so it cannot be placed on the map.")
        dst_transform, w, h = calculate_default_transform(
            src.crs, TARGET_CRS, src.width, src.height, *src.bounds, resolution=TARGET_RES)
        prof = src.profile.copy()
        prof.update(driver="GTiff", crs=TARGET_CRS, transform=dst_transform, width=w, height=h,
                    dtype="float32", nodata=np.nan, tiled=True, blockxsize=512, blockysize=512, compress="deflate")
        with rasterio.open(dst_path, "w", **prof) as dst:
            for b in range(1, src.count + 1):
                reproject(rasterio.band(src, b), rasterio.band(dst, b), src_nodata=src.nodata,
                          dst_nodata=np.nan, resampling=Resampling.bilinear)
            dst.descriptions = src.descriptions
    return dst_path
