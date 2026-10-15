"""Turning files into catalog layers (+ statistics), and catalog rows into API responses."""
from __future__ import annotations

import math
import tempfile
import uuid
from pathlib import Path

from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Layer, ZonalStat
from app.services import rasters
from app.services.storage import get_storage
from model_registry.raster_io import to_cog

# Zoom range from native resolution: 30 m pixels are fully resolved around z13.
DEFAULT_ZOOMS = {"cog": (6, 16), "pmtiles": (8, 16)}


def _json_safe(value):
    """NaN/inf nodata (common for float imagery) cannot go into JSON; store it as null."""
    return None if value is None or not math.isfinite(value) else value


def publish_raster_layer(db: Session, *, local_path: Path, kind: str, name: str, group: str,
                         aoi_id, run_id, style: dict, legend: list, categorical: bool,
                         class_names: dict[int, str] | None = None, is_public: bool = False,
                         already_cog: bool = False) -> Layer:
    """Convert to COG, upload, insert the layer row and its statistics."""
    storage = get_storage()
    layer_id = uuid.uuid4()
    key = f"runs/{run_id or 'reference'}/{kind}-{layer_id.hex[:8]}.cog.tif"
    with tempfile.TemporaryDirectory() as tmp:
        cog = Path(local_path) if already_cog else to_cog(Path(local_path), Path(tmp) / "out.cog.tif", categorical)
        info = rasters.describe(str(cog))
        footprint = rasters.footprint_wgs84(str(cog))
        stats = (rasters.categorical_stats(str(cog), class_names) if categorical and class_names
                 else [rasters.continuous_stats(str(cog))])
        storage.put_file(cog, key, "image/tiff")
    zmin, zmax = DEFAULT_ZOOMS["cog"]
    layer = Layer(id=layer_id, run_id=run_id, aoi_id=aoi_id, kind=kind, group=group, name=name, format="cog",
                  storage_key=key, bounds=from_shape(footprint, srid=4326), min_zoom=zmin, max_zoom=zmax,
                  nodata=_json_safe(info["nodata"]), dtype=info["dtype"], style=style, legend=legend, is_public=is_public)
    db.add(layer)
    db.flush()
    for row in stats:
        db.add(ZonalStat(layer_id=layer.id, zone_type="aoi", zone_id=str(aoi_id), **row))
    return layer


def publish_pmtiles_layer(db: Session, *, local_path: Path, kind: str, name: str, group: str, aoi_id, run_id,
                          bounds_polygon, style: dict, legend: list, is_public: bool = False) -> Layer:
    storage = get_storage()
    layer_id = uuid.uuid4()
    key = f"vector/{aoi_id}/{run_id or 'reference'}/{kind}-{layer_id.hex[:8]}.pmtiles"
    storage.put_file(local_path, key, "application/octet-stream")
    zmin, zmax = DEFAULT_ZOOMS["pmtiles"]
    layer = Layer(id=layer_id, run_id=run_id, aoi_id=aoi_id, kind=kind, group=group, name=name, format="pmtiles",
                  storage_key=key, bounds=from_shape(bounds_polygon, srid=4326), min_zoom=zmin, max_zoom=zmax,
                  dtype="vector", style=style, legend=legend, is_public=is_public)
    db.add(layer)
    db.flush()
    return layer


def layer_to_dict(layer: Layer) -> dict:
    s = get_settings()
    b = to_shape(layer.bounds).bounds if layer.bounds is not None else None
    if layer.format == "cog":
        url = f"{s.public_tile_base}/{layer.id}/{layer.version}/{{z}}/{{x}}/{{y}}.png"
    else:
        url = f"pmtiles://{get_storage().public_url(layer.storage_key)}"
    return {
        "id": str(layer.id), "kind": layer.kind, "group": layer.group, "name": layer.name, "format": layer.format,
        "run_id": str(layer.run_id) if layer.run_id else None, "aoi_id": str(layer.aoi_id) if layer.aoi_id else None,
        "bounds": list(b) if b else None, "min_zoom": layer.min_zoom, "max_zoom": layer.max_zoom,
        "style": layer.style, "legend": layer.legend, "version": layer.version, "tile_url": url,
        "created_at": layer.created_at.isoformat() if layer.created_at else None,
    }
