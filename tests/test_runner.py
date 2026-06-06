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
    """Only the AI-pasted submission (Cyril) fires rules in Phase 1.
    Anna's original, Boris's web-copied, and Daria's verbatim copy of
    Anna are all targets for Phase 2 / Phase 4 signals — none of which
    are in scope for Phase 1."""
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


def test_phase1_stubs_return_empty():
    """Cohort and web signals are stubbed in Phase 1 — they must not crash
    and must consistently return empty lists across every assignment."""
    for assignment_id, title in [
        ("assignment-a", "A"),
        ("assignment-b", "B"),
        ("assignment-c", "C"),
    ]:
        report = _scan(assignment_id, title)
        for s in report.submissions:
            assert s.cohort_matches == []
            assert s.web_hits == []
