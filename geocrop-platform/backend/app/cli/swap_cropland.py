"""One-off migration: the LSTM becomes the cropland model; the previous Random Forest is kept as a backup.

    python -m app.cli.swap_cropland

1. Registers both plug-ins (`cropland` = LSTM, `cropland_rf_legacy` = previous RF, disabled).
2. Credits every existing cropland result (they were all made by the RF) to the backup model and
   renames those layers, so nothing produced by the old model is shown under the new model's name.
3. Adds the AOI 1 monthly composite (77 bands, April-October 2022) as a source image of AOI 1, so the
   new model can be run on AOI 1 from the Analyze pop-up ("Re-analyse an existing image").
Safe to run more than once.
"""
from pathlib import Path

from sqlalchemy import select

from app.db.models import Aoi, Layer, Model, ModelRun, SourceImage
from app.db.session import SessionLocal
import tempfile

from app.services.layers import publish_source_image
from app.services.models_sync import sync_models
from model_registry.raster_io import to_cog

AOI_NAME = "AOI 1: Columbia Basin, Washington"
COMPOSITE = Path("/data/raw/aoi1_composite_2022.tif")
MONTHLY_KIND = "sentinel2_monthly_2022"


def main() -> None:
    db = SessionLocal()
    errors = sync_models(db)
    for e in errors:
        print("registry warning:", e)
    new = db.scalar(select(Model).where(Model.key == "cropland"))
    old = db.scalar(select(Model).where(Model.key == "cropland_rf_legacy"))
    if not new or not old:
        raise SystemExit("Both cropland plug-ins must be registered (check the registry warnings above).")

    moved = 0
    for run in db.scalars(select(ModelRun).where(ModelRun.model_id == new.id)).all():
        split = ((run.metrics or {}).get("training") or {}).get("split") or ""
        if split.startswith("leave-one-area-out"):
            continue                                   # produced by the LSTM
        run.model_id = old.id
        for layer in db.scalars(select(Layer).where(Layer.run_id == run.id)).all():
            layer.name = old.name
        moved += 1
    db.commit()
    print(f"Cropland runs credited to the previous model (backup): {moved}")

    aoi = db.scalar(select(Aoi).where(Aoi.name == AOI_NAME))
    if aoi and COMPOSITE.exists():
        if db.scalar(select(SourceImage).where(SourceImage.aoi_id == aoi.id, SourceImage.kind == MONTHLY_KIND)):
            print("AOI 1 monthly composite already registered.")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                cog = to_cog(COMPOSITE, Path(tmp) / "composite.cog.tif", categorical=False)
                layer, key = publish_source_image(db, cog_path=cog, aoi_id=aoi.id, band_count=77, is_public=True,
                                                  name="Sentinel-2 monthly composite 2022 (July shown)")
            db.add(SourceImage(aoi_id=aoi.id, kind=MONTHLY_KIND, storage_key=key, bounds=layer.bounds,
                               crs_original="EPSG:5070", band_count=77, resolution_m=30.0,
                               captured_on="2022 Apr-Oct"))
            db.commit()
            print("AOI 1 monthly composite registered as a source image.")
    elif not COMPOSITE.exists():
        print(f"{COMPOSITE} not found; build it with tools/build_composite_stac.py to run the LSTM on AOI 1.")
    db.close()


if __name__ == "__main__":
    main()
