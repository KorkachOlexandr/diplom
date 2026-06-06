"""Rule family: LLM boilerplate patterns in source code.

Patterns characteristic of LLM-generated code that aren't strictly invalid
but appear together far more often in pasted LLM output than in student-
authored code: the 'main' guard with 'example usage' comments, defensive
type-checking on every parameter, etc. These are individually weak signals;
together (and with the comment-family rules) they form circumstantial
evidence the teacher can corroborate.
"""
from __future__ import annotations

import re

from app.signals.ai_leakage.engine import Rule, register


_EXAMPLE_USAGE_RE = re.compile(
    r"(?:#|//|\"\"\"|''')\s*example\s+usage\s*:?", re.IGNORECASE
)


def _example_usage(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _EXAMPLE_USAGE_RE.finditer(text)]


_TIME_COMPLEXITY_RE = re.compile(
    r"(?:#|//|\"\"\"|''')[^\n]*time\s+complexity\s*:?\s*O\s*\([^)]+\)",
    re.IGNORECASE,
)


def _time_complexity(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _TIME_COMPLEXITY_RE.finditer(text)]


_NOTE_BLOCK_RE = re.compile(
    r"(?:#|//|\"\"\"|''')\s*note\s*:\s*\S",
    re.IGNORECASE,
)


def _note_block(text: str) -> list[tuple[int, int, str]]:
    matches = list(_NOTE_BLOCK_RE.finditer(text))
    if len(matches) < 2:
        return []
    return [(m.start(), m.end(), m.group(0)) for m in matches]


register(
    Rule(
        id="boilerplate.example_usage_comment",
        name="Boilerplate: 'Example usage:' comment block",
        family="llm_boilerplate",
        description=(
            "LLMs love to append demonstration call sites under a "
            "'# Example usage:' header. Plenty of real students also do "
            "this, so this rule is one piece of a wider picture rather than "
            "a standalone verdict."
        ),
        detector=_example_usage,
    )
)


register(
    Rule(
        id="boilerplate.time_complexity_inline",
        name="Boilerplate: inline 'Time complexity: O(...)' comment",
        family="llm_boilerplate",
        description=(
            "Inline complexity annotations are a strong tell of LLM-generated "
            "explanations dropped into a comment. Honest students more often "
            "discuss complexity in prose or skip it entirely."
        ),
        detector=_time_complexity,
    )
)


register(
    Rule(
        id="boilerplate.note_blocks_repeated",
        name="Boilerplate: multiple 'Note:' comment blocks",
        family="llm_boilerplate",
        description=(
            "Two or more '# Note:' / '\"\"\"Note:' blocks in the same file. "
            "LLMs love adding sidenotes after every other function. Required "
            "threshold of two suppresses the single-note false positive."
        ),
        detector=_note_block,
    )
)
