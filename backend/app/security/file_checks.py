from dataclasses import dataclass
from pathlib import Path

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
PDF_LAUNCH = (b"/Launch", b"/launch")
EXECUTABLE = (b"MZ", b"\x7fELF")


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    threat_name: str | None = None
    source: str = "heuristic"


def inspect_file(path: Path) -> ScanResult:
    """Cheap local checks. Do not log file bytes or extracted text."""
    data = path.read_bytes()
    if not data:
        return ScanResult(clean=False, threat_name="empty", source="heuristic")
    if EICAR in data:
        return ScanResult(clean=False, threat_name="eicar", source="heuristic")
    if data.startswith(EXECUTABLE):
        return ScanResult(clean=False, threat_name="executable", source="heuristic")
    if data[:2] == b"MZ" or data.startswith(b"\x7fELF"):
        return ScanResult(clean=False, threat_name="executable", source="heuristic")
    if data.startswith(b"%PDF") and any(token in data for token in PDF_LAUNCH):
        return ScanResult(clean=False, threat_name="pdf_launch", source="heuristic")
    if data.startswith(b"%PDF") and (b"MZ" == data[4:6] or b"\x7fELF" in data[:64]):
        return ScanResult(clean=False, threat_name="polyglot", source="heuristic")
    return ScanResult(clean=True, threat_name=None, source="heuristic")
