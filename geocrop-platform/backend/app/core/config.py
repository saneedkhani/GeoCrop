"""Application settings. Everything comes from environment variables (see .env.example)."""
import os
from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    jwt_secret: str = "change-me"
    jwt_expiry_hours: int = 24
    # When false, requests without a token act as the guest account (the seeded demo user),
    # so the app opens straight to the map. Set AUTH_REQUIRED=true for real deployments.
    auth_required: bool = False
    guest_username: str = "demo"
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    internal_token: str = "change-me-internal"

    database_url: str = "postgresql+psycopg://geocrop:geocrop@localhost:5432/geocrop"

    redis_url: str = "redis://localhost:6379/0"
    celery_always_eager: bool = False

    storage_backend: str = "s3"
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "geocrop"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    local_store_dir: str = "./data/store"

    tiles_internal_url: str = "http://localhost:8001"
    public_tile_base: str = "http://localhost:8080/tiles"
    public_pmtiles_base: str = "http://localhost:9000/geocrop"

    model_dirs: str = "model_registry/builtin"
    model_artifact_dir: str = "./data/models"
    max_upload_mb: int = 500

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def model_dir_list(self) -> list[str]:
        return [d.strip() for d in self.model_dirs.split(",") if d.strip()]

    @property
    def degraded_modes(self) -> list[str]:
        """Demo shortcuts that are switched on. Shown by /health and the UI."""
        modes = []
        if self.storage_backend == "local":
            modes.append("STORAGE_BACKEND=local (files on disk instead of MinIO/S3)")
        if not self.auth_required:
            modes.append("AUTH_REQUIRED=false (app opens without sign-in, as the guest account)")
        if self.celery_always_eager:
            modes.append("CELERY_ALWAYS_EAGER=true (jobs run inside the API, no Redis broker)")
        return modes


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_gdal_env(settings: Settings) -> None:
    """Let GDAL/rasterio read COGs straight from MinIO/S3 through /vsis3/."""
    if settings.storage_backend != "s3":
        return
    endpoint = urlparse(settings.s3_endpoint)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.s3_access_key)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.s3_secret_key)
    os.environ.setdefault("AWS_S3_ENDPOINT", endpoint.netloc)
    os.environ.setdefault("AWS_HTTPS", "YES" if endpoint.scheme == "https" else "NO")
    os.environ.setdefault("AWS_VIRTUAL_HOSTING", "FALSE")
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
