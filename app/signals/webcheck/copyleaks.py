"""CopyLeaks v3 REST integration.

Flow:
1. POST /v3/account/login-token with (email, key) → JWT access token.
2. PUT  /v3/scans/submit/file/{scanId} with base64'd content + properties.
3. CopyLeaks POSTs results to our configured webhook URL.

CopyLeaks v3 is webhook-only — there is no polling endpoint for the
finished scan results. For the thesis demo this module exposes:

- `check_text(text)` → submits a scan and returns immediately. The
  WebHits list is empty in the returned SubmissionReport; results arrive
  asynchronously and are persisted to the webcheck store, where the
  teacher UI re-reads them on the next view.
- `app.signals.webcheck.webhook:create_app()` → a FastAPI app that
  receives results and writes them into the store.

To actually demo end-to-end, the webhook must be reachable from the
internet (ngrok during development; a real host in production). Without
that, `check_text` still authenticates and submits successfully but
results never come back. This is documented in the thesis as a
deployment concern, not a methodological gap.
"""
from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import requests

from app.config import settings
from app.report.model import WebHit


log = logging.getLogger(__name__)


LOGIN_URL = "https://id.copyleaks.com/v3/account/login-token"
SUBMIT_URL_TPL = "https://api.copyleaks.com/v3/scans/submit/file/{scan_id}"

_TOKEN_CACHE_FILE = "copyleaks_token.json"


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float

    def is_valid(self) -> bool:
        return time.time() < self.expires_at - 60  # 60s safety margin


def _token_path() -> Path:
    return settings.db_path.parent / _TOKEN_CACHE_FILE


def _load_cached_token() -> _CachedToken | None:
    path = _token_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        tok = _CachedToken(access_token=data["access_token"], expires_at=data["expires_at"])
        return tok if tok.is_valid() else None
    except Exception:  # noqa: BLE001
        return None


def _save_cached_token(tok: _CachedToken) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"access_token": tok.access_token, "expires_at": tok.expires_at}))


def _login(email: str, api_key: str, session: requests.Session | None = None) -> _CachedToken:
    sess = session or requests
    resp = sess.post(
        LOGIN_URL,
        json={"email": email, "key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # CopyLeaks tokens last 48h.
    return _CachedToken(
        access_token=data["access_token"],
        expires_at=time.time() + 47 * 3600,
    )


def _get_token(session: requests.Session | None = None) -> _CachedToken:
    cached = _load_cached_token()
    if cached:
        return cached
    if not settings.copyleaks_email or not settings.copyleaks_api_key:
        raise RuntimeError("CopyLeaks credentials missing in settings")
    tok = _login(settings.copyleaks_email, settings.copyleaks_api_key, session=session)
    _save_cached_token(tok)
    return tok


def submit_scan(
    text: str,
    webhook_url: str,
    *,
    filename: str = "submission.txt",
    session: requests.Session | None = None,
    scan_id: str | None = None,
) -> str:
    """Submit text to CopyLeaks. Returns the scan_id used.

    Caller is responsible for providing a webhook URL that CopyLeaks can
    POST results to.
    """
    sess = session or requests
    tok = _get_token(session=session)
    scan_id = scan_id or str(uuid.uuid4())

    body = {
        "base64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "filename": filename,
        "properties": {
            "webhooks": {
                "status": f"{webhook_url}/{{STATUS}}/{scan_id}",
            },
            "sandbox": False,
        },
    }
    resp = sess.put(
        SUBMIT_URL_TPL.format(scan_id=scan_id),
        json=body,
        headers={"Authorization": f"Bearer {tok.access_token}"},
        timeout=60,
    )
    resp.raise_for_status()
    return scan_id


def check_text(text: str) -> list[WebHit]:
    """Synchronous-style adapter for the pipeline.

    Phase 4: if CopyLeaks creds are configured AND a webhook URL is set,
    submit the scan and return []. Webhook results arrive later and are
    fetched separately by the UI from the webcheck store. Returning empty
    here is intentional — the alternative would be blocking the scan
    indefinitely waiting for an external callback.
    """
    if not settings.has_copyleaks:
        return []
    webhook_url = getattr(settings, "copyleaks_webhook_url", None)
    if not webhook_url:
        log.info("CopyLeaks configured but no webhook URL set; skipping submission")
        return []
    try:
        sid = submit_scan(text, webhook_url)
        log.info("Submitted CopyLeaks scan %s", sid)
    except Exception as e:  # noqa: BLE001 — never let webcheck failures break a scan
        log.warning("CopyLeaks submission failed: %s: %s", type(e).__name__, e)
    return []
