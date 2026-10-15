"""Example plug-in model: NDVI = (B8 - B4) / (B8 + B4). Copy this folder to add a model."""
import numpy as np
import rasterio

from model_registry.base import ModelTask, RunContext, RunResult
from model_registry.raster_io import output_profile, windows


class NdviTask(ModelTask):
    def run(self, ctx: RunContext) -> RunResult:
        out_path = ctx.out_dir / f"{self.manifest['outputs'][0]['kind']}.tif"
        with rasterio.open(ctx.image_path) as src:
            wins = list(windows(src))
            with rasterio.open(out_path, "w", **output_profile(src, "float32", -9999.0)) as dst:
                for i, w in enumerate(wins):
                    b4, b8 = src.read(3, window=w).astype("float32"), src.read(4, window=w).astype("float32")
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ndvi = (b8 - b4) / (b8 + b4)
                    dst.write(np.where(np.isfinite(ndvi), ndvi, -9999.0).astype("float32"), 1, window=w)
                    ctx.progress((i + 1) / len(wins), f"NDVI block {i + 1} of {len(wins)}")
        return RunResult(files={self.manifest["outputs"][0]["kind"]: out_path})
