from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock

import pytest

from app.signals.webcheck import copyleaks


@pytest.fixture(autouse=True)
def isolate_token_cache(tmp_path, monkeypatch):
    """Redirect the cached-token file into a tmp directory so tests don't
    pollute the developer's home / repo state."""
    from app.config import settings

    monkeypatch.setattr(settings, "db_path", tmp_path / "diplom.sqlite")
    monkeypatch.setattr(settings, "copyleaks_email", "test@example.com")
    monkeypatch.setattr(settings, "copyleaks_api_key", "fake-api-key")
    yield


def _login_response(token: str = "test-jwt-token"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token}
    resp.raise_for_status.return_value = None
    return resp


def _submit_response():
    resp = MagicMock()
    resp.status_code = 201
    resp.json.return_value = {"ok": True}
    resp.raise_for_status.return_value = None
    return resp


def test_login_caches_token(tmp_path, monkeypatch):
    session = MagicMock()
    session.post.return_value = _login_response("jwt-A")

    tok = copyleaks._login("u@example.com", "k", session=session)
    assert tok.access_token == "jwt-A"
    assert tok.is_valid()

    copyleaks._save_cached_token(tok)
    cached = copyleaks._load_cached_token()
    assert cached is not None
    assert cached.access_token == "jwt-A"


def test_submit_scan_uses_correct_url_and_body(monkeypatch):
    session = MagicMock()
    session.post.return_value = _login_response("jwt-B")
    session.put.return_value = _submit_response()

    sid = copyleaks.submit_scan(
        "Hello world",
        webhook_url="https://example.com/cb",
        scan_id="abc123",
        session=session,
    )
    assert sid == "abc123"

    # Verify auth happened.
    assert session.post.call_args.args[0] == copyleaks.LOGIN_URL

    # Verify submission URL and Authorization header.
    put_call = session.put.call_args
    assert put_call.args[0] == copyleaks.SUBMIT_URL_TPL.format(scan_id="abc123")
    assert put_call.kwargs["headers"]["Authorization"] == "Bearer jwt-B"

    body = put_call.kwargs["json"]
    decoded = base64.b64decode(body["base64"]).decode("utf-8")
    assert decoded == "Hello world"
    assert "STATUS" in body["properties"]["webhooks"]["status"]
    assert "abc123" in body["properties"]["webhooks"]["status"]


def test_check_text_returns_empty_without_webhook(monkeypatch):
    """check_text always returns [] immediately — results come via webhook."""
    monkeypatch.setattr(
        "app.config.settings.copyleaks_webhook_url", None, raising=False
    )
    assert copyleaks.check_text("anything") == []


def test_check_text_returns_empty_without_credentials(monkeypatch):
    monkeypatch.setattr("app.config.settings.copyleaks_email", None)
    monkeypatch.setattr("app.config.settings.copyleaks_api_key", None)
    assert copyleaks.check_text("anything") == []


def test_webhook_store_roundtrip(tmp_path, monkeypatch):
    from app.signals.webcheck import webhook
    from app.config import settings

    monkeypatch.setattr(settings, "db_path", tmp_path / "diplom.sqlite")
    webhook.store_result("scan-1", "completed", {"score": 42})
    loaded = webhook.load_result("scan-1")
    assert loaded is not None
    status, payload = loaded
    assert status == "completed"
    assert payload == {"score": 42}
