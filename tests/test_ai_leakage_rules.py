from __future__ import annotations

import pytest

from app.signals.ai_leakage import detect, registered_rules


def _rule_ids(text: str) -> set[str]:
    return {h.rule_id for h in detect(text)}


@pytest.mark.parametrize(
    "text,expected",
    [
        # English comment-leakage family
        ("# Here's the function you requested.\ndef f(): pass", "comment.heres_the"),
        ("// Here is the code:\nint f() { return 0; }", "comment.heres_the"),
        ("# Certainly! Here is the implementation.\ndef f(): pass", "comment.certainly_heres"),
        ("# As an AI language model, I would write:\ndef f(): pass", "comment.as_an_ai"),
        ("def f(): pass\n# I hope this helps!\n", "comment.i_hope_this_helps"),
        ("# This function takes a list and returns it sorted.\ndef sort(x): return x", "comment.explanation_block"),

        # Boilerplate
        ("def f(): pass\n# Example usage:\nf()\n", "boilerplate.example_usage_comment"),
        ("# Time complexity: O(n log n)\ndef f(x): return x", "boilerplate.time_complexity_inline"),

        # Markdown leakage
        ("```\ndef f(): pass\n```\n", "markdown.code_fence_in_source"),
        ("```python\ndef f(): pass\n```\n", "markdown.language_fence_in_source"),

        # Policy in comment
        ("# I'm sorry, but I cannot provide the full code.\ndef f(): pass", "policy.im_sorry_but_in_comment"),
        ("# I cannot provide the complete implementation.\ndef f(): pass", "policy.cannot_provide_in_comment"),
        ("# My knowledge cutoff is 2023.\ndef f(): pass", "policy.knowledge_cutoff_in_comment"),

        # Ukrainian
        ("# Ось функція, яку ви просили.\ndef f(): pass", "comment.ua_os_funktsiya"),
        ("# Звичайно! Ось ваша реалізація.\ndef f(): pass", "comment.ua_zvychaino_in_comment"),
        ("# Як мовна модель, я б написав це так:\ndef f(): pass", "comment.ua_as_language_model"),
        ("def f(): pass\n# Сподіваюся, це допоможе!\n", "comment.ua_spodivaius_dopomozhe"),
        ("# На жаль, я не можу надати повне рішення.\ndef f(): pass", "policy.ua_na_zhal"),
    ],
)
def test_rule_fires_on_positive_example(text: str, expected: str):
    assert expected in _rule_ids(text), (
        f"expected {expected} in {_rule_ids(text)}"
    )


def test_clean_code_has_no_hits():
    clean = (
        "def bubble_sort(lst):\n"
        "    n = len(lst)\n"
        "    for i in range(n):\n"
        "        for j in range(n - i - 1):\n"
        "            if lst[j] > lst[j + 1]:\n"
        "                lst[j], lst[j + 1] = lst[j + 1], lst[j]\n"
        "    return lst\n"
    )
    assert detect(clean) == []


def test_rules_registry_is_populated():
    rules = registered_rules()
    assert len(rules) >= 15
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), "rule ids must be unique"


def test_x_operator_does_not_trip_bold_in_code():
    """`x ** 2` is a Python operator, not Markdown bold. The bold rule must
    not fire on operator-heavy expressions."""
    code = "result = x ** 2 + y ** 3 + z ** 4"
    assert "markdown.bold_in_code" not in _rule_ids(code)


def test_hits_carry_evidence_and_spans():
    text = "intro\n# As an AI language model, here is the function.\ndef f(): pass"
    hits = detect(text)
    assert hits
    for h in hits:
        assert 0 <= h.start < h.end <= len(text)
        assert text[h.start:h.end] == h.evidence
