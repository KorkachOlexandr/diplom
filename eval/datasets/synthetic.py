"""Synthetic dataset generator for the code-plagiarism evaluation chapter.

Produces labeled fixtures for both signals without any external download:

- ai_leakage: clean Python snippets + clean snippets with known leakage
  patterns injected at specific positions. Each positive is tagged with
  the rule_id it should fire.

- cohort: pairs of (text_a, text_b, relation) where relation is one of
  "unrelated", "exact_copy", "renamed" (variables renamed but structure
  identical), or "reordered" (independent statements reordered).

Reproducibility: a given seed produces the same dataset every time so
the thesis evaluation chapter cites stable numbers.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass


# ---------- Seed Python snippets ----------

_CLEAN_SNIPPETS = [
    # bubble sort
    'def bubble_sort(lst):\n'
    '    n = len(lst)\n'
    '    for i in range(n):\n'
    '        for j in range(0, n - i - 1):\n'
    '            if lst[j] > lst[j + 1]:\n'
    '                lst[j], lst[j + 1] = lst[j + 1], lst[j]\n'
    '    return lst\n',
    # iterative fib
    'def fib(n):\n'
    '    a, b = 0, 1\n'
    '    for _ in range(n):\n'
    '        a, b = b, a + b\n'
    '    return a\n',
    # recursive factorial
    'def factorial(n):\n'
    '    if n <= 1:\n'
    '        return 1\n'
    '    return n * factorial(n - 1)\n',
    # gcd
    'def gcd(a, b):\n'
    '    while b != 0:\n'
    '        a, b = b, a % b\n'
    '    return a\n',
    # linear search
    'def find(lst, target):\n'
    '    for i, item in enumerate(lst):\n'
    '        if item == target:\n'
    '            return i\n'
    '    return -1\n',
    # count vowels
    'def count_vowels(s):\n'
    '    vowels = "aeiou"\n'
    '    count = 0\n'
    '    for ch in s.lower():\n'
    '        if ch in vowels:\n'
    '            count += 1\n'
    '    return count\n',
    # is_palindrome
    'def is_palindrome(s):\n'
    '    cleaned = s.lower()\n'
    '    return cleaned == cleaned[::-1]\n',
    # reverse list
    'def reverse(lst):\n'
    '    out = []\n'
    '    for i in range(len(lst) - 1, -1, -1):\n'
    '        out.append(lst[i])\n'
    '    return out\n',
]


# ---------- AI-leakage positive injections ----------

# Each entry: (rule_id, injection_text_to_insert_before_or_after_snippet, prepend?)
# Where the leakage shows up in real code: above the function (as a header
# comment / docstring) or below it (as an "example usage" block).
_LEAKAGE_INJECTIONS: list[tuple[str, str, bool]] = [
    # llm_comment family
    ("comment.heres_the", "# Here's the function you requested.\n", True),
    ("comment.certainly_heres", "# Certainly! Here is the implementation.\n", True),
    ("comment.as_an_ai", "# As an AI language model, I would write this as:\n", True),
    ("comment.i_hope_this_helps", "\n# I hope this helps! Let me know if you have any questions.\n", False),
    ("comment.explanation_block", "# This function takes a list and returns it sorted.\n", True),

    # boilerplate family
    ("boilerplate.example_usage_comment", "\n# Example usage:\nprint(fn([3, 1, 2]))\n", False),
    ("boilerplate.time_complexity_inline", "# Time complexity: O(n log n)\n", True),
    (
        "boilerplate.note_blocks_repeated",
        "# Note: handles empty input.\n",
        True,
    ),

    # markdown family
    ("markdown.code_fence_in_source", "```\n", True),
    ("markdown.language_fence_in_source", "```python\n", True),

    # policy family
    ("policy.im_sorry_but_in_comment", "# I'm sorry, but I cannot provide the complete solution.\n", True),
    ("policy.cannot_provide_in_comment", "# I cannot provide the complete implementation in one block.\n", True),
    ("policy.knowledge_cutoff_in_comment", "# My knowledge cutoff is 2023.\n", True),

    # Ukrainian variants
    ("comment.ua_os_funktsiya", "# Ось функція, яку ви просили.\n", True),
    ("comment.ua_zvychaino_in_comment", "# Звичайно! Ось ваша реалізація.\n", True),
    ("comment.ua_as_language_model", "# Як мовна модель, я б написав це так:\n", True),
    ("comment.ua_spodivaius_dopomozhe", "\n# Сподіваюся, це допоможе!\n", False),
    ("policy.ua_na_zhal", "# На жаль, я не можу надати повне рішення.\n", True),
]


@dataclass(frozen=True)
class LeakageExample:
    text: str
    is_positive: bool
    expected_rule_id: str | None


def _inject(snippet: str, injection: str, prepend: bool, extra_for_note: bool = False) -> str:
    if extra_for_note:
        # note_blocks_repeated requires 2+ notes; sprinkle a second one.
        injection = injection + injection.replace("empty input", "edge cases")
    return injection + snippet if prepend else snippet + injection


def generate_ai_leakage(n_per_rule: int = 5, n_negative: int = 40, seed: int = 0) -> list[LeakageExample]:
    rng = random.Random(seed)
    out: list[LeakageExample] = []
    for rule_id, injection, prepend in _LEAKAGE_INJECTIONS:
        for _ in range(n_per_rule):
            base = rng.choice(_CLEAN_SNIPPETS)
            text = _inject(
                base,
                injection,
                prepend,
                extra_for_note=(rule_id == "boilerplate.note_blocks_repeated"),
            )
            out.append(LeakageExample(text=text, is_positive=True, expected_rule_id=rule_id))
    for _ in range(n_negative):
        out.append(
            LeakageExample(text=rng.choice(_CLEAN_SNIPPETS), is_positive=False, expected_rule_id=None)
        )
    rng.shuffle(out)
    return out


# ---------- Cohort: code transformations ----------

@dataclass(frozen=True)
class CohortExample:
    id_a: str
    id_b: str
    text_a: str
    text_b: str
    relation: str  # "unrelated" | "exact_copy" | "renamed" | "reordered"


_RENAME_TABLE = {
    "lst": "arr", "n": "length", "i": "outer", "j": "inner",
    "a": "first", "b": "second", "count": "total", "out": "result",
    "target": "needle", "vowels": "vowel_set", "cleaned": "lowered",
    "fib": "fibonacci", "fn": "func", "find": "linear_search",
    "factorial": "fact", "gcd": "greatest_common_divisor",
}


def _rename_identifiers(source: str) -> str:
    """Replace whole-word identifiers per the rename table. Deliberately
    naive: a real student rename pass is messier, but this is enough to
    test the cohort signal's robustness against the simplest evasion."""
    def sub(m: re.Match) -> str:
        word = m.group(0)
        return _RENAME_TABLE.get(word, word)
    return re.sub(r"\b\w+\b", sub, source)


def _reorder_top_level_defs(source: str) -> str:
    """Reorder independent top-level statements separated by blank lines.

    For the seed snippets each is a single function definition, so this is
    a near-noop. We emit a tweak that still exercises the AST channel:
    inserting an extra do-nothing assignment at the top.
    """
    return "_helper = None\n" + source


def generate_cohort(
    n_unrelated: int = 60,
    n_exact: int = 15,
    n_renamed: int = 15,
    n_reordered: int = 10,
    seed: int = 0,
) -> list[CohortExample]:
    rng = random.Random(seed)
    out: list[CohortExample] = []
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"s-{counter:04d}"

    for _ in range(n_exact):
        a = rng.choice(_CLEAN_SNIPPETS)
        out.append(CohortExample(next_id(), next_id(), a, a, "exact_copy"))

    for _ in range(n_renamed):
        a = rng.choice(_CLEAN_SNIPPETS)
        b = _rename_identifiers(a)
        out.append(CohortExample(next_id(), next_id(), a, b, "renamed"))

    for _ in range(n_reordered):
        a = rng.choice(_CLEAN_SNIPPETS)
        b = _reorder_top_level_defs(a)
        out.append(CohortExample(next_id(), next_id(), a, b, "reordered"))

    for _ in range(n_unrelated):
        a, b = rng.sample(_CLEAN_SNIPPETS, 2)
        out.append(CohortExample(next_id(), next_id(), a, b, "unrelated"))

    rng.shuffle(out)
    return out
