import asyncio
from functools import lru_cache
from pathlib import Path

from ..core.config import settings
from .clamav import ClamAVClient, ScannerUnavailable
from .file_checks import ScanResult, inspect_file


class MalwareScanner:
    def __init__(self, client: ClamAVClient, required: bool) -> None:
        self._client = client
        self.required = required

    async def health_check(self) -> bool:
        return await asyncio.to_thread(self._client.ping)

    async def scan(self, path: Path) -> ScanResult:
        heuristic = await asyncio.to_thread(inspect_file, path)
        if not heuristic.clean:
            return heuristic
        try:
            return await asyncio.to_thread(self._client.scan_path, path)
        except ScannerUnavailable:
            if self.required:
                raise
            return heuristic


@lru_cache
def get_scanner() -> MalwareScanner:
    return MalwareScanner(
        ClamAVClient(
            settings.clamav_host,
            settings.clamav_port,
            settings.clamav_timeout_seconds,
        ),
        required=settings.clamav_required,
    )
