from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.report.model import ScanReport


SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    assignment_title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scans_assignment ON scans(assignment_id, created_at DESC);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def save_scan(report: ScanReport, db_path: Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scans "
            "(scan_id, course_id, assignment_id, assignment_title, created_at, report_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                report.scan_id,
                report.course_id,
                report.assignment_id,
                report.assignment_title,
                report.created_at.isoformat(),
                report.model_dump_json(),
            ),
        )


def load_scan(scan_id: str, db_path: Path | None = None) -> ScanReport | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT report_json FROM scans WHERE scan_id = ?", (scan_id,)
        ).fetchone()
    if not row:
        return None
    return ScanReport.model_validate_json(row[0])


def list_scans(assignment_id: str | None = None, db_path: Path | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        if assignment_id:
            rows = conn.execute(
                "SELECT scan_id, course_id, assignment_id, assignment_title, created_at "
                "FROM scans WHERE assignment_id = ? ORDER BY created_at DESC",
                (assignment_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT scan_id, course_id, assignment_id, assignment_title, created_at "
                "FROM scans ORDER BY created_at DESC"
            ).fetchall()
    return [
        {
            "scan_id": r[0],
            "course_id": r[1],
            "assignment_id": r[2],
            "assignment_title": r[3],
            "created_at": datetime.fromisoformat(r[4]),
        }
        for r in rows
    ]
