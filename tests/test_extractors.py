from __future__ import annotations

import pytest

from app.classroom.extractors import UnsupportedMimeError, extract_text


def test_plain_text_utf8():
    data = "hello world\nsecond line".encode("utf-8")
    assert extract_text(data, "text/plain") == "hello world\nsecond line"


def test_plain_text_latin1_fallback():
    data = "café".encode("latin-1")
    assert "caf" in extract_text(data, "text/plain")


def test_google_doc_treated_as_text():
    data = "exported doc body".encode("utf-8")
    assert extract_text(data, "application/vnd.google-apps.document") == "exported doc body"


def test_unsupported_mime_raises():
    with pytest.raises(UnsupportedMimeError):
        extract_text(b"\x00\x01", "application/octet-stream")
