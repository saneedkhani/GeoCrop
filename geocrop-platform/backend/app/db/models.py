"""Database schema (PostgreSQL + PostGIS).

Free-form fields (layer kind, style, legend, model manifest, metrics) are JSONB
or plain strings on purpose: a new model output never needs a schema change.
Geometries are EPSG:4326.
"""
import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, Uuid)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Aoi(Base):
    __tablename__ = "aoi"
    id: Mapped[uuid.UUID] = pk()
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    geom = mapped_column(Geometry("POLYGON", srid=4326))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Upload(Base):
    __tablename__ = "upload"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    aoi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aoi.id"))
    filename: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceImage(Base):
    __tablename__ = "source_image"
    id: Mapped[uuid.UUID] = pk()
    aoi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aoi.id"))
    upload_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("upload.id"))
    kind: Mapped[str] = mapped_column(String(64))
    captured_on: Mapped[str | None] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(String(1024))
    bounds = mapped_column(Geometry("POLYGON", srid=4326))
    crs_original: Mapped[str | None] = mapped_column(String(64))
    band_count: Mapped[int] = mapped_column(Integer)
    resolution_m: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Model(Base):
    __tablename__ = "model"
    id: Mapped[uuid.UUID] = pk()
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    task: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    manifest: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ModelRun(Base):
    __tablename__ = "model_run"
    id: Mapped[uuid.UUID] = pk()
    aoi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aoi.id"), index=True)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model.id"))
    source_image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_image.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    model: Mapped[Model] = relationship()


class Layer(Base):
    __tablename__ = "map_layer"
    __table_args__ = (Index("ix_layer_aoi_kind", "aoi_id", "kind"),)
    id: Mapped[uuid.UUID] = pk()
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_run.id"), index=True)
    aoi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aoi.id"))
    kind: Mapped[str] = mapped_column(String(64))
    group: Mapped[str] = mapped_column(String(64), default="Results")
    name: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(16))
    storage_key: Mapped[str] = mapped_column(String(1024))
    bounds = mapped_column(Geometry("POLYGON", srid=4326))
    min_zoom: Mapped[int] = mapped_column(Integer, default=0)
    max_zoom: Mapped[int] = mapped_column(Integer, default=22)
    nodata: Mapped[float | None] = mapped_column(Float)
    dtype: Mapped[str | None] = mapped_column(String(32))
    style: Mapped[dict] = mapped_column(JSONB, default=dict)
    legend: Mapped[list] = mapped_column(JSONB, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ZonalStat(Base):
    __tablename__ = "zonal_stat"
    __table_args__ = (Index("ix_zonal_layer_zone", "layer_id", "zone_type", "zone_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    layer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("map_layer.id", ondelete="CASCADE"))
    zone_type: Mapped[str] = mapped_column(String(32), default="aoi")
    zone_id: Mapped[str] = mapped_column(String(128))
    class_code: Mapped[int | None] = mapped_column(Integer)
    class_name: Mapped[str | None] = mapped_column(String(255))
    pixel_count: Mapped[int] = mapped_column(BigInteger, default=0)
    area_ha: Mapped[float] = mapped_column(Float, default=0.0)
    mean: Mapped[float | None] = mapped_column(Float)
    min: Mapped[float | None] = mapped_column(Float)
    max: Mapped[float | None] = mapped_column(Float)


class Field(Base):
    __tablename__ = "field"
    id: Mapped[uuid.UUID] = pk()
    aoi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aoi.id"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_run.id"))
    geom = mapped_column(Geometry("POLYGON", srid=4326))
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)


class Job(Base):
    __tablename__ = "job"
    id: Mapped[uuid.UUID] = pk()
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSONB, default=list)
    upload_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("upload.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
