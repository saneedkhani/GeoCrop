"""
GeoCrop platform copy of train_croptype_model.py.

Extended vs the prototype original: also saves
  data/models/croptype.joblib   {"model", "class_names", "keep_codes", "band_names"}
  data/results/aoi1_croptype.tif   uint8: 0 nodata/non-cropland, N = class_names[N-1]
  data/results/aoi1_croptype.metrics.json
Set SKIP_VECTORIZE=1 to skip the slow GeoJSON step.
"""
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parents[1]
import argparse
import json
import sys

import numpy as np
import rasterio
from rasterio.features import shapes as raster_shapes
from rasterio.warp import reproject, Resampling, transform_geom
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# Same non-crop codes as train_cropland_model.py - a pixel with one of
# these codes never enters stage 2 at all.
NON_CROP_CODES = {111, 112, 121, 122, 123, 124, 131, 141, 142, 143, 152, 176, 190, 195}
NODATA_CODE = 0
BAND_NAMES = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI"]

OTHER_CROP_LABEL = "Other crop"

# Standard USDA CDL crop codes. Anything actually present in your raster
# that ISN'T in this dict still works fine - it just prints as "Class <n>"
# instead of a name, so we never guess at a label we're not sure of.
CDL_CROP_NAMES = {
    1: "Corn", 2: "Cotton", 3: "Rice", 4: "Sorghum", 5: "Soybeans",
    6: "Sunflower", 10: "Peanuts", 11: "Tobacco", 12: "Sweet Corn",
    13: "Pop or Orn Corn", 14: "Mint", 21: "Barley", 22: "Durum Wheat",
    23: "Spring Wheat", 24: "Winter Wheat", 25: "Other Small Grains",
    26: "Winter Wheat/Soybeans", 27: "Rye", 28: "Oats", 29: "Millet",
    30: "Speltz", 31: "Canola", 32: "Flaxseed", 33: "Safflower",
    34: "Rape Seed", 35: "Mustard", 36: "Alfalfa", 37: "Other Hay/Non Alfalfa",
    38: "Camelina", 39: "Buckwheat", 41: "Sugarbeets", 42: "Dry Beans",
    43: "Potatoes", 44: "Other Crops", 45: "Sugarcane", 46: "Sweet Potatoes",
    47: "Misc Vegs & Fruits", 48: "Watermelons", 49: "Onions", 50: "Cucumbers",
    51: "Chick Peas", 52: "Lentils", 53: "Peas", 54: "Tomatoes",
    55: "Caneberries", 56: "Hops", 57: "Herbs", 58: "Clover/Wildflowers",
    59: "Sod/Grass Seed", 61: "Fallow/Idle Cropland", 66: "Cherries",
    67: "Peaches", 68: "Apples", 69: "Grapes", 70: "Christmas Trees",
    71: "Other Tree Crops", 72: "Citrus", 74: "Pecans", 75: "Almonds",
    76: "Walnuts", 77: "Pears", 204: "Pistachios", 205: "Triticale",
    206: "Carrots", 207: "Asparagus", 208: "Garlic", 209: "Cantaloupes",
    210: "Prunes", 211: "Olives", 212: "Oranges", 213: "Honeydew Melons",
    214: "Broccoli", 216: "Peppers", 217: "Pomegranates", 218: "Nectarines",
    219: "Greens", 220: "Plums", 221: "Strawberries", 222: "Squash",
    223: "Apricots", 224: "Vetch", 225: "Winter Wheat/Corn", 226: "Sweet Corn/Corn",
    227: "Lettuce", 228: "Oats/Corn", 229: "Pumpkins", 242: "Blueberries",
    243: "Cabbage", 244: "Cauliflower", 245: "Celery", 246: "Radishes",
    247: "Turnips", 248: "Eggplants", 249: "Gourds", 250: "Cranberries",
}


def load_and_align(cdl_path, imagery_path):
    """Same as train_cropland_model.py: use the CDL raster's grid as the
    reference, resample the Sentinel-2 composite onto it pixel-for-pixel."""
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


def build_cropland_mask(cdl):
    """Stage-1 label, recomputed here so stage 2 only ever sees pixels
    stage 1 would call cropland - keeps the two models consistent even if
    you run this script on its own."""
    valid = cdl != NODATA_CODE
    is_cropland = valid & ~np.isin(cdl, list(NON_CROP_CODES))
    return is_cropland


def bucket_rare_classes(codes, min_pixels):
    """Any CDL code with fewer than min_pixels occurrences becomes
    "Other crop" instead of its own class. Returns (label_ids, class_names)
    where class_names[i] is the human name for label id i."""
    values, counts = np.unique(codes, return_counts=True)
    keep_codes = sorted(v for v, c in zip(values, counts) if c >= min_pixels)

    class_names = [CDL_CROP_NAMES.get(c, f"Class {c}") for c in keep_codes]
    class_names.append(OTHER_CROP_LABEL)
    other_id = len(keep_codes)

    code_to_id = {c: i for i, c in enumerate(keep_codes)}
    label_ids = np.array([code_to_id.get(c, other_id) for c in codes])

    return label_ids, class_names, keep_codes


def vectorize_prediction(pred_raster, valid_mask, profile, class_names):
    """Same idea as train_cropland_model.py's vectorizer, but each polygon
    now carries the predicted crop NAME instead of a fixed "cropland" tag."""
    out = np.where(valid_mask, pred_raster, 255).astype(np.uint16)

    features = []
    for geom, value in raster_shapes(out, mask=(out != 255), transform=profile["transform"]):
        geom_wgs84 = transform_geom(profile["crs"], "EPSG:4326", geom)
        features.append({
            "type": "Feature",
            "geometry": geom_wgs84,
            "properties": {"crop_type": class_names[int(value)]},
        })

    return {"type": "FeatureCollection", "features": features}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cdl", help="CDL GeoTIFF (e.g. usa_cdl_aoi1.tif)")
    parser.add_argument("imagery", help="Sentinel-2 composite from export_sentinel2_gee.py")
    parser.add_argument("out_geojson", help="Output GeoJSON path")
    parser.add_argument("--min-pixels", type=int, default=5000,
                         help="Crops with fewer training pixels than this get bucketed into "
                              "'Other crop' instead of their own class (default: 5000)")
    args = parser.parse_args()

    print("Aligning imagery to the CDL grid...")
    cdl, bands, profile = load_and_align(args.cdl, args.imagery)

    print("Restricting to cropland pixels (stage 1 output)...")
    cropland_mask = build_cropland_mask(cdl)
    print(f"  {cropland_mask.sum():,} of {cdl.size:,} pixels are cropland")

    codes = cdl[cropland_mask]
    label_ids, class_names, keep_codes = bucket_rare_classes(codes, args.min_pixels)
    print(f"\n  {len(keep_codes)} crop types kept as their own class "
          f"(>= {args.min_pixels:,} px), everything else bucketed as '{OTHER_CROP_LABEL}':")
    for code, name in zip(keep_codes, class_names):
        n = int((codes == code).sum())
        print(f"    {name:24s} ({n:,} px)")
    other_n = int((label_ids == len(keep_codes)).sum())
    if other_n:
        print(f"    {OTHER_CROP_LABEL:24s} ({other_n:,} px)")

    X = bands[:, cropland_mask].T
    y = label_ids

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("\nTraining Random Forest (multi-class)...")
    clf = RandomForestClassifier(n_estimators=300, max_depth=16, n_jobs=-1, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    print("\nAccuracy on held-out pixels:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=class_names, zero_division=0))
    print("Confusion matrix (rows=actual, cols=predicted):\n", confusion_matrix(y_test, y_pred))

    print("\nFeature importance:")
    for name, imp in sorted(zip(BAND_NAMES, clf.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name:6s} {imp:.3f}")

    print("\nRunning model over all cropland pixels in the AOI...")
    full_flat = bands.reshape(bands.shape[0], -1).T
    full_pred = np.zeros(cdl.size, dtype=np.uint16)
    flat_cropland = cropland_mask.reshape(-1)
    full_pred[flat_cropland] = clf.predict(full_flat[flat_cropland])
    full_pred = full_pred.reshape(cdl.shape)

    # --- platform additions: persist model, raster and metrics -------------
    import joblib as _joblib, os as _os
    (ROOT / "data/models").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/results").mkdir(parents=True, exist_ok=True)
    _joblib.dump({"model": clf, "class_names": class_names, "keep_codes": [int(c) for c in keep_codes],
                  "band_names": BAND_NAMES}, ROOT / "data/models/croptype.joblib")
    _out = np.where(cropland_mask, full_pred.astype("int32") + 1, 0).astype("uint8")
    _prof = profile.copy()
    _prof.update(dtype="uint8", count=1, nodata=0, compress="deflate")
    with rasterio.open(ROOT / "data/results/aoi1_croptype.tif", "w", **_prof) as _dst:
        _dst.write(_out, 1)
    _rep = classification_report(y_test, y_pred, target_names=class_names, zero_division=0, output_dict=True)
    with open(ROOT / "data/results/aoi1_croptype.metrics.json", "w") as _f:
        json.dump({"model": "RandomForest(300, depth 16, balanced)", "min_pixels": args.min_pixels,
                   "split": "random 80/20 pixels, stratified, seed 42",
                   "note": "single AOI, spatial leakage likely; accuracy is optimistic",
                   "class_names": class_names, "report": _rep,
                   "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
                   "feature_importance": dict(zip(BAND_NAMES, map(float, clf.feature_importances_)))}, _f, indent=2)
    print("Saved model, raster and metrics under data/")
    if _os.environ.get("SKIP_VECTORIZE") == "1":
        return 0

    print(f"Vectorizing predictions -> {args.out_geojson}")
    geojson = vectorize_prediction(full_pred, cropland_mask, profile, class_names)
    with open(args.out_geojson, "w") as f:
        json.dump(geojson, f)
    print(f"Wrote {len(geojson['features'])} crop-type polygons.")


if __name__ == "__main__":
    sys.exit(main())
