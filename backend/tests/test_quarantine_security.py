import tempfile
import unittest
from pathlib import Path

from app.security.clamav import ScannerUnavailable
from app.security.file_checks import EICAR, inspect_file
from app.security.scanner import MalwareScanner
from app.storage.local_storage import LocalStorage


class FakeClamAV:
    def __init__(self, *, ping: bool = True, result=None, error: Exception | None = None) -> None:
        self._ping = ping
        self._result = result
        self._error = error
        self.scanned = []

    def ping(self) -> bool:
        return self._ping

    def scan_path(self, path: Path):
        self.scanned.append(path)
        if self._error:
            raise self._error
        return self._result


class FileCheckTests(unittest.TestCase):
    def test_eicar_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"prefix " + EICAR + b" suffix")
            path = Path(handle.name)
        try:
            result = inspect_file(path)
            self.assertFalse(result.clean)
            self.assertEqual(result.threat_name, "eicar")
        finally:
            path.unlink(missing_ok=True)

    def test_executable_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"MZ\x90\x00this is not a pdf")
            path = Path(handle.name)
        try:
            result = inspect_file(path)
            self.assertFalse(result.clean)
            self.assertEqual(result.threat_name, "executable")
        finally:
            path.unlink(missing_ok=True)

    def test_pdf_launch_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"%PDF-1.4\n1 0 obj\n<< /Launch << /Win << /F (cmd.exe) >> >> >>\n")
            path = Path(handle.name)
        try:
            result = inspect_file(path)
            self.assertFalse(result.clean)
            self.assertEqual(result.threat_name, "pdf_launch")
        finally:
            path.unlink(missing_ok=True)

    def test_clean_pdf_passes_heuristics(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"%PDF-1.4\n%EOF\n")
            path = Path(handle.name)
        try:
            result = inspect_file(path)
            self.assertTrue(result.clean)
        finally:
            path.unlink(missing_ok=True)


class ScannerFailClosedTests(unittest.IsolatedAsyncioTestCase):
    async def test_required_scanner_unavailable_raises(self) -> None:
        scanner = MalwareScanner(
            FakeClamAV(error=ScannerUnavailable("down")),
            required=True,
        )
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"%PDF-1.4\n%EOF\n")
            path = Path(handle.name)
        try:
            with self.assertRaises(ScannerUnavailable):
                await scanner.scan(path)
        finally:
            path.unlink(missing_ok=True)

    async def test_optional_scanner_unavailable_allows_clean_heuristic(self) -> None:
        scanner = MalwareScanner(
            FakeClamAV(error=ScannerUnavailable("down")),
            required=False,
        )
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"%PDF-1.4\n%EOF\n")
            path = Path(handle.name)
        try:
            result = await scanner.scan(path)
            self.assertTrue(result.clean)
            self.assertEqual(result.source, "heuristic")
        finally:
            path.unlink(missing_ok=True)

    async def test_heuristic_reject_skips_clamav(self) -> None:
        fake = FakeClamAV(result=None)
        scanner = MalwareScanner(fake, required=True)
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"MZ\x90\x00not-a-document")
            path = Path(handle.name)
        try:
            result = await scanner.scan(path)
            self.assertFalse(result.clean)
            self.assertEqual(fake.scanned, [])
        finally:
            path.unlink(missing_ok=True)


class LocalQuarantineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.storage = LocalStorage(str(root / "quarantine"), str(root / "uploads"))
        self.key = "workspaces/ws/documents/doc/original.pdf"

    async def asyncTearDown(self) -> None:
        self.temp.cleanup()

    async def test_rejected_file_never_enters_permanent(self) -> None:
        async def chunks():
            yield b"%PDF-1.4\n%EOF\n"

        await self.storage.save_quarantine(self.key, chunks())
        self.assertFalse(await self.storage.exists_permanent(self.key))
        await self.storage.delete_quarantine(self.key)
        with self.assertRaises(FileNotFoundError):
            async with self.storage.open_for_read(self.key, location="quarantine"):
                pass

    async def test_promote_moves_out_of_quarantine(self) -> None:
        async def chunks():
            yield b"%PDF-1.4\n%EOF\n"

        await self.storage.save_quarantine(self.key, chunks())
        await self.storage.promote(self.key)
        self.assertTrue(await self.storage.exists_permanent(self.key))
        with self.assertRaises(FileNotFoundError):
            async with self.storage.open_for_read(self.key, location="quarantine"):
                pass
        path, is_temp = await self.storage.materialize(self.key, location="permanent")
        self.assertFalse(is_temp)
        self.assertEqual(path.read_bytes(), b"%PDF-1.4\n%EOF\n")

    async def test_orphan_cleanup(self) -> None:
        async def chunks():
            yield b"%PDF-1.4\n%EOF\n"

        await self.storage.save_quarantine(self.key, chunks())
        removed = await self.storage.cleanup_orphans(max_age_seconds=0)
        self.assertEqual(removed, 1)
        self.assertFalse(await self.storage.exists_permanent(self.key))


if __name__ == "__main__":
    unittest.main()
