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
    """Bubble-sort assignment: Cyril's AI-pasted version fires multiple
    leakage rules; Anna and Daria submit structurally identical code
    (rename only) and should match each other via the cohort channels."""
    report = _scan("assignment-a", "Originals & Copies")
    assert len(report.submissions) == 4

    rules = _rules_by_student(report)

    # Cyril (AI-pasted) should fire several leakage rules.
    cyril = rules["Cyril Chatgpt"]
    assert "comment.certainly_heres" in cyril
    assert "comment.i_hope_this_helps" in cyril
    assert "boilerplate.example_usage_comment" in cyril
    assert "markdown.code_fence_in_source" in cyril
    assert "markdown.language_fence_in_source" in cyril

    # Anna's clean original — no leakage rules should fire.
    assert rules["Anna Aiken"] == set()

    # Daria's rename — also no leakage rules.
    assert rules["Daria Duplicate"] == set()

    # Cohort: Anna and Daria should match each other (winnowing + ast).
    by_name = {s.student_name: s for s in report.submissions}
    anna_targets = {
        (m.other_student_name, m.channel) for m in by_name["Anna Aiken"].cohort_matches
    }
    assert ("Daria Duplicate", "winnowing") in anna_targets
    assert ("Daria Duplicate", "ast") in anna_targets

    daria_targets = {
        (m.other_student_name, m.channel) for m in by_name["Daria Duplicate"].cohort_matches
    }
    assert ("Anna Aiken", "winnowing") in daria_targets
    assert ("Anna Aiken", "ast") in daria_targets


def test_assignment_b_known_limitations_fires_expected_false_positives():
    """Each submission in assignment B is honest code that deliberately
    trips a specific rule. Documents the limitations chapter."""
    report = _scan("assignment-b", "Known limitations")
    rules = _rules_by_student(report)

    # Anna: docstring tutorial — fires explanation_block + example_usage.
    assert "comment.explanation_block" in rules["Anna Aiken"]

    # Boris: legitimate essay-style comment about ML — fires as_an_ai.
    assert "comment.as_an_ai" in rules["Boris Borrowed"]

    # Cyril: docstring contains a literal ``` fence for documentation.
    assert "markdown.code_fence_in_source" in rules["Cyril Chatgpt"]

    # Daria: legitimate multi-note module — fires note_blocks_repeated.
    assert "boilerplate.note_blocks_repeated" in rules["Daria Duplicate"]


def test_assignment_c_all_clean():
    """Three honest fib implementations + one empty submission.
    No leakage rules should fire on the implementations."""
    report = _scan("assignment-c", "All clean")
    assert len(report.submissions) == 4

    daria = next(s for s in report.submissions if s.student_name == "Daria Duplicate")
    assert daria.text == ""
    assert daria.extraction_error == "no attachments"

    # The three other submissions are honest, distinct fib implementations.
    for s in report.submissions:
        if s.student_name == "Daria Duplicate":
            continue
        assert s.leakage_hits == [], (
            f"{s.student_name} unexpectedly fired: {[h.rule_id for h in s.leakage_hits]}"
        )


def test_web_signal_stays_empty_without_deployed_webhook():
    """CopyLeaks-equivalent web signal is a stub for code-plagiarism — the
    real-world counterpart is Moss/JPlag which are CLI tools, not REST APIs.
    web_hits must stay empty across all assignments in demo mode."""
    for assignment_id, title in [
        ("assignment-a", "A"),
        ("assignment-b", "B"),
        ("assignment-c", "C"),
    ]:
        report = _scan(assignment_id, title)
        for s in report.submissions:
            assert s.web_hits == []
