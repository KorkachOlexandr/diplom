from __future__ import annotations

from datetime import datetime, timezone

from app.pipeline import store
from app.report.model import LeakageHit, ScanReport, SubmissionReport


def _make_report(scan_id: str = "scan-1") -> ScanReport:
    return ScanReport(
        scan_id=scan_id,
        course_id="course-1",
        assignment_id="asn-1",
        assignment_title="Essay",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        submissions=[
            SubmissionReport(
                submission_id="sub-1",
                student_id="user-1",
                student_name="Alice",
                text="As an AI language model, I cannot help.",
                leakage_hits=[
                    LeakageHit(
                        rule_id="refusal.as_an_ai",
                        rule_family="refusal",
                        description="self-id",
                        start=0,
                        end=23,
                        evidence="As an AI language model",
                    )
                ],
            )
        ],
    )


def test_save_and_load_roundtrip(tmp_path):
    db = tmp_path / "test.sqlite"
    report = _make_report()
    store.save_scan(report, db_path=db)

    loaded = store.load_scan(report.scan_id, db_path=db)
    assert loaded is not None
    assert loaded.scan_id == report.scan_id
    assert loaded.submissions[0].leakage_hits[0].rule_id == "refusal.as_an_ai"


def test_list_scans_filters_by_assignment(tmp_path):
    db = tmp_path / "test.sqlite"
    store.save_scan(_make_report("scan-a"), db_path=db)
    store.save_scan(_make_report("scan-b"), db_path=db)

    rows = store.list_scans(assignment_id="asn-1", db_path=db)
    assert {r["scan_id"] for r in rows} == {"scan-a", "scan-b"}

    none_rows = store.list_scans(assignment_id="other", db_path=db)
    assert none_rows == []
