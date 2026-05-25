from __future__ import annotations

import io


SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.presentation",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


class UnsupportedMimeError(ValueError):
    pass


def extract_text(data: bytes, mime_type: str) -> str:
    """Return plain text extracted from a file's bytes.

    Google-native docs are expected to have already been exported to text/plain
    by ClassroomClient.download_drive_file, so we treat them as text here.
    """
    if mime_type.startswith("application/vnd.google-apps."):
        return _decode_text(data)
    if mime_type in ("text/plain", "text/markdown"):
        return _decode_text(data)
    if mime_type == "application/pdf":
        return _extract_pdf(data)
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(data)
    raise UnsupportedMimeError(f"Unsupported MIME type: {mime_type}")


def _decode_text(data: bytes) -> str:
    # Try UTF-8 first; fall back to latin-1, which is total (every byte decodes).
    # UTF-16 is intentionally skipped because it silently decodes arbitrary bytes
    # into garbage when the input is actually a single-byte encoding.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)
