"""Load the AOI 1 demo into PostGIS + object storage.

Real data only: the Sentinel-2 composite, the USDA CDL reference, the two trained
models' predicted rasters and their stored metrics, and the demo boundary layer.

    python -m app.cli.seed_demo            # skip if already seeded
    python -m app.cli.seed_demo --reset    # remove the demo AOI and seed again
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import shapefile
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.models import Aoi, Field, Layer, Model, ModelRun, SourceImage, User, ZonalStat
from app.db.session import SessionLocal
from app.services.cdl import CDL_NAMES
from app.services.layers import publish_pmtiles_layer, publish_raster_layer
from app.services.models_sync import artifact_dir, sync_models
from model_registry.colormaps import QUALITATIVE, categorical, rgb

DATA = Path("/data")
AOI_NAME = "AOI 1: Columbia Basin, Washington"
DEMO_USER = {"username": "demo", "email": "demo@geocrop.local", "password": "geocrop-demo"}


def need(path: Path) -> Path:
    if not path.exists():
        sys.exit(f"Missing {path}. Run `make data` first (see README).")
    return path


def reset(db) -> None:
    aoi = db.scalar(select(Aoi).where(Aoi.name == AOI_NAME))
    if not aoi:
        return
    layer_ids = db.scalars(select(Layer.id).where(Layer.aoi_id == aoi.id)).all()
    db.execute(delete(ZonalStat).where(ZonalStat.layer_id.in_(layer_ids)))
    db.execute(delete(Layer).where(Layer.aoi_id == aoi.id))
    db.execute(delete(Field).where(Field.aoi_id == aoi.id))
    db.execute(delete(ModelRun).where(ModelRun.aoi_id == aoi.id))
    db.execute(delete(SourceImage).where(SourceImage.aoi_id == aoi.id))
    db.delete(aoi)
    db.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    print("1/7 Registering models from the registry")
    errors = sync_models(db)
    for e in errors:
        print("   registry warning:", e)
    for name in ("aoi1_cropland.metrics.json", "aoi1_croptype.metrics.json"):
        src = DATA / "results" / name
        if src.exists():
            shutil.copyfile(src, artifact_dir() / name)

    if args.reset:
        reset(db)
    if db.scalar(select(Aoi).where(Aoi.name == AOI_NAME)):
        print("Demo already seeded. Use --reset to seed again.")
        return

    print("2/7 Demo user")
    user = db.scalar(select(User).where(User.username == DEMO_USER["username"]))
    if not user:
        user = User(username=DEMO_USER["username"], email=DEMO_USER["email"], role="admin",
                    password_hash=hash_password(DEMO_USER["password"]))
        db.add(user)
        db.flush()

    print("3/7 AOI 1 boundary from the shapefile")
    shp = shapefile.Reader(str(need(DATA / "raw/Pl_usa_aoi1_wgs84.shp")))
    geom = shape(shp.shape(0).__geo_interface__)
    if geom.geom_type != "Polygon":
        geom = geom.envelope
    aoi = Aoi(owner_id=user.id, name=AOI_NAME, geom=from_shape(geom, srid=4326), is_public=True)
    db.add(aoi)
    db.flush()

    print("4/7 Sentinel-2 imagery and CDL reference")
    s, legend = rgb([3, 2, 1], [0, 2000])
    img = publish_raster_layer(db, local_path=need(DATA / "cog/aoi1_sentinel2.cog.tif"), kind="imagery",
                               name="Sentinel-2 composite (true colour)", group="Imagery", aoi_id=aoi.id,
                               run_id=None, style=s, legend=legend, categorical=False, already_cog=True,
                               is_public=True)
    db.add(SourceImage(aoi_id=aoi.id, kind="sentinel2_composite", storage_key=img.storage_key, bounds=img.bounds,
                       crs_original="EPSG:5070", band_count=7, resolution_m=30.0, captured_on="2022 season"))
    import rasterio, numpy as np
    with rasterio.open(DATA / "cog/aoi1_cdl.cog.tif") as d:
        codes = [int(c) for c in np.unique(d.read(1)) if c in CDL_NAMES]
    s, legend = categorical({c: CDL_NAMES[c] for c in codes})
    publish_raster_layer(db, local_path=DATA / "cog/aoi1_cdl.cog.tif", kind="reference_cdl",
                         name="USDA Cropland Data Layer 2022 (reference)", group="Reference", aoi_id=aoi.id,
                         run_id=None, style=s, legend=legend, categorical=True,
                         class_names={c: CDL_NAMES[c] for c in codes}, already_cog=True, is_public=True)

    print("5/7 Model results: cropland and crop type")
    runs = {}
    for key, kind, group in (("cropland", "cropland", "Cropland"), ("croptype", "croptype", "Crop type")):
        model = db.scalar(select(Model).where(Model.key == key))
        metrics = json.loads(need(DATA / f"results/aoi1_{key}.metrics.json").read_text())
        rep = metrics.get("report", {})
        run = ModelRun(aoi_id=aoi.id, model_id=model.id, status="done", started_at=now, finished_at=now,
                       params={"source": "training run on AOI 1 (ml/)"},
                       metrics={"training": {"accuracy": rep.get("accuracy"),
                                             "macro_f1": (rep.get("macro avg") or {}).get("f1-score"),
                                             "split": metrics.get("split"), "note": metrics.get("note")}})
        db.add(run)
        db.flush()
        runs[key] = run
        if key == "cropland":
            names = {1: "Cropland", 2: "Non-cropland"}
            s, legend = categorical(names, "cropland_default")
        else:
            names = {i + 1: n for i, n in enumerate(metrics["class_names"])}
            s, legend = categorical(names)
        publish_raster_layer(db, local_path=need(DATA / f"results/aoi1_{key}.tif"), kind=kind,
                             name=model.name, group=group, aoi_id=aoi.id, run_id=run.id, style=s, legend=legend,
                             categorical=True, class_names=names, is_public=True)
    croptype_names = json.loads((DATA / "results/aoi1_croptype.metrics.json").read_text())["class_names"]

    print("6/7 Boundary layer (PMTiles) and field polygons in PostGIS")
    gj = json.loads(need(DATA / "results/aoi1_fields.geojson").read_text())
    colors = {n: QUALITATIVE[i % len(QUALITATIVE)] for i, n in enumerate(croptype_names)}
    style = {"type": "vector", "source_layer": "fields", "color_by": "class_name", "colors": colors,
             "outline": "#ffffff"}
    legend = [{"label": "Areas of one predicted crop, at least 25 pixels (about 2 ha). Derived from the crop-type layer."}]
    publish_pmtiles_layer(db, local_path=need(DATA / "results/aoi1_boundaries.pmtiles"), kind="boundary",
                          name="Field regions", group="Boundaries", aoi_id=aoi.id, run_id=runs["croptype"].id,
                          bounds_polygon=geom, style=style, legend=legend, is_public=True)
    for f in gj["features"]:
        g = shape(f["geometry"])
        if g.geom_type != "Polygon":
            continue
        db.add(Field(aoi_id=aoi.id, run_id=runs["croptype"].id, geom=from_shape(g, srid=4326),
                     attributes=f["properties"]))

    print("7/7 Commit")
    db.commit()
    print(f"Seeded. Sign in as '{DEMO_USER['username']}' / '{DEMO_USER['password']}'.")


if __name__ == "__main__":
    main()
