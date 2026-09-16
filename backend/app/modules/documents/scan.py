import shutil
import subprocess
from pathlib import Path

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
PDF_LAUNCH = (b"/Launch", b"/launch")
EXECUTABLE = (b"MZ", b"\x7fELF")


def scan_path(path: Path) -> str:
    """Return 'clean' or 'infected'. Do not log file bytes or extracted text."""
    data = path.read_bytes()
    if not data:
        return "infected"
    if EICAR in data:
        return "infected"
    if data.startswith(EXECUTABLE):
        return "infected"
    if data.startswith(b"%PDF") and any(token in data for token in PDF_LAUNCH):
        return "infected"
    clam = _clamscan(path)
    if clam == "infected":
        return "infected"
    return "clean"


def _clamscan(path: Path) -> str | None:
    exe = shutil.which("clamscan")
    if not exe:
        return None
    try:
        completed = subprocess.run(
            [exe, "--no-summary", "--stdout", str(path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode == 1:
        return "infected"
    if completed.returncode == 0:
        return "clean"
    return None
