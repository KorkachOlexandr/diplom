from __future__ import annotations

import pytest

from app.signals.ai_leakage import detect, registered_rules


def _rule_ids(text: str) -> set[str]:
    return {h.rule_id for h in detect(text)}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Certainly! Here's an essay about climate change.", "preamble.certainly_heres"),
        ("Sure, here is your summary.", "preamble.certainly_heres"),
        ("I'd be happy to help with that essay.", "preamble.happy_to_help"),
        ("Here's a 300-word essay about climate change.", "preamble.heres_a"),
        ("As an AI language model, I should note that...", "refusal.as_an_ai"),
        ("I cannot provide a definitive answer to this.", "refusal.i_cannot"),
        ("My knowledge cutoff is 2023.", "refusal.knowledge_cutoff"),
        ("[Your Name]\nEssay on photosynthesis", "template.bracket_placeholder"),
        ("Please enter your name above the title.", "template.instruction_echo"),
    ],
)
def test_rule_fires_on_positive_example(text: str, expected: str):
    assert expected in _rule_ids(text)


def test_clean_text_has_no_hits():
    clean = (
        "Photosynthesis is the process by which green plants convert sunlight into "
        "chemical energy. The chloroplasts contain chlorophyll, which absorbs light "
        "primarily in the blue and red wavelengths."
    )
    assert detect(clean) == []


def test_rules_registry_is_populated():
    rules = registered_rules()
    assert len(rules) >= 5
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), "rule ids must be unique"


def test_hits_carry_evidence_and_spans():
    text = "Some intro. As an AI language model, I can help. End."
    hits = detect(text)
    assert hits, "expected at least one hit"
    for h in hits:
        assert 0 <= h.start < h.end <= len(text)
        assert text[h.start:h.end] == h.evidence
