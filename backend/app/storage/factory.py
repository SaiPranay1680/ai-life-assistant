from functools import lru_cache

from ..core.config import settings
from .base import StorageBackend
from .local_storage import LocalStorage


@lru_cache
def get_storage() -> StorageBackend:
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "s3":
        from .s3_storage import S3Storage

        return S3Storage(
            region=settings.aws_region,
            quarantine_bucket=settings.aws_s3_quarantine_bucket,
            permanent_bucket=settings.aws_s3_permanent_bucket,
            quarantine_prefix=settings.aws_s3_quarantine_prefix,
            permanent_prefix=settings.aws_s3_permanent_prefix,
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
        )
    if backend != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {settings.storage_backend}")
    return LocalStorage(settings.quarantine_dir, settings.upload_dir)
