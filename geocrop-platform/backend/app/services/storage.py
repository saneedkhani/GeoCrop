"""Object storage behind one interface: S3/MinIO in the full stack, local disk as a flagged fallback."""
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, configure_gdal_env, get_settings


class Storage(ABC):
    @abstractmethod
    def put_file(self, local_path: Path | str, key: str, content_type: str | None = None) -> None: ...

    @abstractmethod
    def download(self, key: str, dest: Path) -> Path: ...

    @abstractmethod
    def gdal_path(self, key: str) -> str:
        """A path rasterio/GDAL can open directly (local path or /vsis3/...)."""

    @abstractmethod
    def public_url(self, key: str) -> str: ...

    @abstractmethod
    def signed_put_url(self, key: str, expires: int = 3600) -> str | None: ...

    @abstractmethod
    def healthy(self) -> bool: ...


class LocalStorage(Storage):
    def __init__(self, settings: Settings):
        self.root = Path(settings.local_store_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base = settings.public_pmtiles_base

    def _p(self, key: str) -> Path:
        return self.root / key

    def put_file(self, local_path, key, content_type=None):
        dst = self._p(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dst)

    def download(self, key, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._p(key), dest)
        return dest

    def gdal_path(self, key):
        return str(self._p(key))

    def public_url(self, key):
        return f"{self.public_base}/{key}"

    def signed_put_url(self, key, expires=3600):
        return None  # browser uploads go through the API multipart route instead

    def healthy(self):
        return self.root.exists()


class S3Storage(Storage):
    def __init__(self, settings: Settings):
        import boto3
        from botocore.config import Config

        cfg = Config(signature_version="s3v4", s3={"addressing_style": "path"})
        common = dict(aws_access_key_id=settings.s3_access_key, aws_secret_access_key=settings.s3_secret_key,
                      region_name="us-east-1", config=cfg)
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint, **common)
        # Signed URLs must use the host the browser can reach.
        self.signer = boto3.client("s3", endpoint_url=settings.s3_public_endpoint, **common)
        self.bucket = settings.s3_bucket
        self.public_base = settings.public_pmtiles_base
        configure_gdal_env(settings)

    def put_file(self, local_path, key, content_type=None):
        extra = {"ContentType": content_type} if content_type else None
        self.client.upload_file(str(local_path), self.bucket, key, ExtraArgs=extra)

    def download(self, key, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(dest))
        return dest

    def gdal_path(self, key):
        return f"/vsis3/{self.bucket}/{key}"

    def public_url(self, key):
        return f"{self.public_base}/{key}"

    def signed_put_url(self, key, expires=3600):
        return self.signer.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires)

    def healthy(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    return LocalStorage(s) if s.storage_backend == "local" else S3Storage(s)
