"""FastAPI webhook receiver for CopyLeaks results.

Run separately from the Streamlit UI:

    uvicorn app.signals.webcheck.webhook:app --host 0.0.0.0 --port 8000

Expose it publicly (ngrok / Cloudflare Tunnel / actual host) and set
the public URL as `COPYLEAKS_WEBHOOK_URL` so submit_scan can register it
with CopyLeaks. Results land in `data/webcheck.sqlite` keyed by scan_id;
the teacher UI then re-renders any newly-arrived WebHits.

Webhook bodies are not currently signature-verified — CopyLeaks supports
HMAC verification headers and adding that check is a small extension
documented as future work.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.config import settings


_SCHEMA = """
CREATE TABLE IF NOT EXISTS webcheck_results (
    scan_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _db_path() -> Path:
    return settings.db_path.parent / "webcheck.sqlite"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def store_result(scan_id: str, status: str, payload: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO webcheck_results (scan_id, status, payload) VALUES (?, ?, ?)",
            (scan_id, status, json.dumps(payload)),
        )


def load_result(scan_id: str) -> tuple[str, dict[str, Any]] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT status, payload FROM webcheck_results WHERE scan_id = ?",
            (scan_id,),
        ).fetchone()
    if not row:
        return None
    return row[0], json.loads(row[1])


def _build_app():
    try:
        from fastapi import FastAPI, Request
    except ImportError as e:
        raise RuntimeError(
            "FastAPI not installed — install the 'webhook' extra: pip install -e .[webhook]"
        ) from e

    app = FastAPI(title="diplom CopyLeaks webhook")

    @app.post("/{status}/{scan_id}")
    async def receive(status: str, scan_id: str, request: Request):
        payload = await request.json()
        store_result(scan_id, status, payload)
        return {"ok": True}

    return app


def create_app():
    """Factory used by uvicorn. Lazy-imports FastAPI so the webhook extra is optional."""
    return _build_app()


# Convenience for `uvicorn app.signals.webcheck.webhook:app`
try:
    app = _build_app()
except RuntimeError:
    app = None  # type: ignore[assignment]
