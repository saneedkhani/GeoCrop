SHELL := /bin/bash
PY := .venv/bin/python
COMPOSE := docker compose

.PHONY: help venv data up down logs migrate seed reset test benchmark web-dev ps

help: ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-11s %s\n", $$1, $$2}'

venv: ## Host Python env for ml/ and tools/
	python3 -m venv .venv && $(PY) -m pip install -q numpy rasterio scikit-learn==1.9.1 shapely pyproj joblib pyyaml \
	  pyshp mapbox-vector-tile mercantile pmtiles pytest

data: ## Copy AOI 1 inputs, train both models, build COGs and the boundary PMTiles
	./scripts/fetch_demo_data.sh
	cd ml && SKIP_VECTORIZE=1 ../$(PY) train_cropland_model.py ../data/raw/usa_cdl_aoi1.tif ../data/raw/aoi1_sentinel2.tif /tmp/c.geojson
	cd ml && SKIP_VECTORIZE=1 ../$(PY) train_croptype_model.py ../data/raw/usa_cdl_aoi1.tif ../data/raw/aoi1_sentinel2.tif /tmp/t.geojson
	mkdir -p data/cog
	$(PY) tools/to_cog.py data/raw/aoi1_sentinel2.tif data/cog/aoi1_sentinel2.cog.tif --continuous
	$(PY) tools/to_cog.py data/raw/usa_cdl_aoi1.tif data/cog/aoi1_cdl.cog.tif --categorical
	$(PY) tools/build_boundaries.py data/results/aoi1_croptype.tif data/results/aoi1_croptype.metrics.json data/results

up: ## Build and start the whole stack
	$(COMPOSE) up -d --build

ps: ## Service status
	$(COMPOSE) ps

down: ## Stop the stack (data volumes are kept)
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

seed: ## Load AOI 1 layers, runs and statistics into PostGIS + MinIO
	$(COMPOSE) exec api python -m app.cli.seed_demo

reset: ## Re-seed the demo AOI from scratch
	$(COMPOSE) exec api python -m app.cli.seed_demo --reset

test: ## Backend tests (registry + flexibility test)
	cd backend && ../$(PY) -m pytest tests -q

benchmark: ## Tile latency and size vs the old 43 MB GeoJSON
	$(PY) tools/benchmark_tiles.py

web-dev: ## Frontend dev server on :5173 (talks to the stack on :8080)
	cd web && npm install && npm run dev
