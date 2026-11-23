# Upgrade path: from demo to product

The demo is built to be upgraded in place. Each row says what is demo-grade today and what replaces it, without rewriting the rest.

| Area | Today | Upgrade | Touches |
|---|---|---|---|
| Models | Random Forests trained on AOI 1 only, random pixel split | Multi-AOI training with spatial hold-out, stored metrics per version | `ml/`, new model folders |
| Boundary model | Registered stub; demo layer is regions of one predicted crop | Real boundary model writing COG or polygons, then PMTiles | `model_registry/builtin/boundary/` |
| Yield model | Registered stub | Model trained with USDA NASS yield history | `model_registry/builtin/yield_/` |
| Input formats | Stacked Sentinel-2 GeoTIFF (6 or 7 bands) | `.SAFE` reader, cloud mask (SCL), multi-date composites | `workers/tasks.py` ingest step |
| Auth | Email/password, JWT | Identity provider (Keycloak, Auth0) behind `core/security.py` | `core/security.py` |
| Private tiles | Tile URLs are unauthenticated | Short-lived signed tile tokens checked by the tile service | `tiles/main.py`, `layers.py` |
| Basemap | Keyless OSM fallback unless a key is set | MapTiler or Esri account key in `.env` | `.env` only |
| Large uploads | Single PUT | Multipart upload, resumable | `web/src/pages/Upload.tsx`, storage |
| Vector tiles | Pure-Python PMTiles builder | tippecanoe for large inputs | `services/vector_tiles.py` |
| Many images | One layer per image | MosaicJSON / STAC mosaics in TiTiler | `tiles/main.py` |
| Scale | Single host, Docker Compose | Managed Postgres, S3, CDN in front of `/tiles`, autoscaled workers and tile replicas | deployment only |
| Monitoring | `/health` + status page | Metrics (tile latency, queue depth), alerts | new |
| Migrations | Initial Alembic revision | `alembic revision --autogenerate` per change | `backend/alembic/` |
