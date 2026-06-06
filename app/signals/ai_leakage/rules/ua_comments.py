"""Rule family: Ukrainian-language LLM comments in source code.

Closes the Ukrainian-language gap for the code-leakage taxonomy. Same
families as the English siblings (preamble, self-id, policy) but matched
inside the comment/docstring contexts that programming submissions use.
"""
from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


register(
    Rule(
        id="comment.ua_os_funktsiya",
        name="Ukrainian comment: 'Ось функція/код/розв'язок...'",
        family="llm_comment",
        description=(
            "Service-language Ukrainian comment from an LLM reply pasted "
            "into source: «# Ось функція, яку ви просили», «# Ось код для…», "
            "«# Ось розв'язок». Direct counterpart to the English "
            "comment.heres_the rule."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')\s*(?:ось|нижче|надаю)\s+"
            r"(?:функці[яю]|метод|клас|код|розв[''’`ʼ]?язок|"
            r"імплементаці[яю]|реалізаці[яю])"
        ),
    )
)


register(
    Rule(
        id="comment.ua_zvychaino_in_comment",
        name="Ukrainian comment: 'Звичайно/Звісно! Ось...'",
        family="llm_comment",
        description=(
            "Ukrainian-localized assistant preamble caught in a comment: "
            "«# Звичайно! Ось ваша функція…», «# Звісно, ось код…»."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')\s*(?:звичайно|звісно|безумовно)[!,]?\s+"
            r"(?:ось|нижче|надаю)"
        ),
    )
)


register(
    Rule(
        id="comment.ua_as_language_model",
        name="Ukrainian comment: 'Як мовна модель / штучний інтелект'",
        family="llm_comment",
        description=(
            "Ukrainian translation of the canonical AI self-disclosure, "
            "landed inside a comment. Forms: «Як мовна модель», «Як ШІ», "
            "«Як штучний інтелект»."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*\bяк\s+("
            r"мовн[аі]я?\s+модел[ьі]|"
            r"велик[аі]я?\s+мовн[аі]я?\s+модел[ьі]|"
            r"штучн[иі]й?\s+інтелект|"
            r"ші(?:\s*[-—–]\s*помічник)?"
            r")\b"
        ),
    )
)


register(
    Rule(
        id="comment.ua_spodivaius_dopomozhe",
        name="Ukrainian comment: 'Сподіваюся, це допоможе' sign-off",
        family="llm_comment",
        description=(
            "Service-style Ukrainian sign-off LLMs append to replies, left "
            "in a comment: «# Сподіваюся, це допоможе!», "
            "«# Якщо є питання — звертайтеся»."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*"
            r"(?:сподіваю(?:ся|сь),?\s+(?:це|що це)\s+допоможе|"
            r"якщо\s+(?:є|у\s+вас\s+є|виникнуть)\s+(?:питання|запитання)|"
            r"звертай(?:теся|тесь))"
        ),
    )
)


register(
    Rule(
        id="policy.ua_na_zhal",
        name="Ukrainian comment: 'На жаль, я не можу...'",
        family="policy",
        description=(
            "Ukrainian refusal opener pasted into a comment: «# На жаль, "
            "я не можу надати повний код…»."
        ),
        detector=regex_detector(
            r"(?:#|//|\"\"\"|''')[^\n]*"
            r"\bна\s+жаль,?\s+я\s+не\s+можу"
        ),
    )
)
