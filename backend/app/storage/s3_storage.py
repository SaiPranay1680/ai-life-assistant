import asyncio
import tempfile
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import boto3
from botocore.exceptions import ClientError

from .base import StorageBackend, normalize_key


class S3Storage(StorageBackend):
    def __init__(
        self,
        *,
        region: str,
        quarantine_bucket: str,
        permanent_bucket: str,
        quarantine_prefix: str = "",
        permanent_prefix: str = "",
        access_key_id: str = "",
        secret_access_key: str = "",
    ) -> None:
        if not quarantine_bucket or not permanent_bucket:
            raise RuntimeError("S3 storage requires quarantine and permanent bucket names.")

        kwargs: dict[str, Any] = {"region_name": region}
        if access_key_id and secret_access_key:
            kwargs["aws_access_key_id"] = access_key_id
            kwargs["aws_secret_access_key"] = secret_access_key
        self._client = boto3.client("s3", **kwargs)
        self.quarantine_bucket = quarantine_bucket
        self.permanent_bucket = permanent_bucket
        self.quarantine_prefix = quarantine_prefix.strip("/")
        self.permanent_prefix = permanent_prefix.strip("/")

    def _object_key(self, key: str, prefix: str) -> str:
        logical = normalize_key(key)
        if not prefix:
            return logical
        return f"{prefix}/{logical}"

    def _quarantine_key(self, key: str) -> str:
        return self._object_key(key, self.quarantine_prefix)

    def _permanent_key(self, key: str) -> str:
        return self._object_key(key, self.permanent_prefix)

    async def save_quarantine(self, key: str, chunks: AsyncIterable[bytes]) -> None:
        object_key = self._quarantine_key(key)
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            temp_path = Path(handle.name)
            try:
                async for chunk in chunks:
                    handle.write(chunk)
            except Exception:
                handle.close()
                temp_path.unlink(missing_ok=True)
                raise
        try:
            await asyncio.to_thread(
                self._client.upload_file,
                str(temp_path),
                self.quarantine_bucket,
                object_key,
            )
        finally:
            temp_path.unlink(missing_ok=True)

    async def promote(self, key: str) -> None:
        source_key = self._quarantine_key(key)
        dest_key = self._permanent_key(key)
        copy_source = {"Bucket": self.quarantine_bucket, "Key": source_key}

        def _copy_and_delete() -> None:
            self._client.copy_object(
                Bucket=self.permanent_bucket,
                Key=dest_key,
                CopySource=copy_source,
            )
            self._client.delete_object(Bucket=self.quarantine_bucket, Key=source_key)

        await asyncio.to_thread(_copy_and_delete)

    async def delete_quarantine(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self.quarantine_bucket,
            Key=self._quarantine_key(key),
        )

    async def delete_permanent(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self.permanent_bucket,
            Key=self._permanent_key(key),
        )

    async def exists_permanent(self, key: str) -> bool:
        def _exists() -> bool:
            try:
                self._client.head_object(Bucket=self.permanent_bucket, Key=self._permanent_key(key))
                return True
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise

        return await asyncio.to_thread(_exists)

    async def materialize(self, key: str, *, location: str) -> tuple[Path, bool]:
        if location == "quarantine":
            bucket, object_key = self.quarantine_bucket, self._quarantine_key(key)
        elif location == "permanent":
            bucket, object_key = self.permanent_bucket, self._permanent_key(key)
        else:
            raise ValueError("location must be quarantine or permanent.")
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            await asyncio.to_thread(self._client.download_file, bucket, object_key, str(temp_path))
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return temp_path, True

    @asynccontextmanager
    async def open_for_read(self, key: str, *, location: str) -> AsyncIterator[Path]:
        path, is_temp = await self.materialize(key, location=location)
        try:
            yield path
        finally:
            if is_temp:
                path.unlink(missing_ok=True)

    async def cleanup_orphans(self, max_age_seconds: int) -> int:
        prefix = f"{self.quarantine_prefix}/" if self.quarantine_prefix else ""
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds

        def _cleanup() -> int:
            removed = 0
            paginator = self._client.get_paginator("list_objects_v2")
            kwargs = {"Bucket": self.quarantine_bucket}
            if prefix:
                kwargs["Prefix"] = prefix
            for page in paginator.paginate(**kwargs):
                for obj in page.get("Contents", []):
                    last_modified = obj.get("LastModified")
                    if last_modified is None:
                        continue
                    stamp = last_modified.timestamp()
                    if stamp < cutoff:
                        self._client.delete_object(Bucket=self.quarantine_bucket, Key=obj["Key"])
                        removed += 1
            return removed

        return await asyncio.to_thread(_cleanup)
