# GeoCrop

**GeoCrop: Automated Crop Monitoring and Forecasting Toolkit** (FAST-NUCES Islamabad, FYP F26-155)

GeoCrop turns Sentinel-2 satellite imagery into crop intelligence: cropland, crop type, field regions
and (planned) yield, shown as fast, toggleable layers on a live web map.

**Team:** Huzaifa Bin Khalid, Saneed Ullah, Taha Bashir Awan
**Supervisor:** Mr. Muhammad Aadil Ur Rehman | **Co-supervisor:** Mr. Obaid Ur Rehman (Institute of Space Technology)

## What is in this repository

| Folder | What it is | Status |
|---|---|---|
| [`geocrop-platform/`](geocrop-platform/) | **Base architecture with implementation**: React + MapLibre, FastAPI, TiTiler (COG tiles), PMTiles, PostGIS, Celery + Redis, MinIO, Nginx, Docker Compose | Current |
| [`geocrop/`](geocrop/) | Proposal-stage **Django + Leaflet prototype** | Kept for reference |

The platform replaces the prototype. The prototype sent one 43.3 MB GeoJSON file (101,435 polygons)
for a single area; the platform sends only the map tiles in view.

## Why the platform is faster (AOI 1, crop-type layer)

| Measure | Prototype | Platform |
|---|---|---|
| Data for one screen | 43.3 MB | **337 KB** (24 tiles) |
| Cold tile (median / p95) | n/a (JSON parse alone 1,021 ms) | **47 ms / 54 ms** |
| Cached tile | n/a | **1 ms** |
| Upload to map | preview only, no model run | **57 s** |
| Stored result | 43.3 MB GeoJSON | 222 KB GeoTIFF |

## Architecture in one picture

```
Browser (React + MapLibre GL)
        |
      Nginx  -- serves the app, proxies /api, caches /tiles
     /     \
FastAPI    TiTiler  (COG -> PNG tiles)
   |  \        |
PostGIS  Redis/Celery workers --> MinIO (COG, PMTiles, uploads)
```

Full description: [`geocrop-platform/docs/ARCHITECTURE.md`](geocrop-platform/docs/ARCHITECTURE.md).

## Quick start

Requirements: Docker with Compose; Python 3.11+ on the host (for data preparation).

```bash
cd geocrop-platform
cp .env.example .env
make venv        # host Python env for ml/ and tools/
make data        # needs the AOI 1 input files, see below (~3 min)
make up          # build and start all services
make seed        # load AOI 1 layers, runs and statistics
```

Open **http://localhost:8080** (API docs at `/api/docs`).

Daily use: `make up` / `make down`. Other targets: `make ps`, `make logs`, `make test`, `make benchmark`.

### Data and model files are not in git

The satellite imagery, CDL labels and trained models are large (about 1.7 GB) and are gitignored.
To run the platform you need either:

- the `fast_shared/` input folder from the prototype work (used by `make data`), or
- the prepared `geocrop-platform/data/` folder shared by the team.

## Plug in a new model

Copy `geocrop-platform/backend/model_registry/builtin/example_ndvi`, edit the manifest, write
`run()`, and restart `api` and `worker`. The API, database and interface need no changes. See
[`docs/ADDING_A_MODEL.md`](geocrop-platform/docs/ADDING_A_MODEL.md).

## Documentation

| Document | Location |
|---|---|
| FYP-1 mid report (LaTeX + PDF) | [`geocrop-platform/docs/fyp1-mid-report/`](geocrop-platform/docs/fyp1-mid-report/) |
| Design artifacts and design evolution | [`geocrop-platform/docs/design-artifacts/`](geocrop-platform/docs/design-artifacts/) |
| Architecture vs. prototype comparison | [`geocrop-platform/docs/architecture-comparison/`](geocrop-platform/docs/architecture-comparison/) |
| Revised evaluation metrics | [`geocrop-platform/docs/evaluation-metrics/`](geocrop-platform/docs/evaluation-metrics/) |
| Benchmark | [`geocrop-platform/docs/benchmark.md`](geocrop-platform/docs/benchmark.md) |
| Status, upgrade path, demo script | [`geocrop-platform/docs/`](geocrop-platform/docs/) |

## Crop-type model work

Eleven crop-type models were compared on two U.S. areas (AOI 1 eastern Washington, AOI 2 North
Dakota) with a spatial block split. A small CPU-only LightGBM pipeline (about 2 MB) is proposed:
76.1% accuracy on AOI 1 and 92.2% on AOI 2. The platform currently runs a baseline Random Forest;
integrating the selected pipeline is the first task of Iteration 2.

## Roadmap

1. **Iteration 1 (done):** base architecture, benchmark, crop-type model evaluation.
2. **Iteration 2:** integrate the LightGBM pipeline, CDL confidence rule, cross-area test, multi-image upload, usability study.
3. **Iteration 3 (FYP-2):** field-boundary model and yield model.
4. **Iteration 4 (FYP-2):** end-to-end evaluation, hardening, deployment.

## Prototype (`geocrop/`)

```bash
cd geocrop
pip install -r requirements.txt
python manage.py runserver
```

## Data sources

Sentinel-2 (ESA / Copernicus), USDA Cropland Data Layer, USDA NASS statistics.
