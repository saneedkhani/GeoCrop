"""Raster classes -> polygons -> PMTiles (vector tiles), in pure Python.

Used for the boundary layer today and for any future model that outputs
regions. tippecanoe can replace this later for very large inputs.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import mapbox_vector_tile
import mercantile
import rasterio
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import box, mapping, shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform


def polygonize(raster_path: str, class_names: dict[int, str], min_pixels: int = 25,
               simplify_m: float = 15.0) -> list[dict]:
    """Connected same-class regions as GeoJSON-like features in EPSG:4326."""
    feats = []
    with rasterio.open(raster_path) as ds:
        arr = ds.read(1)
        pix_area = abs(ds.transform.a * ds.transform.e)
        for i, (geom, val) in enumerate(shapes(arr, mask=arr > 0, transform=ds.transform)):
            poly = shape(geom)
            if poly.area < min_pixels * pix_area:
                continue
            poly = poly.simplify(simplify_m, preserve_topology=True)
            if poly.is_empty:
                continue
            g = transform_geom(ds.crs, "EPSG:4326", mapping(poly))
            code = int(val)
            feats.append({"geometry": g, "properties": {
                "field_id": len(feats) + 1, "class_code": code, "class_name": class_names.get(code, str(code)),
                "area_ha": round(poly.area / 10_000, 2)}})
    return feats


def write_pmtiles(features: list[dict], out_path: Path, min_zoom: int = 8, max_zoom: int = 14,
                  layer_name: str = "fields") -> dict:
    """Encode features into MVT tiles for each zoom and pack them into one PMTiles file."""
    geoms = [(shp_transform(_to_3857, shape(f["geometry"])), f["properties"]) for f in features]
    lons, lats = [], []
    for f in features:
        b = shape(f["geometry"]).bounds
        lons += [b[0], b[2]]
        lats += [b[1], b[3]]
    west, south, east, north = min(lons), min(lats), max(lons), max(lats)
    tiles = {}
    for z in range(min_zoom, max_zoom + 1):
        for t in mercantile.tiles(west, south, east, north, zooms=[z]):
            xb = mercantile.xy_bounds(t)
            buf = (xb.right - xb.left) * 0.02
            tile_box = box(xb.left - buf, xb.bottom - buf, xb.right + buf, xb.top + buf)
            tol = (xb.right - xb.left) / 4096
            layer_feats = []
            for g, props in geoms:
                if not g.intersects(tile_box):
                    continue
                clipped = g.intersection(tile_box).simplify(tol, preserve_topology=True)
                if not clipped.is_empty:
                    layer_feats.append({"geometry": clipped.wkb, "properties": props})
            if not layer_feats:
                continue
            data = mapbox_vector_tile.encode(
                [{"name": layer_name, "features": layer_feats}],
                default_options={"quantize_bounds": (xb.left, xb.bottom, xb.right, xb.top), "extents": 4096})
            tiles[zxy_to_tileid(z, t.x, t.y)] = gzip.compress(data)
    with open(out_path, "wb") as f:
        w = Writer(f)
        for tid in sorted(tiles):
            w.write_tile(tid, tiles[tid])
        w.finalize(
            {"tile_type": TileType.MVT, "tile_compression": Compression.GZIP,
             "min_lon_e7": int(west * 1e7), "min_lat_e7": int(south * 1e7),
             "max_lon_e7": int(east * 1e7), "max_lat_e7": int(north * 1e7),
             "center_zoom": (min_zoom + max_zoom) // 2,
             "center_lon_e7": int((west + east) / 2 * 1e7), "center_lat_e7": int((south + north) / 2 * 1e7)},
            {"name": layer_name, "vector_layers": [{"id": layer_name, "fields": {
                "field_id": "Number", "class_code": "Number", "class_name": "String", "area_ha": "Number"}}]})
    return {"tiles": len(tiles), "features": len(features), "bounds": [west, south, east, north]}


def save_geojson(features: list[dict], path: Path) -> None:
    path.write_text(json.dumps({"type": "FeatureCollection",
                                "features": [{"type": "Feature", **f} for f in features]}))
