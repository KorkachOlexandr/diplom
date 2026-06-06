from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


# Family: policy / capability refusal phrasing. These are the openers of
# refusals or capability disclosures that LLMs emit when they can't or
# won't fully answer a prompt. Students who paste the whole reply often
# leave these intact.


register(
    Rule(
        id="policy.im_sorry_but",
        name="Refusal opener: 'I'm sorry, but I cannot/can't...'",
        family="policy",
        description=(
            "Stock LLM refusal lede. Very high precision — humans almost "
            "never apologize this way in essay-style writing."
        ),
        detector=regex_detector(
            r"\bi'?m\s+sorry,?\s+but\s+i\s+(cannot|can'?t|am\s+(not\s+able|unable))"
        ),
    )
)


register(
    Rule(
        id="policy.no_realtime",
        name="Capability disclosure: 'no access to real-time information'",
        family="policy",
        description=(
            "Standard LLM capability disclaimer. Distinctive enough that "
            "no human writer produces this phrasing in a school essay."
        ),
        detector=regex_detector(
            r"\b(i\s+do\s+not|i\s+don'?t|i\s+have\s+no)\s+have\s+access\s+to\s+"
            r"(real[\s-]?time|current|up[\s-]?to[\s-]?date|live)\s+"
            r"(information|data|news|events)"
        ),
    )
)


register(
    Rule(
        id="policy.cannot_browse",
        name="Capability disclosure: 'I can't browse the internet'",
        family="policy",
        description=(
            "LLM-specific tool-availability disclaimer. Pasted verbatim "
            "from chat replies."
        ),
        detector=regex_detector(
            r"\bi\s+(cannot|can'?t|am\s+(not\s+able|unable))\s+"
            r"(browse|access)\s+the\s+(internet|web)"
        ),
    )
)
