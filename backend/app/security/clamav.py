import socket
import struct
from pathlib import Path

from .file_checks import ScanResult


class ScannerUnavailable(Exception):
    pass


class ClamAVClient:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def ping(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"nPING\n")
                data = _recv_line(sock)
            return b"PONG" in data
        except OSError:
            return False

    def scan_path(self, path: Path) -> ScanResult:
        try:
            with socket.create_connection((self.host, self.port), self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"nINSTREAM\n")
                with path.open("rb") as handle:
                    while True:
                        chunk = handle.read(65536)
                        if not chunk:
                            break
                        sock.sendall(struct.pack(">I", len(chunk)) + chunk)
                sock.sendall(struct.pack(">I", 0))
                response = _recv_line(sock)
        except OSError as exc:
            raise ScannerUnavailable("ClamAV scanner is unavailable.") from exc

        text = response.decode("utf-8", errors="replace").strip()
        if text.endswith("FOUND"):
            threat = text.rsplit("FOUND", 1)[0]
            if ":" in threat:
                threat = threat.split(":", 1)[1].strip()
            return ScanResult(clean=False, threat_name=threat or "malware", source="clamav")
        if text.endswith("OK"):
            return ScanResult(clean=True, threat_name=None, source="clamav")
        raise ScannerUnavailable("ClamAV scanner returned an unexpected result.")


def _recv_line(sock: socket.socket) -> bytes:
    data = b""
    while True:
        part = sock.recv(4096)
        if not part:
            break
        data += part
        if b"\n" in data:
            break
    return data
