# GeoCrop platform

Crop intelligence from Sentinel-2 imagery: cropland, crop type, field regions and (later) yield, shown as fast, toggleable layers on a live map.

This repository is the **working demo of the GeoCrop architecture** and the foundation of the product. It replaces the old Django prototype. Real parts and demo shortcuts are listed in [docs/STATUS.md](docs/STATUS.md).

## Stack

| Concern | Technology |
|---|---|
| Frontend | React, Vite, TypeScript, React Router, TanStack Query, Zustand |
| Map | MapLibre GL JS via `react-map-gl` |
| Raster results | Cloud Optimized GeoTIFF (COG) served as tiles by TiTiler / rio-tiler |
| Vector results | PMTiles read by the browser through the `pmtiles` protocol |
| API | FastAPI (OpenAPI docs at `/api/docs`) |
| Database | PostgreSQL + PostGIS, SQLAlchemy 2, GeoAlchemy2, Alembic |
| Jobs | Celery workers, Redis broker |
| Storage | MinIO (S3 API) |
| Edge | Nginx (SPA, API proxy, tile cache with immutable headers) |
| Models | Plug-in registry (`backend/model_registry/`), scikit-learn Random Forests for cropland and crop type |

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it

Requirements: Docker with Compose, Python 3.11+ on the host (for data preparation), and the old prototype's `fast_shared/` folder for the AOI 1 data.

```bash
cp .env.example .env              # optional: set VITE_BASEMAP_MODE=provider and VITE_BASEMAP_KEY
make venv                         # host Python env for ml/ and tools/
make data                         # copy AOI 1, train both models, build COGs and PMTiles (~3 min)
make up                           # build and start every service
make seed                         # load AOI 1 layers, runs and statistics
```

Open **http://localhost:8080**. The app opens on the home page without sign-in (set `AUTH_REQUIRED=true` and `VITE_AUTH_REQUIRED=true` to require it).

| URL | What |
|---|---|
| http://localhost:8080 | The app |
| http://localhost:8080/api/docs | API documentation |
| http://localhost:9001 | MinIO console (`minioadmin` / `minioadmin`, local only) |
| `localhost:5432` | PostGIS (`geocrop` / `geocrop`) |

Other commands: `make ps`, `make logs`, `make test`, `make benchmark`, `make reset`, `make down`.

No Docker? See [docs/RUN_WITHOUT_DOCKER.md](docs/RUN_WITHOUT_DOCKER.md).

## Add a model

Copy `backend/model_registry/builtin/example_ndvi`, change the manifest, write `run()`, restart `api` and `worker`. Nothing else changes. Details: [docs/ADDING_A_MODEL.md](docs/ADDING_A_MODEL.md).

## Repository layout

```
backend/        FastAPI app, Celery workers, model registry, Alembic, tests
tiles/          TiTiler-based tile service
web/            React app + nginx config
ml/             training scripts (extended copies of the prototype's)
tools/          COG conversion, boundary PMTiles, benchmark
infra/          MinIO init, nginx reference config
scripts/        data fetch
docs/           architecture, status, upgrade path, demo script
data/           (gitignored) inputs, trained models, results
```
