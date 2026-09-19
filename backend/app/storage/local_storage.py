import asyncio
import shutil
import time
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from .base import StorageBackend, normalize_key


class LocalStorage(StorageBackend):
    def __init__(self, quarantine_dir: str, permanent_dir: str) -> None:
        self.quarantine_root = Path(quarantine_dir)
        self.permanent_root = Path(permanent_dir)
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        self.permanent_root.mkdir(parents=True, exist_ok=True)

    def _path(self, root: Path, key: str) -> Path:
        relative = Path(normalize_key(key))
        path = (root / relative).resolve()
        root_resolved = root.resolve()
        if path != root_resolved and root_resolved not in path.parents:
            raise ValueError("Invalid storage key.")
        return path

    def _quarantine_path(self, key: str) -> Path:
        return self._path(self.quarantine_root, key)

    def _permanent_path(self, key: str) -> Path:
        return self._path(self.permanent_root, key)

    async def save_quarantine(self, key: str, chunks: AsyncIterable[bytes]) -> None:
        dest = self._quarantine_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with dest.open("wb") as handle:
                async for chunk in chunks:
                    handle.write(chunk)
        except Exception:
            dest.unlink(missing_ok=True)
            self._cleanup_empty_parents(dest, self.quarantine_root)
            raise

    async def promote(self, key: str) -> None:
        source = self._quarantine_path(key)
        dest = self._permanent_path(key)
        if not source.exists():
            raise FileNotFoundError("Quarantine object is missing.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.move, str(source), str(dest))
        self._cleanup_empty_parents(source, self.quarantine_root)

    async def delete_quarantine(self, key: str) -> None:
        path = self._quarantine_path(key)
        path.unlink(missing_ok=True)
        self._cleanup_empty_parents(path, self.quarantine_root)

    async def delete_permanent(self, key: str) -> None:
        path = self._permanent_path(key)
        path.unlink(missing_ok=True)
        self._cleanup_empty_parents(path, self.permanent_root)

    async def exists_permanent(self, key: str) -> bool:
        return self._permanent_path(key).exists()

    async def materialize(self, key: str, *, location: str) -> tuple[Path, bool]:
        if location == "quarantine":
            path = self._quarantine_path(key)
        elif location == "permanent":
            path = self._permanent_path(key)
        else:
            raise ValueError("location must be quarantine or permanent.")
        if not path.exists():
            raise FileNotFoundError("Stored object is missing.")
        return path, False

    @asynccontextmanager
    async def open_for_read(self, key: str, *, location: str) -> AsyncIterator[Path]:
        path, is_temp = await self.materialize(key, location=location)
        try:
            yield path
        finally:
            if is_temp:
                path.unlink(missing_ok=True)

    async def cleanup_orphans(self, max_age_seconds: int) -> int:
        if not self.quarantine_root.exists():
            return 0
        cutoff = time.time() - max_age_seconds
        removed = 0
        for path in self.quarantine_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
                    self._cleanup_empty_parents(path, self.quarantine_root)
                    removed += 1
            except OSError:
                continue
        return removed

    def _cleanup_empty_parents(self, path: Path, root: Path) -> None:
        parent = path.parent
        root_resolved = root.resolve()
        while parent != root_resolved and root_resolved in parent.resolve().parents:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
