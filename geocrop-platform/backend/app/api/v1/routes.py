"""REST API v1. Every route returns plain-language errors."""
from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from geoalchemy2.shape import to_shape
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_token, current_user, hash_password, internal_only, verify_password
from app.db.models import Aoi, Field, Job, Layer, Model, ModelRun, SourceImage, Upload, User, ZonalStat
from app.db.session import get_db
from app.schemas import CompleteIn, LoginIn, RunIn, SignupIn, UploadIn
from app.services import rasters
from app.services.layers import layer_to_dict
from app.services.models_sync import artifact_dir, get_registry
from app.services.storage import get_storage

router = APIRouter()


def _uuid(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(404, f"{what} not found.")


def _visible_layers(user: User):
    return (select(Layer).join(Aoi, Layer.aoi_id == Aoi.id, isouter=True)
            .where(or_(Layer.is_public.is_(True), Aoi.owner_id == user.id)))


# ---------------------------------------------------------------- health
@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    s = get_settings()
    services = {}
    try:
        ver = db.execute(text("select postgis_lib_version()")).scalar()
        services["database"] = {"ok": True, "detail": f"PostgreSQL + PostGIS {ver}"}
    except Exception as e:
        services["database"] = {"ok": False, "detail": str(e)[:200]}
    if s.celery_always_eager:
        services["redis"] = {"ok": True, "detail": "not used (eager mode)"}
    else:
        try:
            import redis
            redis.from_url(s.redis_url, socket_timeout=2).ping()
            services["redis"] = {"ok": True, "detail": "Celery broker reachable"}
        except Exception as e:
            services["redis"] = {"ok": False, "detail": str(e)[:200]}
    services["storage"] = {"ok": get_storage().healthy(), "detail": s.storage_backend}
    try:
        r = httpx.get(f"{s.tiles_internal_url}/healthz", timeout=2)
        services["tiles"] = {"ok": r.status_code == 200, "detail": "TiTiler / rio-tiler"}
    except Exception as e:
        services["tiles"] = {"ok": False, "detail": str(e)[:200]}
    reg = get_registry()
    services["models"] = {"ok": not reg.errors, "detail": f"{len(reg.models)} registered",
                          "errors": reg.errors}
    ok = all(v["ok"] for v in services.values())
    return {"status": "ok" if ok else "degraded", "services": services, "degraded_modes": s.degraded_modes}


# ---------------------------------------------------------------- auth
def _user_dict(u: User) -> dict:
    return {"id": str(u.id), "email": u.email, "username": u.username, "role": u.role}


@router.post("/auth/signup", tags=["auth"])
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if not (body.email and body.username and body.password):
        raise HTTPException(400, "Fill in all fields.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords do not match.")
    if len(body.password) < 8:
        raise HTTPException(400, "Use at least 8 characters for the password.")
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(400, "That username is already taken.")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(400, "An account with that email already exists.")
    u = User(email=body.email.strip(), username=body.username.strip(), password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    return {"token": create_token(u.id), "user": _user_dict(u)}


@router.post("/auth/login", tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(or_(User.username == body.username, User.email == body.username)))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid username or password.")
    return {"token": create_token(u.id), "user": _user_dict(u)}


@router.get("/auth/me", tags=["auth"])
def me(user: User = Depends(current_user)):
    return _user_dict(user)


# ---------------------------------------------------------------- aois
@router.get("/aois", tags=["catalog"])
def list_aois(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Aoi).where(or_(Aoi.is_public.is_(True), Aoi.owner_id == user.id))
                      .order_by(Aoi.created_at)).all()
    return [{"id": str(a.id), "name": a.name, "bounds": list(to_shape(a.geom).bounds) if a.geom is not None else None,
             "is_public": a.is_public} for a in rows]


# ---------------------------------------------------------------- models
def _class_scores(manifest: dict) -> list[dict]:
    """Per-class held-out precision/recall/F1 from the training metrics file, if saved."""
    name = (manifest.get("training") or {}).get("metrics_file")
    path = artifact_dir() / name if name else None
    if not path or not path.exists():
        return []
    report = json.loads(path.read_text()).get("report", {})
    skip = {"accuracy", "macro avg", "weighted avg"}
    return [{"label": k, "precision": round(v["precision"], 3), "recall": round(v["recall"], 3),
             "f1": round(v["f1-score"], 3), "support": int(v["support"])}
            for k, v in report.items() if k not in skip and isinstance(v, dict)]


@router.get("/models", tags=["models"])
def list_models(db: Session = Depends(get_db)):
    out = []
    for m in db.scalars(select(Model).order_by(Model.key)).all():
        mf = m.manifest or {}
        last = db.scalar(select(ModelRun).where(ModelRun.model_id == m.id, ModelRun.status == "done")
                         .order_by(ModelRun.finished_at.desc()))
        out.append({"key": m.key, "name": m.name, "task": m.task, "version": m.version, "status": m.status,
                    "enabled": m.enabled, "requires": mf.get("requires", []),
                    "outputs": [o["kind"] for o in mf.get("outputs", [])],
                    "input_bands": (mf.get("input_spec") or {}).get("bands"),
                    "valid_regions": mf.get("valid_regions", []), "notes": mf.get("notes"),
                    "training": mf.get("training"),
                    "last_run_metrics": (last.metrics or {}).get("training") if last else None,
                    "class_scores": _class_scores(mf)})
    return {"models": out, "registry_errors": get_registry().errors}


# ---------------------------------------------------------------- layers
@router.get("/layers", tags=["catalog"])
def list_layers(aoi: str | None = None, kind: str | None = None, run: str | None = None,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = _visible_layers(user)
    if aoi:
        q = q.where(Layer.aoi_id == _uuid(aoi, "Area"))
    if kind:
        q = q.where(Layer.kind == kind)
    if run:
        q = q.where(Layer.run_id == _uuid(run, "Run"))
    return [layer_to_dict(l) for l in db.scalars(q.order_by(Layer.created_at)).all()]


@router.get("/layers/{layer_id}", tags=["catalog"])
def get_layer(layer_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    layer = db.scalar(_visible_layers(user).where(Layer.id == _uuid(layer_id, "Layer")))
    if not layer:
        raise HTTPException(404, "Layer not found.")
    return layer_to_dict(layer)


# ---------------------------------------------------------------- fields
@router.get("/fields", tags=["catalog"])
def list_fields(aoi: str | None = None, q: str | None = None, limit: int = Query(200, le=1000),
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Field regions with their crop and area, largest first (for the map's field list)."""
    qry = (select(Field).join(Aoi, Field.aoi_id == Aoi.id)
           .where(or_(Aoi.is_public.is_(True), Aoi.owner_id == user.id)))
    if aoi:
        qry = qry.where(Field.aoi_id == _uuid(aoi, "Area"))
    if q:
        qry = qry.where(Field.attributes["class_name"].astext.ilike(f"%{q}%"))
    rows = db.scalars(qry.order_by(Field.attributes["area_ha"].as_float().desc()).limit(limit)).all()
    return [{"id": str(f.id), "field_id": f.attributes.get("field_id"), "class_name": f.attributes.get("class_name"),
             "area_ha": f.attributes.get("area_ha"), "bbox": list(to_shape(f.geom).bounds)} for f in rows]


# ---------------------------------------------------------------- point + stats
@router.get("/point", tags=["analysis"])
def point(lng: float, lat: float, layers: str = Query(..., description="Comma-separated layer ids"),
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    storage = get_storage()
    results = []
    for lid in [x for x in layers.split(",") if x][:12]:
        layer = db.scalar(_visible_layers(user).where(Layer.id == _uuid(lid, "Layer")))
        if not layer or layer.format != "cog":
            continue
        try:
            value = rasters.sample(storage.gdal_path(layer.storage_key), lng, lat)
        except Exception:
            value = None
        label = None
        if value is not None and layer.style.get("type") == "categorical":
            label = next((e["label"] for e in layer.legend if e.get("code") == int(value)), None)
        results.append({"layer_id": str(layer.id), "name": layer.name, "kind": layer.kind,
                        "value": value, "label": label})
    return {"lng": lng, "lat": lat, "values": results}


@router.get("/stats", tags=["analysis"])
def stats(layer: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lyr = db.scalar(_visible_layers(user).where(Layer.id == _uuid(layer, "Layer")))
    if not lyr:
        raise HTTPException(404, "Layer not found.")
    rows = db.scalars(select(ZonalStat).where(ZonalStat.layer_id == lyr.id)
                      .order_by(ZonalStat.area_ha.desc())).all()
    total = sum(r.area_ha for r in rows) or 0.0
    colors = {e.get("code"): e.get("color") for e in lyr.legend or []}
    return {"layer": layer_to_dict(lyr), "total_area_ha": round(total, 2),
            "rows": [{"class_code": r.class_code, "class_name": r.class_name, "pixel_count": r.pixel_count,
                      "area_ha": r.area_ha, "pct": round(100 * r.area_ha / total, 2) if total else None,
                      "mean": r.mean, "min": r.min, "max": r.max, "color": colors.get(r.class_code)}
                     for r in rows]}


# ---------------------------------------------------------------- uploads, runs, jobs
def _job_dict(j: Job) -> dict:
    return {"id": str(j.id), "kind": j.kind, "status": j.status, "progress": j.progress, "message": j.message,
            "error": j.error, "steps": j.steps or [], "upload_id": str(j.upload_id) if j.upload_id else None,
            "created_at": j.created_at.isoformat(), "finished_at": j.finished_at.isoformat() if j.finished_at else None}


@router.post("/uploads", tags=["pipeline"])
def create_upload(body: UploadIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = get_settings()
    if not body.filename.lower().endswith((".tif", ".tiff")):
        raise HTTPException(400, "Upload a GeoTIFF (.tif or .tiff).")
    if body.size_bytes and body.size_bytes > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"The file is larger than the {s.max_upload_mb} MB limit.")
    up = Upload(user_id=user.id, filename=body.filename, size_bytes=body.size_bytes, storage_key="")
    db.add(up)
    db.flush()
    up.storage_key = f"raw/{up.id}/original.tif"
    db.commit()
    return {"id": str(up.id), "upload_url": get_storage().signed_put_url(up.storage_key), "method": "PUT",
            "fallback_url": f"/api/v1/uploads/{up.id}/file"}


@router.post("/uploads/{upload_id}/file", tags=["pipeline"])
def upload_file(upload_id: str, file: UploadFile = File(...), user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    up = db.get(Upload, _uuid(upload_id, "Upload"))
    if not up or up.user_id != user.id:
        raise HTTPException(404, "Upload not found.")
    with tempfile.NamedTemporaryFile(suffix=".tif") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp.flush()
        get_storage().put_file(tmp.name, up.storage_key, "image/tiff")
    up.status = "uploaded"
    db.commit()
    return {"ok": True}


@router.post("/uploads/{upload_id}/complete", tags=["pipeline"])
def complete_upload(upload_id: str, body: CompleteIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    from app.workers.tasks import ingest_upload
    up = db.get(Upload, _uuid(upload_id, "Upload"))
    if not up or up.user_id != user.id:
        raise HTTPException(404, "Upload not found.")
    try:
        order = get_registry().plan(body.model_keys)
    except ValueError as e:
        raise HTTPException(400, str(e))
    steps = [{"name": "Upload received", "status": "done"}, {"name": "Validate image", "status": "pending"},
             {"name": "Convert to cloud-optimized GeoTIFF", "status": "pending"}]
    steps += [{"name": f"Run {get_registry().get(k).manifest['name']}", "status": "pending"} for k in order]
    steps.append({"name": "Publish layers", "status": "pending"})
    job = Job(kind="upload_pipeline", upload_id=up.id, user_id=user.id, steps=steps, message="Queued")
    up.status = "queued"
    db.add(job)
    db.commit()
    ingest_upload.delay(str(job.id), str(up.id), body.model_keys, body.location, body.capture_date)
    return _job_dict(job)


@router.post("/runs", tags=["pipeline"])
def start_run(body: RunIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.workers.tasks import run_pipeline
    src = db.get(SourceImage, _uuid(body.source_image_id, "Image"))
    if not src:
        raise HTTPException(404, "Image not found.")
    try:
        order = get_registry().plan(body.model_keys)
    except ValueError as e:
        raise HTTPException(400, str(e))
    steps = [{"name": f"Run {get_registry().get(k).manifest['name']}", "status": "pending"} for k in order]
    job = Job(kind="model_run", user_id=user.id, steps=steps + [{"name": "Publish layers", "status": "pending"}])
    db.add(job)
    db.commit()
    run_pipeline.delay(str(job.id), str(src.id), body.model_keys, 0.0)
    return _job_dict(job)


@router.get("/runs", tags=["pipeline"])
def list_runs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(ModelRun, Model.key, Model.name).join(Model)
                      .join(Aoi, ModelRun.aoi_id == Aoi.id, isouter=True)
                      .where(or_(Aoi.is_public.is_(True), Aoi.owner_id == user.id))
                      .order_by(ModelRun.created_at.desc()).limit(100)).all()
    return [{"id": str(r.id), "model_key": k, "model_name": n, "status": r.status, "error": r.error,
             "aoi_id": str(r.aoi_id) if r.aoi_id else None, "metrics": r.metrics,
             "source_image_id": str(r.source_image_id) if r.source_image_id else None,
             "started_at": r.started_at.isoformat() if r.started_at else None,
             "finished_at": r.finished_at.isoformat() if r.finished_at else None} for r, k, n in rows]


@router.get("/sources", tags=["pipeline"])
def list_sources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(SourceImage).join(Aoi, SourceImage.aoi_id == Aoi.id)
                      .where(or_(Aoi.is_public.is_(True), Aoi.owner_id == user.id))
                      .order_by(SourceImage.created_at.desc())).all()
    return [{"id": str(s.id), "aoi_id": str(s.aoi_id), "kind": s.kind, "band_count": s.band_count,
             "created_at": s.created_at.isoformat()} for s in rows]


@router.get("/jobs", tags=["pipeline"])
def list_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(20)).all()
    return [_job_dict(j) for j in rows]


@router.get("/jobs/{job_id}", tags=["pipeline"])
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(Job, _uuid(job_id, "Job"))
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found.")
    return _job_dict(job)


# ---------------------------------------------------------------- internal (tile service)
@router.get("/internal/layers/{layer_id}", tags=["internal"], dependencies=[Depends(internal_only)],
            include_in_schema=False)
def internal_layer(layer_id: str, db: Session = Depends(get_db)):
    layer = db.get(Layer, _uuid(layer_id, "Layer"))
    if not layer:
        raise HTTPException(404, "Layer not found.")
    return {"id": str(layer.id), "format": layer.format, "version": layer.version, "nodata": layer.nodata,
            "dtype": layer.dtype, "style": layer.style, "path": get_storage().gdal_path(layer.storage_key)}
