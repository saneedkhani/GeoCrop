"""Small helpers shared by model tasks: windowed reading, feature building and COG writing."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import rasterio
import rasterio.shutil
from rasterio.windows import Window

S2_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI"]


def windows(src: rasterio.io.DatasetReader, size: int = 512) -> Iterator[Window]:
    for row in range(0, src.height, size):
        for col in range(0, src.width, size):
            yield Window(col, row, min(size, src.width - col), min(size, src.height - row))


def s2_features(block: np.ndarray) -> np.ndarray:
    """Return the 7 training features (B2,B3,B4,B8,B11,B12,NDVI) for a (bands,h,w) block.

    Accepts 7-band input as trained, or 6 bands and computes NDVI exactly like the
    training composite: (B8 - B4) / (B8 + B4).
    """
    block = block.astype("float32")
    if block.shape[0] == 7:
        return block
    if block.shape[0] == 6:
        b4, b8 = block[2], block[3]
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = (b8 - b4) / (b8 + b4)
        return np.concatenate([block, ndvi[None]], axis=0)
    raise ValueError(f"Expected 6 or 7 Sentinel-2 bands, got {block.shape[0]}")


def output_profile(src: rasterio.io.DatasetReader, dtype: str, nodata) -> dict:
    prof = src.profile.copy()
    prof.update(driver="GTiff", count=1, dtype=dtype, nodata=nodata, tiled=True,
                blockxsize=512, blockysize=512, compress="deflate")
    return prof


def to_cog(src_path: Path, dst_path: Path, categorical: bool) -> Path:
    rasterio.shutil.copy(
        str(src_path), str(dst_path), driver="COG", COMPRESS="DEFLATE", BLOCKSIZE=512,
        OVERVIEW_RESAMPLING="NEAREST" if categorical else "AVERAGE", NUM_THREADS="ALL_CPUS")
    return dst_path
