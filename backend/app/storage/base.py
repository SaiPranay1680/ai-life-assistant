from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from pathlib import Path
from typing import AsyncContextManager


def normalize_key(key: str) -> str:
    cleaned = key.replace("\\", "/").lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise ValueError("Invalid storage key.")
    return cleaned


class StorageBackend(ABC):
    """Logical keys are the same for quarantine and permanent objects."""

    @abstractmethod
    async def save_quarantine(self, key: str, chunks: AsyncIterable[bytes]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def promote(self, key: str) -> None:
        """Move a clean object from quarantine into permanent storage."""
        raise NotImplementedError

    @abstractmethod
    async def delete_quarantine(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_permanent(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists_permanent(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def materialize(self, key: str, *, location: str) -> tuple[Path, bool]:
        """Return (local_path, is_temporary). Caller must delete temporary files."""
        raise NotImplementedError

    @abstractmethod
    def open_for_read(self, key: str, *, location: str) -> AsyncContextManager[Path]:
        """Yield a local readable path. location is 'quarantine' or 'permanent'."""
        raise NotImplementedError

    @abstractmethod
    async def save_permanent_from_path(self, key: str, src_path: str) -> None:
        """Save a local file at src_path into permanent storage under the logical key."""
        raise NotImplementedError

    @abstractmethod
    async def cleanup_orphans(self, max_age_seconds: int) -> int:
        """Delete stale quarantine objects. Returns how many were removed."""
        raise NotImplementedError
