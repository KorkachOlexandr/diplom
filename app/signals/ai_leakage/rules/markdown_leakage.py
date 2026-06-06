from __future__ import annotations

import re

from app.signals.ai_leakage.engine import Rule, register


# Family: Markdown formatting leakage into a plain-prose context.
#
# Higher false-positive risk than the other families — students who happen
# to know Markdown legitimately use these constructs. To keep precision up,
# we require *multiple* instances within the same submission before firing.
# The thesis discusses this design tradeoff explicitly.


_BOLD_RE = re.compile(r"\*\*[^*\n]{2,80}\*\*")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)
_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def _bold_in_prose(text: str) -> list[tuple[int, int, str]]:
    matches = list(_BOLD_RE.finditer(text))
    if len(matches) < 3:
        return []
    return [(m.start(), m.end(), m.group(0)) for m in matches]


def _markdown_headings(text: str) -> list[tuple[int, int, str]]:
    matches = list(_HEADING_RE.finditer(text))
    if len(matches) < 2:
        return []
    return [(m.start(), m.end(), m.group(0).strip()) for m in matches]


def _code_fences(text: str) -> list[tuple[int, int, str]]:
    matches = list(_FENCE_RE.finditer(text))
    if len(matches) < 2:
        return []
    return [(m.start(), m.end(), m.group(0)) for m in matches]


register(
    Rule(
        id="markdown.bold_in_prose",
        name="Markdown bold in plain prose (3+ occurrences)",
        family="markdown_leak",
        description=(
            "Multiple **bold** spans in a context that isn't being rendered as "
            "Markdown. Common when students paste LLM output into a plain Doc "
            "without stripping the asterisks. Threshold of three suppresses "
            "false positives from students who legitimately know Markdown."
        ),
        detector=_bold_in_prose,
    )
)


register(
    Rule(
        id="markdown.headings_in_prose",
        name="Markdown headings in plain prose (2+ occurrences)",
        family="markdown_leak",
        description=(
            "Multiple lines starting with `#`/`##`/`###` in a submission that "
            "isn't being rendered as Markdown. Strong LLM-output signature."
        ),
        detector=_markdown_headings,
    )
)


register(
    Rule(
        id="markdown.code_fences_in_prose",
        name="Triple-backtick fences in a non-code submission",
        family="markdown_leak",
        description=(
            "Two or more ``` fences appearing in an otherwise prose submission. "
            "Very rare outside of pasted LLM responses."
        ),
        detector=_code_fences,
    )
)
