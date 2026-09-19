"""Compatibility wrapper. New code should use app.security.scanner."""

from pathlib import Path

from ...security.file_checks import inspect_file


def scan_path(path: Path) -> str:
    result = inspect_file(path)
    return "clean" if result.clean else "infected"
