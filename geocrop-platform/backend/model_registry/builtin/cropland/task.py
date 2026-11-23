"""Cropland vs non-cropland with the class-weighted LSTM (Gajardo 2023 / Kerner 2020).

Input: the 77-band monthly composite (April..October x 11 values) built by tools/build_composite_stac.py.
geocrop_model.py and predict_cropland.py are the model team's files, unchanged; this task only adapts
them to the platform contract (block-wise run, progress, output codes 1 = cropland, 2 = non-cropland, 0 = no data).
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import rasterio

from model_registry.base import ModelTask, RunContext, RunResult
from model_registry.raster_io import output_profile, windows

HERE = Path(__file__).parent
_NODATA_I16 = -32768


def _load(name: str):
    """Import a sibling file under its own name (predict_cropland.py imports `geocrop_model`)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gm = _load("geocrop_model")
pc = _load("predict_cropland")
_MODEL_CACHE: dict[str, object] = {}


def load_model_safely(path: Path):
    """Load model.pt with weights_only=True (tensors and numpy arrays only, no arbitrary objects)."""
    key = str(path)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    import torch
    from numpy._core.multiarray import _reconstruct
    torch.serialization.add_safe_globals([_reconstruct, np.ndarray, np.dtype, type(np.dtype("float32"))])
    ck = torch.load(path, map_location="cpu", weights_only=True)
    model = gm.TorchCropModel.__new__(gm.TorchCropModel)
    model.kind, state = ck["kind"], ck["state"]
    model.mean = np.asarray(ck["mean"], np.float32)
    model.std = np.asarray(ck["std"], np.float32)
    model.net = gm._build_net(model.kind, state)
    model.net.load_state_dict(state)
    model.net.eval()
    _MODEL_CACHE[key] = model
    return model


class CroplandLSTMTask(ModelTask):
    def validate(self, ctx: RunContext) -> list[str]:
        problems = []
        if not (ctx.artifact_dir / self.manifest["artifact"]).exists():
            problems.append(f"Trained model file {self.manifest['artifact']} is missing from the model folder.")
        with rasterio.open(ctx.image_path) as src:
            if src.count != gm.T * gm.NB:
                problems.append(
                    f"Image has {src.count} bands; this cropland model needs the 77-band monthly composite "
                    "(April-October x 11: B02 B03 B04 B05 B06 B07 B08 B8A B11 B12 NDVI). "
                    "Build it with tools/build_composite_stac.py.")
        return problems

    def run(self, ctx: RunContext) -> RunResult:
        model = load_model_safely(ctx.artifact_dir / self.manifest["artifact"])
        threshold = float((self.manifest.get("training") or {}).get("threshold", 0.5))
        out_path = ctx.out_dir / "cropland.tif"
        counts = {1: 0, 2: 0}
        prob_sum = 0.0
        with rasterio.open(ctx.image_path) as src:
            wins = list(windows(src))
            with rasterio.open(out_path, "w", **output_profile(src, "uint8", 0)) as dst:
                for i, w in enumerate(wins):
                    block = src.read(window=w).astype("float32")
                    # Uploaded images arrive as float32 with NaN for no data; the builder writes int16 with -32768.
                    block = np.where(np.isfinite(block), np.round(block), _NODATA_I16)
                    feat, use = pc.block_features(block)
                    out = np.zeros(block.shape[1] * block.shape[2], dtype="uint8")
                    if len(feat):
                        p = model.predict_proba(feat)
                        out[use] = np.where(p > threshold, 1, 2)
                        prob_sum += float(p.sum())
                    out = out.reshape(block.shape[1], block.shape[2])
                    dst.write(out, 1, window=w)
                    for c in counts:
                        counts[c] += int((out == c).sum())
                    ctx.progress((i + 1) / len(wins), f"Classifying block {i + 1} of {len(wins)}")
        n = counts[1] + counts[2]
        return RunResult(files={"cropland": out_path},
                         metrics={"pixels_cropland": counts[1], "pixels_non_cropland": counts[2],
                                  "mean_probability": round(prob_sum / n, 4) if n else None},
                         class_names={1: "Cropland", 2: "Non-cropland"})
