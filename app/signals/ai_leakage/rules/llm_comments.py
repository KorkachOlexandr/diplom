"""Rule family: LLM-style comments left in source code.

These detect comments and docstrings that read like ChatGPT/Claude/Copilot
replies to a coding prompt — "Here's the function you asked for", "As an
AI language model", and so on. Pasting LLM output and not stripping the
prose comments is one of the most common LLM-misuse failure modes in
student programming submissions.
"""
from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


register(
    Rule(
        id="comment.heres_the",
        name="Comment: 'Here's the [function|code|solution]...'",
        family="llm_comment",
        description=(
            "Service-language comment pasted from an LLM reply: "
            "'# Here's the function you requested', '// Here is the code:'. "
            "Near-zero false-positive rate in student code."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')\s*here\s*(?:is|'s|are)\s+(?:the|a|an|your|"
            r"my)\s+(?:function|code|solution|implementation|class|method|"
            r"answer|response|script)"
        ),
    )
)


register(
    Rule(
        id="comment.certainly_heres",
        name="Comment: 'Certainly! Here is...'",
        family="llm_comment",
        description=(
            "ChatGPT/Claude preamble landing inside a comment block or "
            "docstring, e.g. '# Certainly! Here is your sorting function.'"
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')\s*(?:certainly|sure|of course|absolutely)"
            r"[!,]?\s+(?:here|i'?ll|let\s+me)"
        ),
    )
)


register(
    Rule(
        id="comment.as_an_ai",
        name="Comment: 'As an AI language model...'",
        family="llm_comment",
        description=(
            "Self-identification of an LLM caught inside a comment. "
            "Essentially never written by humans."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*\bas\s+an?\s+"
            r"(?:ai|large\s+language\s+model|language\s+model|"
            r"artificial\s+intelligence)\b"
        ),
    )
)


register(
    Rule(
        id="comment.i_hope_this_helps",
        name="Comment: 'I hope this helps' sign-off",
        family="llm_comment",
        description=(
            "Service-style sign-off LLMs append to coding replies "
            "('I hope this helps!', 'Hope this helps!', 'Let me know if you "
            "have any questions'), pasted into the source unchanged. "
            "Prefix-free by design — the phrase is distinctive enough that "
            "it indicates LLM origin whether it lands in a # comment or "
            "inside a triple-quoted docstring block."
        ),
        detector=regex_detector(
            r"\b("
            r"i\s+hope\s+this\s+helps|"
            r"hope\s+this\s+helps|"
            r"let\s+me\s+know\s+if\s+you\s+have\s+(?:any\s+)?questions|"
            r"feel\s+free\s+to\s+ask"
            r")\b"
        ),
    )
)


register(
    Rule(
        id="comment.explanation_block",
        name="Comment: 'This function does X' explanatory preamble",
        family="llm_comment",
        description=(
            "Long explanatory natural-language comment preceding a function, "
            "matching the pedagogical-explanation style LLMs default to: "
            "'This function takes X and returns Y. It works by ...'."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')\s*this\s+(?:function|method|class|code|"
            r"script|program)\s+(?:takes|accepts|receives|returns|"
            r"calculates|implements|demonstrates|shows)"
        ),
    )
)
