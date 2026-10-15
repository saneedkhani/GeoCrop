"""Keep the `model` table in step with the model registry folders."""
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Model
from model_registry.registry import Registry


@lru_cache
def get_registry() -> Registry:
    return Registry(get_settings().model_dir_list)


def sync_models(db: Session) -> list[str]:
    """Upsert one row per registered model. Returns registry load errors (if any)."""
    reg = get_registry()
    reg.reload()
    for m in reg.list():
        row = db.scalar(select(Model).where(Model.key == m.key))
        if row is None:
            row = Model(key=m.key)
            db.add(row)
        mf = m.manifest
        row.task, row.version, row.name = mf["task"], str(mf["version"]), mf["name"]
        row.status, row.manifest, row.enabled = mf["status"], mf, m.enabled
    db.commit()
    return reg.errors


def artifact_dir() -> Path:
    return Path(get_settings().model_artifact_dir)
