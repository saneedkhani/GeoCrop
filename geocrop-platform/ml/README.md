# ml/

Copies of the prototype training scripts, extended to persist the artifacts the platform needs.

```bash
. ../.venv/bin/activate
SKIP_VECTORIZE=1 python train_cropland_model.py ../data/raw/usa_cdl_aoi1.tif ../data/raw/aoi1_sentinel2.tif /tmp/c.geojson
SKIP_VECTORIZE=1 python train_croptype_model.py ../data/raw/usa_cdl_aoi1.tif ../data/raw/aoi1_sentinel2.tif /tmp/t.geojson
```

Outputs: `data/models/*.joblib`, `data/results/*.tif`, `data/results/*.metrics.json`.
Limitation: trained and evaluated on AOI 1 only, random pixel split (optimistic).
