"""Background jobs: ingest an upload, then run the requested models through the registry.

Every model output becomes a COG layer with statistics as soon as that model
finishes, so the map fills in progressively.
"""
from __future__ import annotations

import json
import tempfile
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from geoalchemy2.shape import from_shape
from sqlalchemy import select

from app.db.models import Aoi, Job, Model, ModelRun, SourceImage, Upload
from app.db.session import SessionLocal
from app.services import rasters
from app.services.layers import publish_raster_layer
from app.services.models_sync import artifact_dir, get_registry
from app.services.storage import get_storage
from app.workers.celery_app import celery_app
from model_registry.base import RunContext
from model_registry.colormaps import rgb, style_for_output
from model_registry.raster_io import to_cog
from model_registry.graph import PlanError

MAX_BANDS = 20


def _now():
    return datetime.now(timezone.utc)


def _set(db, job: Job, progress: float | None = None, message: str | None = None, step: str | None = None,
         step_status: str = "running", status: str | None = None, error: str | None = None) -> None:
    if progress is not None:
        job.progress = round(min(max(progress, 0.0), 1.0), 3)
    if message:
        job.message = message
    if step:
        steps = [dict(s) for s in (job.steps or [])]
        for s in steps:
            if s["name"] == step:
                s["status"] = step_status
                break
        else:
            steps.append({"name": step, "status": step_status})
        job.steps = steps
    if status:
        job.status = status
        if status in ("done", "failed"):
            job.finished_at = _now()
    if error:
        job.error = error
    db.commit()


@celery_app.task(name="geocrop.ingest")
def ingest_upload(job_id: str, upload_id: str, model_keys: list[str], location: str | None = None,
                  capture_date: str | None = None) -> None:
    db = SessionLocal()
    job = db.get(Job, uuid.UUID(job_id))
    upload = db.get(Upload, uuid.UUID(upload_id))
    storage = get_storage()
    try:
        _set(db, job, 0.05, "Checking the image", "Validate image", status="running")
        with tempfile.TemporaryDirectory() as tmp:
            raw = storage.download(upload.storage_key, Path(tmp) / "original.tif")
            try:
                info = rasters.describe(str(raw))
            except Exception:
                raise ValueError("The file could not be read as a GeoTIFF. Upload a georeferenced .tif image.")
            if not info["crs"]:
                raise ValueError("The image has no coordinate reference system, so it cannot be placed on the map.")
            if not 3 <= info["band_count"] <= MAX_BANDS:
                raise ValueError(f"The image has {info['band_count']} bands. Expected a Sentinel-2 stack "
                                 "(B2, B3, B4, B8, B11, B12 and optionally NDVI).")
            _set(db, job, 0.12, "Image is valid", "Validate image", "done")

            _set(db, job, 0.15, "Aligning to the model grid (EPSG:5070, 30 m)", "Convert to cloud-optimized GeoTIFF")
            pre = rasters.preprocess_to_model_grid(str(raw), Path(tmp) / "pre.tif")
            cog = to_cog(pre, Path(tmp) / "image.cog.tif", categorical=False)
            footprint = rasters.footprint_wgs84(str(cog))
            aoi = Aoi(owner_id=upload.user_id, name=(location or "").strip() or f"Upload: {upload.filename}",
                      geom=from_shape(footprint, srid=4326))
            db.add(aoi)
            db.flush()
            style, legend = rgb([3, 2, 1], [0, 2000])
            layer = publish_raster_layer(db, local_path=cog, kind="imagery", name=f"Image: {upload.filename}",
                                         group="Imagery", aoi_id=aoi.id, run_id=None, style=style, legend=legend,
                                         categorical=False, already_cog=True)
            src = SourceImage(aoi_id=aoi.id, upload_id=upload.id, kind="sentinel2_upload", captured_on=capture_date or None,
                              storage_key=layer.storage_key, bounds=from_shape(footprint, srid=4326),
                              crs_original=info["crs"], band_count=info["band_count"], resolution_m=30.0)
            db.add(src)
            upload.aoi_id, upload.status = aoi.id, "ingested"
            db.commit()
            _set(db, job, 0.25, "Image ready", "Convert to cloud-optimized GeoTIFF", "done")
        run_pipeline.delay(job_id, str(src.id), model_keys)
    except Exception as e:
        upload.status = "failed"
        _set(db, job, message="Ingest failed", status="failed", error=str(e) or traceback.format_exc(limit=1))
    finally:
        db.close()


@celery_app.task(name="geocrop.run_pipeline")
def run_pipeline(job_id: str, source_image_id: str, model_keys: list[str], start: float = 0.25) -> None:
    db = SessionLocal()
    job = db.get(Job, uuid.UUID(job_id))
    src = db.get(SourceImage, uuid.UUID(source_image_id))
    registry, storage = get_registry(), get_storage()
    try:
        try:
            order = registry.plan(model_keys)
        except PlanError as e:
            raise ValueError(str(e))
        _set(db, job, start, f"Running {len(order)} model(s): {', '.join(order)}", status="running")
        span = (1.0 - start) / max(len(order), 1)
        with tempfile.TemporaryDirectory() as tmp:
            image = storage.download(src.storage_key, Path(tmp) / "image.tif")
            upstream: dict[str, str] = {}
            for i, key in enumerate(order):
                reg = registry.get(key)
                step = f"Run {reg.manifest['name']}"
                model_row = db.scalar(select(Model).where(Model.key == key))
                run = ModelRun(aoi_id=src.aoi_id, model_id=model_row.id, source_image_id=src.id, status="running",
                               started_at=_now(), params={"requested": model_keys})
                db.add(run)
                db.commit()
                base = start + i * span
                out_dir = Path(tmp) / key
                out_dir.mkdir()

                def progress(fraction: float, message: str, _base=base, _step=step):
                    _set(db, job, _base + fraction * span * 0.8, message, _step)

                ctx = RunContext(run_id=str(run.id), image_path=str(image), upstream=dict(upstream),
                                 out_dir=out_dir, artifact_dir=artifact_dir(), manifest=reg.manifest,
                                 progress=progress)
                task = reg.create()
                _set(db, job, base, f"Starting {reg.manifest['name']}", step)
                problems = task.validate(ctx)
                if problems:
                    run.status, run.error, run.finished_at = "failed", " ".join(problems), _now()
                    db.commit()
                    raise ValueError(f"{reg.manifest['name']}: {' '.join(problems)}")
                result = task.run(ctx)
                if result.status == "not_available":
                    run.status, run.error, run.finished_at = "not_available", result.message, _now()
                    _set(db, job, base + span, result.message, step, "skipped")
                    continue
                outputs = {o["kind"]: o for o in reg.manifest.get("outputs", [])}
                for kind, path in result.files.items():
                    spec = outputs.get(kind, {"kind": kind})
                    style, legend = style_for_output(spec, result.class_names)
                    publish_raster_layer(db, local_path=path, kind=kind, group=spec.get("group", "Results"),
                                         name=f"{reg.manifest['name']}", aoi_id=src.aoi_id, run_id=run.id,
                                         style=style, legend=legend, categorical=bool(result.class_names),
                                         class_names=result.class_names)
                    upstream[kind] = str(path)
                run.metrics = {"run": result.metrics, "training": _training_metrics(reg.manifest)}
                run.status, run.finished_at = "done", _now()
                db.commit()
                _set(db, job, base + span, f"{reg.manifest['name']} finished", step, "done")
        _set(db, job, 1.0, "All results are on the map", "Publish layers", "done", status="done")
    except Exception as e:
        _set(db, job, message="Model run failed", status="failed", error=str(e))
    finally:
        db.close()


def _training_metrics(manifest: dict) -> dict:
    """Summary of stored held-out metrics for this model, if the training run saved them."""
    name = (manifest.get("training") or {}).get("metrics_file")
    if not name:
        return {}
    path = artifact_dir() / name
    if not path.exists():
        return {}
    m = json.loads(path.read_text())
    rep = m.get("report", {})
    return {"accuracy": rep.get("accuracy"), "macro_f1": (rep.get("macro avg") or {}).get("f1-score"),
            "split": m.get("split"), "note": m.get("note")}
