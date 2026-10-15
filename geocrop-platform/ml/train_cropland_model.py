"""
GeoCrop platform copy of train_cropland_model.py.

Extended vs the prototype original: besides the GeoJSON it now also saves
  data/models/cropland.joblib      the fitted Random Forest (used by the registry)
  data/results/aoi1_cropland.tif   predicted raster: 0 nodata, 1 cropland, 2 non-cropland
  data/results/aoi1_cropland.metrics.json   held-out metrics (random pixel split, single AOI)
Set SKIP_VECTORIZE=1 to skip the slow GeoJSON step.
"""
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parents[1]
import sys

import numpy as np
import rasterio
from rasterio.features import shapes as raster_shapes
from rasterio.warp import reproject, Resampling, transform_geom
from shapely.geometry import shape, mapping
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

NON_CROP_CODES = {111, 112, 121, 122, 123, 124, 131, 141, 142, 143, 152, 176, 190, 195}
NODATA_CODE = 0
BAND_NAMES = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI"]


def load_and_align(cdl_path, imagery_path):
    """Read the CDL raster as-is (it's our reference grid) and resample the
    Sentinel-2 composite onto that exact same grid, so every pixel lines up
    1-to-1 between the two files."""
    with rasterio.open(cdl_path) as cdl_src:
        cdl = cdl_src.read(1)
        cdl_profile = cdl_src.profile

    with rasterio.open(imagery_path) as img_src:
        bands = np.zeros((img_src.count, cdl.shape[0], cdl.shape[1]), dtype=np.float32)
        for i in range(img_src.count):
            reproject(
                source=rasterio.band(img_src, i + 1),
                destination=bands[i],
                dst_transform=cdl_profile["transform"],
                dst_crs=cdl_profile["crs"],
                dst_resolution=(30, 30),
                resampling=Resampling.bilinear,
            )

    return cdl, bands, cdl_profile


def build_training_table(cdl, bands):
    """Flatten the aligned rasters into a (pixels x features) table, one row
    per valid (non-nodata) pixel, with its crop/non-crop label."""
    valid = cdl != NODATA_CODE
    labels = np.where(np.isin(cdl, list(NON_CROP_CODES)), 0, 1)  # 0=non-crop, 1=crop

    X = bands[:, valid].T          # (n_valid_pixels, n_bands)
    y = labels[valid]
    return X, y, valid


def vectorize_prediction(pred_raster, valid_mask, profile):
    """Turn a predicted 0/1 raster into GeoJSON polygons in WGS84, so
    Leaflet can draw them directly (mirrors how field_data_view already
    serves the dummy field polygons)."""
    out = np.where(valid_mask, pred_raster, 255).astype(np.uint8)  # 255 = ignore in vectorization

    features = []
    for geom, value in raster_shapes(out, mask=(out != 255), transform=profile["transform"]):
        if value != 1:  # only keep the "cropland" polygons
            continue
        geom_wgs84 = transform_geom(profile["crs"], "EPSG:4326", geom)
        features.append({
            "type": "Feature",
            "geometry": geom_wgs84,
            "properties": {"predicted_class": "cropland"},
        })

    return {"type": "FeatureCollection", "features": features}


def main():
    if len(sys.argv) != 4:
        print("Usage: python train_cropland_model.py <cdl.tif> <sentinel2.tif> <output.geojson>")
        sys.exit(1)

    cdl_path, imagery_path, out_geojson = sys.argv[1], sys.argv[2], sys.argv[3]

    print("Aligning imagery to the CDL grid...")
    cdl, bands, profile = load_and_align(cdl_path, imagery_path)

    print("Building training table...")
    X, y, valid = build_training_table(cdl, bands)
    print(f"  {X.shape[0]:,} labeled pixels, {X.shape[1]} features each "
          f"({sum(y)}, cropland / {len(y) - sum(y)} non-cropland)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
    clf.fit(X_train, y_train)

    print("\nAccuracy on held-out pixels:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["non-cropland", "cropland"]))
    print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

    print("\nFeature importance:")
    for name, imp in sorted(zip(BAND_NAMES, clf.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name:6s} {imp:.3f}")

    print("\nRunning model over the full AOI...")
    full_pred = clf.predict(bands.reshape(bands.shape[0], -1).T).reshape(cdl.shape)

    # --- platform additions: persist model, raster and metrics -------------
    import json as _json, joblib as _joblib, os as _os
    (ROOT / "data/models").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/results").mkdir(parents=True, exist_ok=True)
    _joblib.dump({"model": clf, "band_names": BAND_NAMES, "labels": {"0": "non-cropland", "1": "cropland"}},
                 ROOT / "data/models/cropland.joblib")
    _out = np.where(valid, np.where(full_pred == 1, 1, 2), 0).astype("uint8")
    _prof = profile.copy()
    _prof.update(dtype="uint8", count=1, nodata=0, compress="deflate")
    with rasterio.open(ROOT / "data/results/aoi1_cropland.tif", "w", **_prof) as _dst:
        _dst.write(_out, 1)
    _rep = classification_report(y_test, y_pred, target_names=["non-cropland", "cropland"], output_dict=True)
    with open(ROOT / "data/results/aoi1_cropland.metrics.json", "w") as _f:
        _json.dump({"model": "RandomForest(200, depth 12)", "split": "random 80/20 pixels, stratified, seed 42",
                    "note": "single AOI, spatial leakage likely; accuracy is optimistic",
                    "report": _rep, "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
                    "feature_importance": dict(zip(BAND_NAMES, map(float, clf.feature_importances_)))}, _f, indent=2)
    print("Saved model, raster and metrics under data/")
    if _os.environ.get("SKIP_VECTORIZE") == "1":
        return

    print(f"Vectorizing predictions -> {out_geojson}")
    geojson = vectorize_prediction(full_pred, valid, profile)
    import json
    with open(out_geojson, "w") as f:
        json.dump(geojson, f)
    print(f"Wrote {len(geojson['features'])} cropland polygons.")


if __name__ == "__main__":
    main()
