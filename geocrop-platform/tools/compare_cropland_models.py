"""Compare the previous cropland model (Random Forest) with the new LSTM on AOI 1, against CDL 2022.

Runs inside the worker image (it needs the registry code and the trained models):

    docker compose run --rm --no-deps -v "$PWD/tools:/tools" -v "$OUT:/out" worker \
        python /tools/compare_cropland_models.py all --out /out

Each model runs in its own process so time and peak memory are measured separately.

Inputs (all on /data):
    raw/usa_cdl_aoi1.tif            CDL 2022 labels (the 30 m grid everything is evaluated on)
    raw/aoi1_sentinel2.tif          the single 7-band composite the Random Forest was trained on
    raw/aoi1_composite_2022.tif     the 77-band monthly composite the LSTM needs (tools/build_composite_stac.py)

Labels use the rule both models were trained with: 14 CDL non-crop codes (water, developed, barren, forest,
shrubland, grassland/pasture, wetlands) are non-cropland, every other code is cropland.
"""
import argparse
import importlib.util
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

sys.path.insert(0, "/app")
DATA = Path("/data")
CDL = DATA / "raw/usa_cdl_aoi1.tif"
S2_SINGLE = DATA / "raw/aoi1_sentinel2.tif"
S2_MONTHLY = DATA / "raw/aoi1_composite_2022.tif"
NON_CROP_CODES = [111, 112, 121, 122, 123, 124, 131, 141, 142, 143, 152, 176, 190, 195]
CROP, NONCROP = 1, 2


def cdl_grid():
    with rasterio.open(CDL) as c:
        return c.read(1), c.profile


def single_on_cdl_grid():
    """The 7-band composite resampled onto the CDL grid (bilinear), as the RF training script did."""
    cdl, prof = cdl_grid()
    with rasterio.open(S2_SINGLE) as s:
        out = np.full((s.count, prof["height"], prof["width"]), np.nan, np.float32)
        for b in range(s.count):
            reproject(rasterio.band(s, b + 1), out[b], src_transform=s.transform, src_crs=s.crs,
                      dst_transform=prof["transform"], dst_crs=prof["crs"], resampling=Resampling.bilinear,
                      dst_nodata=np.nan)
    return out


def predict_rf(x):
    """x (7, h, w) features -> uint8 map 1 crop / 2 non-crop / 0 no data (same as the previous plug-in)."""
    import joblib
    clf = joblib.load(DATA / "models/cropland.joblib")["model"]
    h, w = x.shape[1:]
    valid = np.all(np.isfinite(x), axis=0)
    out = np.zeros((h, w), np.uint8)
    pred = clf.predict(x[:, valid].T)
    out[valid] = np.where(pred == 1, CROP, NONCROP)
    return out


def stage_rf_single(out: Path):
    x = single_on_cdl_grid()
    t0 = time.perf_counter()
    pred = predict_rf(x)
    return pred, None, time.perf_counter() - t0


def stage_rf_derived(out: Path):
    from model_registry.raster_io import s2_features
    with rasterio.open(S2_MONTHLY) as s:
        x = s2_features(s.read())
    t0 = time.perf_counter()
    pred = predict_rf(x)
    return pred, None, time.perf_counter() - t0


def _lstm_task():
    spec = importlib.util.spec_from_file_location("cropland_task", "/app/model_registry/builtin/cropland/task.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stage_lstm(out: Path):
    task = _lstm_task()
    model = task.load_model_safely(DATA / "models/cropland_lstm/model.pt")
    with rasterio.open(S2_MONTHLY) as s:
        arr = s.read().astype(np.float32)
        h, w = s.height, s.width
    t0 = time.perf_counter()
    arr = np.where(np.isfinite(arr), arr, -32768)
    feat, use = task.pc.block_features(arr)
    p = model.predict_proba(feat)
    dt = time.perf_counter() - t0
    prob = np.full(h * w, np.nan, np.float32)
    prob[use] = p
    pred = np.zeros(h * w, np.uint8)
    pred[use] = np.where(p > 0.5, CROP, NONCROP)
    return pred.reshape(h, w), prob.reshape(h, w), dt


def stage_croptype(out: Path, source: str):
    """Crop-type RF on CDL cropland pixels, from the original single composite or from features derived from the
    monthly composite. Shows whether the crop-type model still works when the input is a monthly composite."""
    import joblib
    from model_registry.raster_io import s2_features
    cdl, _ = cdl_grid()
    if source == "single":
        x = single_on_cdl_grid()
    else:
        with rasterio.open(S2_MONTHLY) as s:
            x = s2_features(s.read())
    payload = joblib.load(DATA / "models/croptype.joblib")
    clf, names = payload["model"], payload["class_names"]
    mask = (cdl != 0) & ~np.isin(cdl, NON_CROP_CODES) & np.all(np.isfinite(x), axis=0)
    t0 = time.perf_counter()
    pred = np.full(cdl.shape, -1, np.int16)
    pred[mask] = clf.predict(x[:, mask].T)
    return pred, None, time.perf_counter() - t0


STAGES = {"rf_single": stage_rf_single, "rf_derived": stage_rf_derived, "lstm": stage_lstm,
          "croptype_single": lambda o: stage_croptype(o, "single"),
          "croptype_derived": lambda o: stage_croptype(o, "derived")}


def run_stage(name: str, out: Path):
    pred, prob, seconds = STAGES[name](out)
    np.save(out / f"{name}.npy", pred)
    if prob is not None:
        np.save(out / f"{name}_prob.npy", prob)
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    (out / f"{name}.json").write_text(json.dumps({"predict_seconds": round(seconds, 2), "peak_rss_mb": round(rss_mb)}))


# ------------------------------------------------------------------------------------------------ evaluation
def binary_scores(pred, label, mask):
    p, y = pred[mask], label[mask]
    tp = int(((p == CROP) & (y == CROP)).sum()); tn = int(((p == NONCROP) & (y == NONCROP)).sum())
    fp = int(((p == CROP) & (y == NONCROP)).sum()); fn = int(((p == NONCROP) & (y == CROP)).sum())
    rc, rn = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    pc, pn = tp / max(tp + fp, 1), tn / max(tn + fn, 1)
    f = lambda a, b: 2 * a * b / max(a + b, 1e-9)
    return {"pixels": int(mask.sum()), "accuracy": round((tp + tn) / max(mask.sum(), 1), 4),
            "balanced_accuracy": round((rc + rn) / 2, 4),
            "cropland": {"precision": round(pc, 4), "recall": round(rc, 4), "f1": round(f(pc, rc), 4)},
            "non_cropland": {"precision": round(pn, 4), "recall": round(rn, 4), "f1": round(f(pn, rn), 4)},
            "confusion": {"tp": tp, "fn": fn, "fp": fp, "tn": tn}}


def quicklook(path: Path, rgb: np.ndarray, step: int = 2):
    img = rgb[:, ::step, ::step]
    with rasterio.open(path, "w", driver="PNG", width=img.shape[2], height=img.shape[1], count=3, dtype="uint8") as d:
        d.write(img)


def paint(classes: np.ndarray, colors: dict[int, str], background=(255, 255, 255)):
    rgb = np.zeros((3,) + classes.shape, np.uint8)
    for i, c in enumerate(background):
        rgb[i] = c
    for v, hexc in colors.items():
        m = classes == v
        for i in range(3):
            rgb[i][m] = int(hexc[1 + 2 * i:3 + 2 * i], 16)
    return rgb


def evaluate(out: Path):
    cdl, prof = cdl_grid()
    label = np.where(cdl == 0, 0, np.where(np.isin(cdl, NON_CROP_CODES), NONCROP, CROP)).astype(np.uint8)
    pixel_ha = abs(prof["transform"].a * prof["transform"].e) / 10_000
    preds = {k: np.load(out / f"{k}.npy") for k in ("rf_single", "lstm", "rf_derived")}
    common = (label > 0) & np.all([p > 0 for p in preds.values()], axis=0)
    res = {"grid": {"width": prof["width"], "height": prof["height"], "pixel_ha": pixel_ha},
           "label_cropland_share": round(float((label[label > 0] == CROP).mean()), 4),
           "common_pixels": int(common.sum()), "models": {}}
    for k, p in preds.items():
        s = binary_scores(p, label, common)
        s["coverage"] = round(float(((p > 0) & (label > 0)).sum() / (label > 0).sum()), 4)
        s["cropland_area_ha"] = round(float((p == CROP).sum() * pixel_ha))
        s.update(json.loads((out / f"{k}.json").read_text()))
        res["models"][k] = s
    res["label_cropland_area_ha"] = round(float((label == CROP).sum() * pixel_ha))
    a, b = preds["rf_single"], preds["lstm"]
    res["agreement_rf_vs_lstm"] = round(float((a[common] == b[common]).mean()), 4)
    # where the models disagree, who is right
    dis = common & (a != b)
    res["disagreement"] = {"pixels": int(dis.sum()),
                           "lstm_right": int((dis & (b == label)).sum()), "rf_right": int((dis & (a == label)).sum())}
    prob = np.load(out / "lstm_prob.npy")
    res["lstm_probability"] = {"mean": round(float(np.nanmean(prob)), 4),
                               "share_uncertain_0.4_0.6": round(float(((prob > 0.4) & (prob < 0.6)).sum() / np.isfinite(prob).sum()), 4)}

    # crop type with the two kinds of input
    from app.services.cdl import CDL_NAMES
    payload_names = json.loads((DATA / "models/aoi1_croptype.metrics.json").read_text())["class_names"]
    ct = {k: np.load(out / f"{k}.npy") for k in ("croptype_single", "croptype_derived")}
    names_arr = np.array(payload_names)
    cdl_names = np.vectorize(lambda c: CDL_NAMES.get(int(c), ""))(cdl)
    known = set(payload_names) - {"Other crop"}
    truth = np.where(np.isin(cdl_names, list(known)), cdl_names, "Other crop")
    both = (ct["croptype_single"] >= 0) & (ct["croptype_derived"] >= 0)
    res["croptype"] = {"pixels": int(both.sum()),
                       "agreement_single_vs_derived": round(float((ct["croptype_single"][both] == ct["croptype_derived"][both]).mean()), 4)}
    for k, p in ct.items():
        pn = names_arr[p[both]]
        res["croptype"][k] = {"accuracy_vs_cdl": round(float((pn == truth[both]).mean()), 4),
                              **json.loads((out / f"{k}.json").read_text())}

    (out / "comparison.json").write_text(json.dumps(res, indent=1))
    colors = {CROP: "#3f8f3a", NONCROP: "#d8c79a"}
    quicklook(out / "map_cdl.png", paint(label, colors))
    quicklook(out / "map_rf.png", paint(a, colors))
    quicklook(out / "map_lstm.png", paint(b, colors))
    diff = np.zeros(label.shape, np.uint8)
    diff[common & (a == b)] = 1
    diff[common & (a != b) & (b == label)] = 2      # LSTM right
    diff[common & (a != b) & (a == label)] = 3      # RF right
    quicklook(out / "map_disagreement.png", paint(diff, {1: "#e8e8e8", 2: "#1e6fa8", 3: "#c0392b"}))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=list(STAGES) + ["evaluate", "all"])
    ap.add_argument("--out", default="/out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.stage == "all":
        for s in STAGES:
            print("stage", s, flush=True)
            subprocess.run([sys.executable, __file__, s, "--out", a.out], check=True)
        evaluate(out)
    elif a.stage == "evaluate":
        evaluate(out)
    else:
        run_stage(a.stage, out)
