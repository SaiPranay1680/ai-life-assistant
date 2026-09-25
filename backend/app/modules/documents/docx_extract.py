"""DOCX (OOXML) container validation and plain-text extraction.

Uses python-docx for paragraphs/tables only. Does not execute macros,
OLE objects, or external linked content.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_REQUIRED_PARTS = ("[Content_Types].xml", "word/document.xml")


class DocxExtractionError(ValueError):
    """Controlled validation / extraction failure for DOCX uploads."""


def looks_like_docx_bytes(data: bytes) -> bool:
    """Cheap sniff: ZIP local header plus OOXML markers in the head of the file."""
    if not data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return False
    return (
        b"[Content_Types].xml" in data
        or b"word/document" in data
        or b"wordprocessingml" in data
    )


def validate_docx_file(path: Path) -> None:
    """
    Validate that path is a readable OOXML Word package.

    Relies on ZIP structure + required parts — not on the filename alone.
    """
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            for required in _REQUIRED_PARTS:
                if required not in names:
                    raise DocxExtractionError("Invalid DOCX container.")
            # Encrypted OOXML packages are not supported.
            lowered = {name.lower() for name in names}
            if "encryptedpackage" in {Path(name).name.lower() for name in names} or any(
                "encryptioninfo" in name for name in lowered
            ):
                raise DocxExtractionError("Encrypted DOCX is not supported.")
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise DocxExtractionError("Corrupt DOCX archive.")
            # Ensure content types claim a Word document.
            try:
                content_types = archive.read("[Content_Types].xml")
            except KeyError as exc:
                raise DocxExtractionError("Invalid DOCX container.") from exc
            if b"wordprocessingml" not in content_types and b"word/document" not in content_types:
                raise DocxExtractionError("File is not a Word DOCX document.")
    except DocxExtractionError:
        raise
    except zipfile.BadZipFile as exc:
        raise DocxExtractionError("Invalid or corrupt DOCX file.") from exc
    except OSError as exc:
        raise DocxExtractionError("Unable to read this DOCX file.") from exc


def extract_docx_text(path: Path) -> str:
    """Extract non-empty paragraph and table text in document body order."""
    validate_docx_file(path)
    try:
        document = Document(str(path))
    except DocxExtractionError:
        raise
    except Exception as exc:  # malformed package that zip accepted but python-docx rejects
        raise DocxExtractionError("Unable to read this DOCX file.") from exc

    lines: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            paragraph = Paragraph(child, document)
            text = (paragraph.text or "").strip()
            if text:
                lines.append(text)
        elif tag == qn("w:tbl"):
            table = Table(child, document)
            for row in table.rows:
                cells: list[str] = []
                for cell in row.cells:
                    cell_text = " ".join(
                        (p.text or "").strip() for p in cell.paragraphs if (p.text or "").strip()
                    )
                    if cell_text:
                        cells.append(cell_text)
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_docx_pages(path: Path) -> list[tuple[int, str]]:
    """
    Return pages as (page_number, text) for the shared classification pipeline.

    DOCX has no fixed page model here — content is returned as a single logical page.
    Empty documents yield one empty page (safe for downstream classifiers).
    """
    text = extract_docx_text(path)
    return [(1, text)]
