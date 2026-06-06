"""Rule family: Markdown formatting leaking into source code.

The single highest-precision tell of carelessly pasted LLM output: triple-
backtick code fences left in a .py file. LLMs wrap code in ``` for the
chat UI; when a student copies the whole block (including the fence), the
fence ends up in the source file. No legitimate Python program contains
``` at column 0.
"""
from __future__ import annotations

import re

from app.signals.ai_leakage.engine import Rule, register


_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)


def _fence(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _FENCE_RE.finditer(text)]


_LANG_FENCE_RE = re.compile(r"^\s*```(?:python|py|javascript|js|java|cpp|c\+\+|c)\b", re.IGNORECASE | re.MULTILINE)


def _lang_fence(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _LANG_FENCE_RE.finditer(text)]


_PROSE_BOLD_RE = re.compile(r"\*\*[A-Za-z][^*\n]{2,50}\*\*")


def _bold_prose(text: str) -> list[tuple[int, int, str]]:
    # Require at least two occurrences AND that they sit on lines that
    # don't start with structural code characters — suppresses operator-
    # heavy false positives like `x ** 2`.
    candidates = []
    for m in _PROSE_BOLD_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_prefix = text[line_start : m.start()].lstrip()
        if line_prefix and line_prefix[0] in "+-*/=<>(){}[]":
            continue
        candidates.append(m)
    if len(candidates) < 2:
        return []
    return [(m.start(), m.end(), m.group(0)) for m in candidates]


register(
    Rule(
        id="markdown.code_fence_in_source",
        name="Markdown ``` fence left in a source file",
        family="markdown_leak",
        description=(
            "Triple-backtick lines in a .py / .cpp / .java file. No "
            "legitimate program contains these; they're the unambiguous "
            "footprint of a student copying the LLM chat UI verbatim."
        ),
        detector=_fence,
    )
)


register(
    Rule(
        id="markdown.language_fence_in_source",
        name="Markdown ```python fence in source",
        family="markdown_leak",
        description=(
            "Language-tagged fences specifically (```python, ```java, "
            "```cpp). High-confidence superset of the bare-fence rule for "
            "thesis evidence tables."
        ),
        detector=_lang_fence,
    )
)


register(
    Rule(
        id="markdown.bold_in_code",
        name="Markdown **bold** prose in source (2+ occurrences)",
        family="markdown_leak",
        description=(
            "Multiple **bold** spans on prose-style lines inside a source "
            "file. Suppresses Python `x ** 2` operator chains by ignoring "
            "occurrences whose line starts with an operator character. "
            "Designed to surface pasted LLM markdown that survives the copy."
        ),
        detector=_bold_prose,
    )
)
