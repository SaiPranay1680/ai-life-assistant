from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MIME_EXTENSION_MAP = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


def safe_filename(filename: str | None) -> str:
    return Path(filename or "upload").name


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, JPG or PNG files are allowed.")
    return extension


def detect_mime(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "application/octet-stream"


def validate_file_type(extension: str, detected_mime: str) -> None:
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise ValueError("File contents are not a PDF, JPG or PNG.")
    if extension not in MIME_EXTENSION_MAP[detected_mime]:
        raise ValueError("File type does not match the file extension.")
