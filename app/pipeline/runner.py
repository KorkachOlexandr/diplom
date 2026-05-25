from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.classroom.client import ClassroomClient, Submission
from app.classroom.extractors import (
    SUPPORTED_MIME_TYPES,
    UnsupportedMimeError,
    extract_text,
)
from app.report.model import ScanReport, SubmissionReport
from app.signals import ai_leakage, cohort, webcheck


def scan_assignment(
    course_id: str,
    assignment_id: str,
    assignment_title: str,
    client: ClassroomClient,
) -> ScanReport:
    """Run the full pipeline for one assignment.

    Phase 1: webcheck and cohort signals return empty by design (see plan).
    AI-leakage rules are wired up because they're regex-cheap and make the
    end-to-end pipeline observably alive in the dashboard.
    """
    submissions = client.list_submissions(course_id, assignment_id)
    reports = [_build_submission_report(s, client) for s in submissions]

    # Cohort similarity: stubbed; returns {id: []} but plugs into the same
    # SubmissionReport shape so Phase 2 just swaps the implementation.
    cohort_matches = cohort.find_matches(reports)
    for r in reports:
        r.cohort_matches = cohort_matches.get(r.submission_id, [])

    return ScanReport(
        scan_id=str(uuid.uuid4()),
        course_id=course_id,
        assignment_id=assignment_id,
        assignment_title=assignment_title,
        created_at=datetime.now(timezone.utc),
        submissions=reports,
    )


def _build_submission_report(s: Submission, client: ClassroomClient) -> SubmissionReport:
    text, error = _extract_submission_text(s, client)
    return SubmissionReport(
        submission_id=s.id,
        student_id=s.user_id,
        student_name=s.student_name,
        text=text,
        extraction_error=error,
        leakage_hits=ai_leakage.detect(text) if text else [],
        web_hits=webcheck.check_text(text) if text else [],
    )


def _extract_submission_text(s: Submission, client: ClassroomClient) -> tuple[str, str | None]:
    if not s.attachments:
        return ("", "no attachments")
    chunks: list[str] = []
    skipped: list[str] = []
    for att in s.attachments:
        if att.mime_type not in SUPPORTED_MIME_TYPES:
            skipped.append(f"{att.title} ({att.mime_type})")
            continue
        try:
            data = client.download_drive_file(att.file_id, att.mime_type)
            chunks.append(extract_text(data, att.mime_type))
        except UnsupportedMimeError as e:
            skipped.append(f"{att.title}: {e}")
        except Exception as e:  # noqa: BLE001 — surface as a per-submission error, don't fail the whole scan
            skipped.append(f"{att.title}: {type(e).__name__}: {e}")
    text = "\n\n".join(chunks).strip()
    error = "; ".join(skipped) if skipped else None
    return (text, error)
