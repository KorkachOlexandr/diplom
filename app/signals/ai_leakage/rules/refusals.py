from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


# Family: self-identification / refusal artifacts. These are near-zero false-positive.

register(
    Rule(
        id="refusal.as_an_ai",
        name="Self-identification: 'As an AI language model...'",
        family="refusal",
        description=(
            "The textbook LLM self-disclosure. Essentially never written by humans."
        ),
        detector=regex_detector(
            r"\bas\s+an?\s+(ai|large\s+language\s+model|language\s+model|"
            r"artificial\s+intelligence)\b"
        ),
    )
)

register(
    Rule(
        id="refusal.i_cannot",
        name="Refusal artifact: 'I cannot/can't [provide|generate]...'",
        family="refusal",
        description=(
            "LLM refusal phrasing left in the pasted output. Students copying "
            "a partial refusal often leave the opener intact."
        ),
        detector=regex_detector(
            r"\bi\s+(cannot|can'?t|am\s+(not\s+able|unable))\s+"
            r"(provide|generate|create|produce|assist\s+with|help\s+with)"
        ),
    )
)

register(
    Rule(
        id="refusal.knowledge_cutoff",
        name="Knowledge-cutoff disclosure",
        family="refusal",
        description=(
            "Phrases like 'my knowledge cutoff is...' or 'as of my last update' "
            "are LLM-specific disclaimers."
        ),
        detector=regex_detector(
            r"\b(my\s+knowledge\s+cut[\s-]?off|as\s+of\s+my\s+(last\s+update|"
            r"training|knowledge\s+cut[\s-]?off))"
        ),
    )
)
