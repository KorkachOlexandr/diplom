from __future__ import annotations

from app.signals.ai_leakage.engine import Rule, regex_detector, register


# Family: model self-identification. Near-zero false-positive rate — humans
# essentially never refer to themselves as ChatGPT/Claude/Gemini/etc.


register(
    Rule(
        id="self_id.named_model",
        name="Self-identification: 'I am [ChatGPT|Claude|Gemini|...]'",
        family="self_id",
        description=(
            "First-person reference to a specific LLM product name. "
            "Catches submissions where the student left in a model's "
            "self-introduction."
        ),
        detector=regex_detector(
            r"\b(i\s+am|i'?m)\s+"
            r"(chat\s?gpt|claude|gemini|bard|bing|copilot|llama|mistral|deepseek|"
            r"openai'?s\s+assistant|anthropic'?s\s+assistant|google'?s\s+assistant)\b"
        ),
    )
)


register(
    Rule(
        id="self_id.trained_by",
        name="Self-identification: 'trained by [OpenAI|Anthropic|...]'",
        family="self_id",
        description=(
            "Provenance disclosure typical of LLM responses to 'who made you'. "
            "Extremely rare in human writing."
        ),
        detector=regex_detector(
            r"\btrained\s+(by|on)\s+(openai|anthropic|google\s+deepmind|"
            r"google|meta|microsoft)\b"
        ),
    )
)


register(
    Rule(
        id="self_id.developed_by",
        name="Self-identification: 'developed/created by [vendor]'",
        family="self_id",
        description=(
            "Vendor attribution that an LLM emits when describing itself. "
            "Filters to the specific vendors that ship public LLMs."
        ),
        detector=regex_detector(
            r"\b(developed|created|made|built)\s+by\s+"
            r"(openai|anthropic|google|meta(\s+ai)?|microsoft|mistral\s+ai|deepseek)\b"
        ),
    )
)
