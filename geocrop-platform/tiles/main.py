"""GeoCrop tile service: COG -> XYZ PNG tiles with server-side styles.

Built on TiTiler / rio-tiler. Styles come from the layer record in the API, never
from query parameters. Tile URLs carry the layer version, so responses are
immutable and cached for a year by nginx/CDN and the browser.
"""
import os
import time

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Response
from rio_tiler.colormap import cmap as named_cmaps
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import Reader
from titiler.core.factory import TilerFactory

API = os.environ.get("API_INTERNAL_URL", "http://api:8000/api/v1")
TOKEN = os.environ.get("INTERNAL_TOKEN", "change-me-internal")
CACHE_TTL = 300
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}

app = FastAPI(title="GeoCrop tiles", docs_url="/tiles-docs")
app.include_router(TilerFactory().router, prefix="/cog", tags=["TiTiler COG (debug)"])
_cache: dict[tuple[str, int], tuple[float, dict]] = {}


def layer_info(layer_id: str, version: int) -> dict:
    hit = _cache.get((layer_id, version))
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    r = httpx.get(f"{API}/internal/layers/{layer_id}", headers={"X-Internal-Token": TOKEN}, timeout=5)
    if r.status_code != 200:
        raise HTTPException(404, "Layer not found")
    info = r.json()
    _cache[(layer_id, version)] = (time.time(), info)
    return info


def _hex(c: str) -> tuple[int, int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/tiles/{layer_id}/{version}/{z}/{x}/{y}.png")
def tile(layer_id: str, version: int, z: int, x: int, y: int, classes: str | None = None):
    info = layer_info(layer_id, version)
    if info["format"] != "cog":
        raise HTTPException(400, "Not a raster layer")
    style = info.get("style") or {}
    kind = style.get("type", "continuous")
    method = "nearest" if kind == "categorical" else "bilinear"
    try:
        with Reader(info["path"]) as src:
            img = src.tile(x, y, z, tilesize=256, indexes=tuple(style.get("bidx") or [1]),
                           resampling_method=method, reproject_method=method)
    except TileOutsideBounds:
        return Response(status_code=204, headers=IMMUTABLE)

    if kind == "categorical":
        cmap = {int(k): _hex(v) for k, v in style.get("colormap", {}).items()}
        if classes:  # optional crop filter: hide every class not listed
            keep = {int(c) for c in classes.split(",") if c.strip().isdigit()}
            cmap = {k: (v if k in keep else (0, 0, 0, 0)) for k, v in cmap.items()}
        content = img.render(img_format="PNG", colormap=cmap)
    else:
        lo, hi = style.get("rescale", [0, 1])
        img.array.mask |= ~np.isfinite(img.array.data)
        img.rescale(in_range=[(lo, hi)] * img.count)
        cm = named_cmaps.get(style["colormap_name"]) if kind == "continuous" and style.get("colormap_name") else None
        content = img.render(img_format="PNG", colormap=cm)
    return Response(content, media_type="image/png", headers=IMMUTABLE)
