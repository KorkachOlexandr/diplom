from __future__ import annotations

from app.pipeline import runner
from app.ui.demo_client import DemoClient


def test_demo_scan_end_to_end():
    client = DemoClient()
    report = runner.scan_assignment(
        course_id="demo-course",
        assignment_id="demo-assignment",
        assignment_title="Essay: Climate Change",
        client=client,
    )

    assert len(report.submissions) == 4
    by_name = {s.student_name: s for s in report.submissions}

    # Alice's submission is clean prose; no rules should fire.
    assert by_name["Alice Honest"].leakage_hits == []

    # Bob's submission has a preamble and the as-an-AI self-id.
    bob_rules = {h.rule_id for h in by_name["Bob Pastesalot"].leakage_hits}
    assert "preamble.certainly_heres" in bob_rules
    assert "refusal.as_an_ai" in bob_rules

    # Carol has a bracket placeholder and an instruction echo.
    carol_rules = {h.rule_id for h in by_name["Carol Templater"].leakage_hits}
    assert "template.bracket_placeholder" in carol_rules
    assert "template.instruction_echo" in carol_rules

    # Dan has a refusal artifact and a knowledge-cutoff disclosure.
    dan_rules = {h.rule_id for h in by_name["Dan Refuser"].leakage_hits}
    assert "refusal.i_cannot" in dan_rules
    assert "refusal.knowledge_cutoff" in dan_rules

    # All submissions should have empty cohort + web hits in Phase 1.
    for s in report.submissions:
        assert s.cohort_matches == []
        assert s.web_hits == []
