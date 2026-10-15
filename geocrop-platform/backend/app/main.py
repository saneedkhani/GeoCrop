import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router
from app.core.config import configure_gdal_env, get_settings
from app.db.session import SessionLocal
from app.services.models_sync import sync_models

log = logging.getLogger("geocrop")
settings = get_settings()
configure_gdal_env(settings)

app = FastAPI(title="GeoCrop API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
              description="Catalog, models, statistics and processing jobs for GeoCrop.")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def _startup() -> None:
    db = SessionLocal()
    try:
        errors = sync_models(db)
        for e in errors:
            log.warning("Model registry: %s", e)
    except Exception as e:  # DB not migrated yet: the API still starts and /health reports it
        log.warning("Model sync skipped: %s", e)
    finally:
        db.close()
