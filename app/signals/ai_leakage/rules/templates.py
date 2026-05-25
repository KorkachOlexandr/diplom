from __future__ import annotations

import re

from app.signals.ai_leakage.engine import Rule, regex_detector, register


# Family: template / placeholder artifacts that should have been filled in.
# These are user-asked-for; the student literally pasted instructions back.

register(
    Rule(
        id="template.bracket_placeholder",
        name="Unfilled bracket placeholder: '[Your Name]', '[Insert Date]', ...",
        family="template",
        description=(
            "Square-bracket placeholders that students forget to fill in. "
            "High precision; the bracket form is uncommon in normal prose."
        ),
        detector=regex_detector(
            r"\[\s*(your\s+name|insert\s+\w+|name\s+here|date\s+here|"
            r"student\s+name|date|topic|class|professor|instructor)\s*\]"
        ),
    )
)


# Family: instruction echo — the student pasted a prompt or its rewording.
_INSTRUCTION_PATTERNS = re.compile(
    r"\b(please\s+(enter|write|provide|insert|fill\s+in)\s+(your\s+)?"
    r"(name|date|topic|response|answer)|"
    r"write\s+(an?\s+)?(essay|paragraph|response)\s+about|"
    r"the\s+following\s+is\s+(an?\s+)?\w+\s+(essay|response|paragraph)\s+about)\b",
    re.IGNORECASE,
)


def _instruction_echo(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _INSTRUCTION_PATTERNS.finditer(text)]


register(
    Rule(
        id="template.instruction_echo",
        name="Instruction echo: prompt-like phrasing left in the submission",
        family="template",
        description=(
            "Phrases like 'Please enter your name', 'Write an essay about', or "
            "'The following is an essay about ...' indicate the student pasted "
            "the prompt back instead of removing it."
        ),
        detector=_instruction_echo,
    )
)
