"""Crop type, stage 2: runs only where the cropland model said cropland.
Ported from fast_shared/train_croptype_model.py (inference only)."""
import joblib
import numpy as np
import rasterio

from model_registry.base import ModelTask, RunContext, RunResult
from model_registry.raster_io import output_profile, s2_features, windows


class CropTypeTask(ModelTask):
    def validate(self, ctx: RunContext) -> list[str]:
        problems = []
        if not (ctx.artifact_dir / self.manifest["artifact"]).exists():
            problems.append(f"Trained model file {self.manifest['artifact']} is missing. Run ml/train_croptype_model.py.")
        if "cropland" not in ctx.upstream:
            problems.append("Crop type needs the cropland layer from the same run.")
        return problems

    def run(self, ctx: RunContext) -> RunResult:
        payload = joblib.load(ctx.artifact_dir / self.manifest["artifact"])
        clf, names = payload["model"], payload["class_names"]
        out_path = ctx.out_dir / "croptype.tif"
        counts = np.zeros(len(names) + 1, dtype="int64")
        with rasterio.open(ctx.image_path) as src, rasterio.open(ctx.upstream["cropland"]) as crop:
            wins = list(windows(src))
            with rasterio.open(out_path, "w", **output_profile(src, "uint8", 0)) as dst:
                for i, w in enumerate(wins):
                    x = s2_features(src.read(window=w))
                    mask = (crop.read(1, window=w) == 1) & np.all(np.isfinite(x), axis=0)
                    out = np.zeros(mask.shape, dtype="uint8")
                    if mask.any():
                        out[mask] = clf.predict(x[:, mask].T).astype("uint8") + 1
                    dst.write(out, 1, window=w)
                    counts += np.bincount(out.ravel(), minlength=len(counts))[: len(counts)]
                    ctx.progress((i + 1) / len(wins), f"Classifying crops, block {i + 1} of {len(wins)}")
        class_names = {i + 1: n for i, n in enumerate(names)}
        return RunResult(files={"croptype": out_path}, class_names=class_names,
                         metrics={"pixels_by_class": {class_names[c]: int(counts[c]) for c in class_names}})
