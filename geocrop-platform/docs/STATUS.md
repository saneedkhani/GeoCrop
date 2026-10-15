# Status: what is real, partial and stubbed

Kept honest on purpose. Nothing marked "stub" produces data.

| Area | Status | Detail |
|---|---|---|
| Cropland model | **Real** | Random Forest (200 trees, depth 12) trained on Sentinel-2 + USDA CDL for AOI 1. Held-out accuracy 0.93 on a random 80/20 pixel split (optimistic: same area, spatial leakage likely). Runs live in the worker on any 6 or 7-band Sentinel-2 GeoTIFF. |
| Crop type model | **Real** | Random Forest (300 trees, depth 16, balanced), 13 crops + "Other crop". Held-out accuracy 0.56, macro F1 0.51, same caveat. Model file is 1.5 GB, so a run takes extra seconds to load it. |
| Boundary model | **Stub** | Registered, returns "not available". |
| Field regions layer | **Demo-grade** | Same-class regions of the crop-type raster (at least 25 pixels), vectorized to PMTiles. Not a boundary model. 2,433 regions, also stored in PostGIS `field`. |
| Yield model | **Stub** | Registered, returns "not available". |
| NDVI example model | **Real (template)** | The plug-in template; computes NDVI on any image. |
| Tiles | **Real** | COG + TiTiler/rio-tiler, versioned immutable URLs, nginx cache. |
| Vector tiles | **Real** | PMTiles from MinIO through the `pmtiles` protocol. Built with a pure-Python writer; tippecanoe is the upgrade for large inputs. |
| Database | **Real** | PostgreSQL + PostGIS, Alembic migration (main layer table is `map_layer`: the PostGIS image already has a `topology.layer` table), catalog, runs, statistics, fields, jobs. |
| Jobs | **Real** | Celery + Redis; ingest and model runs with per-step progress. |
| Storage | **Real** | MinIO S3 API (pinned `bitnamilegacy/minio:2025.7.23`, because MinIO removed its official images from Docker Hub and Quay in 2025). |
| Auth | **Demo-grade** | Sign-in is off by default (`AUTH_REQUIRED=false`, `VITE_AUTH_REQUIRED=false`): the app opens straight to the map as the guest (`demo`) account, and "Sign in" stays available. Set both to `true` to require sign-in. Email/password + JWT; identity provider is the upgrade. |
| Tile access control | **Demo-grade** | Catalog is per user; tile URLs themselves are not authenticated. Signed tile tokens are the upgrade. |
| Basemap | **Fallback by default** | Keyless OpenStreetMap until `VITE_BASEMAP_MODE=provider` and `VITE_BASEMAP_KEY` are set. Shown on screen. |
| Upload formats | **Partial** | Georeferenced GeoTIFF with Sentinel-2 bands B2, B3, B4, B8, B11, B12 (+ NDVI), reflectance × 10,000. `.SAFE` and cloud masking are not done. |
| Geography | **Limited** | Models are valid for AOI 1 (Columbia Basin, WA). The model cards say so. |

## Verified end to end (this machine)

- `docker compose up` brings up 7 services; `/health` reports database, Redis, storage, tiles and models all OK.
- Seed loads AOI 1 (imagery, CDL reference, cropland, crop type, field regions) in about 5 s.
- Upload of the AOI 1 Sentinel-2 GeoTIFF through a signed URL, ingest, cropland and crop type inference and publishing: **57 s** with live step progress.
- Live inference vs the training-time raster: class areas agree closely (Apples 6,927 ha in both; Alfalfa 11,340 vs 10,781 ha). Differences come from masking by the *predicted* cropland at inference vs the CDL mask during training.
- Registry tests pass (5/5), including the add-a-model-by-manifest test.

## Performance (`make benchmark`)

| Measure | Old prototype (GeoJSON) | New (COG tiles via TiTiler) |
|---|---|---|
| Data for one screen of AOI 1 | 43.3 MB (whole file) | 337 KB (24 tiles) |
| Objects the browser must draw | 101,435 polygons | 24 PNG images |
| Server/parse time | 1,021 ms just to parse the JSON | cold tile p50 47 ms, p95 54 ms |
| Cached tile latency | no caching | p50 1 ms (nginx cache hit) |
| Typical tile size | n/a | median 2.9 KB, max 44 KB |

Latest run: [benchmark.md](benchmark.md).
