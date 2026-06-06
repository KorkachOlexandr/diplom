"""Rule family: LLM refusal / capability disclosures pasted into code.

When a student asks an LLM for code that bumps a policy or capability
limit, the reply often opens with a refusal preamble. Students who paste
the whole reply leave those openers in. These rules look for refusal
phrasing specifically within comments or docstrings.
"""
from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


register(
    Rule(
        id="policy.im_sorry_but_in_comment",
        name="Comment: 'I'm sorry, but I cannot...'",
        family="policy",
        description=(
            "Refusal lede pasted into a comment or docstring. Very high "
            "precision."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*"
            r"\bi'?m\s+sorry,?\s+but\s+i\s+(?:cannot|can'?t|am\s+(?:not\s+able|unable))"
        ),
    )
)


register(
    Rule(
        id="policy.cannot_provide_in_comment",
        name="Comment: 'I cannot provide [implementation|code|...]'",
        family="policy",
        description=(
            "LLM refusal to produce code, left as a comment header on a "
            "stub function. Useful for catching half-completed submissions "
            "with the explanation copied verbatim."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*"
            r"\bi\s+(?:cannot|can'?t|am\s+(?:not\s+able|unable))\s+"
            r"(?:provide|generate|create|write|produce)\s+"
            r"(?:(?:the|a|an|complete|full|entire)\s+){0,3}"
            r"(?:implementation|code|solution|function|class|script)"
        ),
    )
)


register(
    Rule(
        id="policy.knowledge_cutoff_in_comment",
        name="Comment: knowledge-cutoff disclosure",
        family="policy",
        description=(
            "'My knowledge cutoff is …' or 'as of my last update …' in a "
            "comment. LLM-specific disclaimer with effectively zero "
            "false-positive rate."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*"
            r"\b(?:my\s+knowledge\s+cut[\s-]?off|as\s+of\s+my\s+"
            r"(?:last\s+update|training|knowledge\s+cut[\s-]?off))"
        ),
    )
)
