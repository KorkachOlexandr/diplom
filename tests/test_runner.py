from __future__ import annotations

from app.pipeline import runner
from app.ui.demo_client import DemoClient


def _scan(assignment_id: str, title: str):
    return runner.scan_assignment(
        course_id="demo-course",
        assignment_id=assignment_id,
        assignment_title=title,
        client=DemoClient(),
    )


def _rules_by_student(report) -> dict[str, set[str]]:
    return {s.student_name: {h.rule_id for h in s.leakage_hits} for s in report.submissions}


def test_assignment_a_originals_and_copies():
    """AI-leakage fires on Cyril (Phase 1+).
    Cohort similarity fires on the acc1==acc4 verbatim copy (Phase 2 — MinHash).
    Web plagiarism on Boris stays empty (Phase 4 — CopyLeaks webhook deployment)."""
    report = _scan("assignment-a", "Originals & Copies")
    assert len(report.submissions) == 4

    rules = _rules_by_student(report)
    assert rules["Anna Aiken"] == set()
    assert rules["Boris Borrowed"] == set()
    assert rules["Daria Duplicate"] == set()

    cyril = rules["Cyril Chatgpt"]
    assert "preamble.certainly_heres" in cyril
    assert "refusal.as_an_ai" in cyril
    assert "refusal.knowledge_cutoff" in cyril

    # Cohort signal: Anna and Daria submitted identical text, so each
    # should now have a MinHash match pointing at the other.
    by_name = {s.student_name: s for s in report.submissions}
    anna_matches = by_name["Anna Aiken"].cohort_matches
    daria_matches = by_name["Daria Duplicate"].cohort_matches
    assert any(
        m.other_student_name == "Daria Duplicate" and m.channel == "minhash"
        for m in anna_matches
    )
    assert any(
        m.other_student_name == "Anna Aiken" and m.channel == "minhash"
        for m in daria_matches
    )

    # Boris and Cyril should not be in any cohort match (their texts are
    # different from both Anna and from each other).
    assert by_name["Boris Borrowed"].cohort_matches == []
    assert by_name["Cyril Chatgpt"].cohort_matches == []


def test_assignment_b_known_limitations():
    """Every submission is legitimate text that trips a rule on purpose.
    This is the false-positive showcase that feeds the limitations chapter."""
    report = _scan("assignment-b", "Known limitations")
    rules = _rules_by_student(report)

    assert "refusal.as_an_ai" in rules["Anna Aiken"]
    assert "template.bracket_placeholder" in rules["Boris Borrowed"]
    assert "template.instruction_echo" in rules["Cyril Chatgpt"]
    assert "preamble.certainly_heres" in rules["Daria Duplicate"]


def test_assignment_c_all_clean():
    """Four honest essays — and one empty submission — none should fire."""
    report = _scan("assignment-c", "All clean")
    assert len(report.submissions) == 4

    for s in report.submissions:
        assert s.leakage_hits == [], (
            f"{s.student_name} unexpectedly fired: "
            f"{[h.rule_id for h in s.leakage_hits]}"
        )

    daria = next(s for s in report.submissions if s.student_name == "Daria Duplicate")
    assert daria.text == ""
    assert daria.extraction_error == "no attachments"


def test_web_signal_stays_empty_without_deployed_webhook():
    """Phase 4 CopyLeaks integration submits scans asynchronously; results
    arrive via webhook, not inline. Without configured creds + webhook URL
    (which is the test environment's state), web_hits must stay empty."""
    for assignment_id, title in [
        ("assignment-a", "A"),
        ("assignment-b", "B"),
        ("assignment-c", "C"),
    ]:
        report = _scan(assignment_id, title)
        for s in report.submissions:
            assert s.web_hits == []


def test_no_cohort_matches_in_clean_assignment():
    """Assignment C's four submissions are unrelated honest essays."""
    report = _scan("assignment-c", "All clean")
    for s in report.submissions:
        assert s.cohort_matches == [], (
            f"{s.student_name} unexpectedly matched: "
            f"{[(m.other_student_name, m.channel) for m in s.cohort_matches]}"
        )
