# Demo script (6 to 8 minutes)

Before the meeting: `make up && make seed`, open http://localhost:8080 (it starts on the home page), and keep a terminal ready. Record a screen capture once as a backup.

## 1. The problem (30 s)

The old prototype sent one 43 MB GeoJSON with 101,435 polygons for a single area, parsed it three times and drew every polygon. Loading and zooming were slow, and it would not scale to more images or models.

## 2. The architecture (60 s)

Open **System Status** (footer). Every box of the architecture is a running service with a green light: PostGIS, Redis, MinIO, the tile service and the model registry. The table maps each box to its folder. Open `docs/ARCHITECTURE.md` for the diagrams.

## 3. Live map (90 s)

Open **Live Map**. Imagery and crop type are on by default. Use the Filter chip (top left) or click a crop in the ranking to show one crop only, and click a field in the list to fly to it.

- Toggle cropland, crop type, the CDL reference and the field regions. Change opacity.
- Zoom and pan. Point at the Live map panel (top right): a screen costs a few hundred KB of tiles, not 43 MB.
- Click a field: the popup reads real pixel values for every visible layer through `/point`.

## 4. Database (45 s)

```bash
docker compose exec postgres psql -U geocrop -c "select kind, name, format from layer;"
docker compose exec postgres psql -U geocrop -c "select class_name, round(area_ha) from zonal_stat order by area_ha desc limit 8;"
docker compose exec postgres psql -U geocrop -c "select count(*), round(sum(st_area(geom::geography))/10000) as ha from field;"
```

Then open **Dashboard**: the same statistics, read from `zonal_stat`, with the measured model accuracy.

## 5. Upload and job (90 s)

Open **Analyze Imagery**. Either upload a Sentinel-2 GeoTIFF, or choose the Sentinel-2 composite under "Re-analyse an existing image". Select cropland and crop type (or NDVI vegetation index for a fast run). The Processing page shows each step as the Celery worker runs each model, then open the map: the new layers are listed.

## 6. Flexibility (60 s)

Open **Models**. Show `backend/model_registry/builtin/example_ndvi/manifest.yaml` and `task.py`. Explain that copying this folder and editing the manifest adds a model with no change to the API, database, tiles or UI. Show the test:

```bash
make test
```

## 7. Honest status and next steps (45 s)

Open `docs/STATUS.md`: cropland and crop type are real models trained on AOI 1 only (about 93% and 56% held-out accuracy on a random pixel split, so optimistic). Boundary and yield are registered stubs. Next: multi-AOI training with spatial validation, the boundary and yield models, `.SAFE` ingestion.
