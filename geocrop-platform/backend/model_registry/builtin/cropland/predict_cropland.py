"""predict_cropland.py - turn a monthly Sentinel-2 composite GeoTIFF into a cropland map with the saved GeoCrop model.

INPUT  composite GeoTIFF with 77 bands = 7 months (Apr..Oct) x 11 (B02 B03 B04 B05 B06 B07 B08 B8A B11 B12 NDVI), int16,
       reflectance x 10000 (NDVI x 10000), nodata -32768. This is exactly what build_composite_stac.py and the dataset
       notebook (aoiN_composite_2022.tif) write.
OUTPUT GeoTIFF, same grid: band 1 = cropland probability (float32, nodata -1), band 2 = class (uint8: 1 cropland, 0 non-cropland, 255 no data)

A pixel needs clean data in at least 6 of the 7 months; other gaps are filled by linear interpolation between neighbouring
months (same rule as in training). Other pixels are written as no data.

CLI:  python predict_cropland.py --composite comp.tif --model-dir model --out cropland.tif [--threshold 0.5]
"""
import argparse
import time

import numpy as np
import rasterio

from geocrop_model import MONTHS, NB, T, load_model

NODATA_I16 = -32768


def fill_months(feat, month_ok):
    """feat (N, T, NB) float32; month_ok (N, T) bool. Linear interpolation over months (flat at the ends), done per pattern of valid months."""
    idx = month_ok.astype(np.int64) @ (1 << np.arange(T))
    for pat in np.unique(idx):
        v = [m for m in range(T) if (pat >> m) & 1]
        if len(v) == T: continue
        rows = np.where(idx == pat)[0]
        for m in range(T):
            if m in v: continue
            left = [x for x in v if x < m]; right = [x for x in v if x > m]
            if not left: feat[rows, m] = feat[rows, right[0]]
            elif not right: feat[rows, m] = feat[rows, left[-1]]
            else:
                l, r = left[-1], right[0]; w = (m - l) / (r - l)
                feat[rows, m] = (1 - w) * feat[rows, l] + w * feat[rows, r]
    return feat


def block_features(arr, min_valid_months=6):
    """arr (77, h, w) int16 -> (features (n, 77) float32 for the usable pixels, boolean mask (h*w,) of usable pixels)."""
    n_b, h, w = arr.shape
    if n_b != T * NB: raise ValueError(f"expected {T * NB} bands (7 months x 11), found {n_b}")
    X = arr.reshape(T, NB, h * w).astype(np.float32)
    ok = (X != NODATA_I16).all(axis=1)                                   # (T, h*w): month usable only if all 11 values exist
    use = ok.sum(0) >= min_valid_months
    feat = np.transpose(X[:, :, use], (2, 0, 1)) / 10000.0              # (n, T, NB), reflectance 0-1 and NDVI -1..1
    feat = fill_months(feat, ok[:, use].T)
    return feat.reshape(len(feat), T * NB), use


def predict_raster(composite, out, model_dir, rows_per_block=256, threshold=0.5, min_valid_months=6):
    model = load_model(model_dir); t0 = time.time(); n_pred = 0
    with rasterio.open(composite) as src:
        if src.count != T * NB: raise ValueError(f"{composite}: {src.count} bands, expected {T * NB}")
        prof = src.profile.copy(); prof.update(count=2, dtype="float32", nodata=-1.0, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
        prof.pop("predictor", None)
        with rasterio.open(out, "w", **prof) as dst:
            dst.set_band_description(1, "cropland_probability"); dst.set_band_description(2, "cropland_class_1_crop_0_non_255_nodata")
            for r0 in range(0, src.height, rows_per_block):
                h = min(rows_per_block, src.height - r0); win = rasterio.windows.Window(0, r0, src.width, h)
                feat, use = block_features(src.read(window=win), min_valid_months)
                prob = np.full(h * src.width, -1.0, np.float32); cls = np.full(h * src.width, 255, np.float32)
                if len(feat):
                    p = model.predict_proba(feat).astype(np.float32); prob[use] = p; cls[use] = (p > threshold).astype(np.float32); n_pred += len(p)
                dst.write(prob.reshape(h, src.width), 1, window=win); dst.write(cls.reshape(h, src.width), 2, window=win)
    print(f"predicted {n_pred:,} pixels in {time.time() - t0:.0f}s -> {out}")
    return n_pred


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Predict cropland / non-cropland from a monthly Sentinel-2 composite")
    ap.add_argument("--composite", required=True); ap.add_argument("--model-dir", default="model"); ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.5); ap.add_argument("--rows-per-block", type=int, default=256)
    a = ap.parse_args(); predict_raster(a.composite, a.out, a.model_dir, a.rows_per_block, a.threshold)
