"""Cropland vs non-cropland. Ported from fast_shared/train_cropland_model.py (inference only)."""
import joblib
import numpy as np
import rasterio

from model_registry.base import ModelTask, RunContext, RunResult
from model_registry.raster_io import output_profile, s2_features, windows


class CroplandTask(ModelTask):
    def validate(self, ctx: RunContext) -> list[str]:
        problems = []
        if not (ctx.artifact_dir / self.manifest["artifact"]).exists():
            problems.append(f"Trained model file {self.manifest['artifact']} is missing. Run ml/train_cropland_model.py.")
        with rasterio.open(ctx.image_path) as src:
            if src.count not in self.manifest["input_spec"]["accepts_band_counts"]:
                problems.append(f"Image has {src.count} bands; this model needs 6 or 7 "
                                f"({', '.join(self.manifest['input_spec']['bands'])}).")
        return problems

    def run(self, ctx: RunContext) -> RunResult:
        clf = joblib.load(ctx.artifact_dir / self.manifest["artifact"])["model"]
        out_path = ctx.out_dir / "cropland.tif"
        counts = {1: 0, 2: 0}
        with rasterio.open(ctx.image_path) as src:
            wins = list(windows(src))
            with rasterio.open(out_path, "w", **output_profile(src, "uint8", 0)) as dst:
                for i, w in enumerate(wins):
                    x = s2_features(src.read(window=w))
                    valid = np.all(np.isfinite(x), axis=0)
                    out = np.zeros(valid.shape, dtype="uint8")
                    if valid.any():
                        pred = clf.predict(x[:, valid].T)
                        out[valid] = np.where(pred == 1, 1, 2)
                    dst.write(out, 1, window=w)
                    for c in counts:
                        counts[c] += int((out == c).sum())
                    ctx.progress((i + 1) / len(wins), f"Classifying block {i + 1} of {len(wins)}")
        return RunResult(files={"cropland": out_path},
                         metrics={"pixels_cropland": counts[1], "pixels_non_cropland": counts[2]},
                         class_names={1: "Cropland", 2: "Non-cropland"})
