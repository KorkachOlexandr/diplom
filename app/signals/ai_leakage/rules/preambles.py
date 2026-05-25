from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


# Family: assistant-style preambles a student forgot to strip when pasting.
# High precision because no one writes this naturally in an essay opener.

register(
    Rule(
        id="preamble.certainly_heres",
        name="Assistant preamble: 'Certainly! Here is/are...'",
        family="preamble",
        description=(
            "Opening assistant-style preamble characteristic of ChatGPT / Claude "
            "responses. Students copying without editing leave this in."
        ),
        detector=regex_detector(
            r"\b(certainly|sure|of course|absolutely)[!,]?\s+"
            r"(here(?:'s|\s+(?:is|are))|i'?ll|let\s+me|i\s+can|below\s+is)"
        ),
    )
)

register(
    Rule(
        id="preamble.happy_to_help",
        name="Assistant preamble: 'I'd be happy to...'",
        family="preamble",
        description="Service-language opener typical of LLM responses.",
        detector=regex_detector(
            r"\b(i('?d| would) be (happy|glad|delighted) to|i'?m happy to help)"
        ),
    )
)

register(
    Rule(
        id="preamble.heres_a",
        name="Assistant preamble: 'Here's a/an ...essay/summary/...'",
        family="preamble",
        description=(
            "Opening 'Here's a/an [essay|summary|response|analysis|...]' framing — "
            "common when an LLM is asked to write a piece and the student pastes the reply."
        ),
        detector=regex_detector(
            r"^\s*here'?s\s+(?:a|an)(?:\s+[\w-]+){0,4}\s+"
            r"(essay|response|summary|analysis|answer|overview|explanation|breakdown)"
        ),
    )
)
