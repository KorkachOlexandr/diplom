"""Synthetic dataset generator for the evaluation chapter.

Produces labeled fixtures for both signals without any external download:

- ai_leakage: clean essays + clean essays with known leakage patterns
  injected at specific positions. Each positive example is labeled with
  the rule_id it should fire.

- cohort: pairs of (text_a, text_b, relation) where relation is one of
  "unrelated", "exact_copy", or "paraphrase". The paraphrase variant is
  produced by deterministic sentence-level transformations (synonym
  swap, sentence reordering) so the embedding channel has something to
  detect without depending on an external paraphrasing model.

The point of the synthetic generator is reproducibility — the same seed
produces the same examples every time, and the thesis evaluation chapter
can cite exact dataset statistics.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


_CLEAN_TEXTS = [
    "Photosynthesis is the process by which plants convert sunlight into "
    "chemical energy stored in glucose. Chloroplasts house chlorophyll, "
    "which absorbs light in the red and blue parts of the spectrum.",

    "The French Revolution of 1789 reshaped European political order. The "
    "fall of the Bastille on 14 July became the symbolic break with the "
    "old regime and is commemorated each year as a national holiday.",

    "Newton's three laws describe the relationship between forces and "
    "motion. An object at rest stays at rest unless acted upon by an "
    "external force. Force equals mass times acceleration.",

    "Climate change refers to long-term shifts in temperatures and weather "
    "patterns. Human activities, particularly the burning of fossil fuels, "
    "have been the dominant driver since the mid-twentieth century.",

    "The mitochondrion is the energy-producing organelle of eukaryotic "
    "cells. ATP is synthesized through oxidative phosphorylation across "
    "the inner mitochondrial membrane.",

    "Shakespeare's Hamlet is structured as a revenge tragedy but spends "
    "most of its length deferring the revenge it sets up. The play's "
    "central question is what action is justified by what knowledge.",

    "The Roman Republic ended in 27 BCE when Octavian was granted the "
    "title Augustus. The transition was gradual; many republican forms "
    "survived for decades under what was effectively a monarchy.",

    "DNA is a double helix composed of two polynucleotide strands. The "
    "strands are held together by hydrogen bonds between complementary "
    "base pairs: adenine with thymine, cytosine with guanine.",
]


# Per-rule positive injection templates: (rule_id, prefix, suffix).
# The injected phrase is what the rule is designed to catch; we wrap it
# around a clean text to produce a realistic-looking positive.
_LEAKAGE_INJECTIONS: list[tuple[str, str, str]] = [
    ("preamble.certainly_heres", "Certainly! Here's a short essay:\n\n", ""),
    ("preamble.heres_a", "Here's a brief response about this topic:\n\n", ""),
    ("preamble.happy_to_help", "I'd be happy to help with this assignment.\n\n", ""),
    ("refusal.as_an_ai", "As an AI language model, I would note that ", ""),
    ("refusal.i_cannot", "I cannot provide a complete answer, but ", ""),
    ("refusal.knowledge_cutoff", "", "\n\nMy knowledge cutoff is 2023."),
    ("template.bracket_placeholder", "[Your Name]\n\n", ""),
    ("template.instruction_echo", "Please enter your name above. ", ""),
    ("self_id.named_model", "I am ChatGPT. ", ""),
    ("self_id.trained_by", "", "\n\nI was trained by OpenAI."),
    ("self_id.developed_by", "", "\n\nThis content was developed by Anthropic."),
    ("policy.im_sorry_but", "I'm sorry, but I cannot provide a complete essay. ", ""),
    ("policy.no_realtime", "", "\n\nI do not have access to real-time information."),
    ("policy.cannot_browse", "", "\n\nI cannot browse the internet for the latest sources."),
    (
        "markdown.bold_in_prose",
        "**Overview:** ",
        " The **chloroplasts** are the **key organelle**, and the **process** is critical.",
    ),
    (
        "markdown.headings_in_prose",
        "## Introduction\n\n",
        "\n\n## Conclusion\n\nIn short, this is the main idea.",
    ),
    (
        "markdown.code_fences_in_prose",
        "```\nexample\n```\n\n",
        "\n\n```\nanother\n```",
    ),
]


@dataclass(frozen=True)
class LeakageExample:
    text: str
    is_positive: bool
    expected_rule_id: str | None  # which rule should fire; None for negatives


def generate_ai_leakage(n_per_rule: int = 5, n_negative: int = 40, seed: int = 0) -> list[LeakageExample]:
    """Generate a labeled AI-leakage dataset.

    For each rule there are n_per_rule positive examples (clean text +
    injection); positives are paired with n_negative pure-clean negatives
    so the false-positive rate of each rule is also estimable.
    """
    rng = random.Random(seed)
    out: list[LeakageExample] = []
    for rule_id, prefix, suffix in _LEAKAGE_INJECTIONS:
        for _ in range(n_per_rule):
            base = rng.choice(_CLEAN_TEXTS)
            out.append(
                LeakageExample(
                    text=f"{prefix}{base}{suffix}",
                    is_positive=True,
                    expected_rule_id=rule_id,
                )
            )
    for _ in range(n_negative):
        base = rng.choice(_CLEAN_TEXTS)
        out.append(LeakageExample(text=base, is_positive=False, expected_rule_id=None))
    rng.shuffle(out)
    return out


@dataclass(frozen=True)
class CohortExample:
    id_a: str
    id_b: str
    text_a: str
    text_b: str
    relation: str  # "unrelated" | "exact_copy" | "paraphrase"


_SYNONYMS = {
    "important": "significant",
    "process": "procedure",
    "describe": "explain",
    "produce": "generate",
    "shift": "change",
    "convert": "transform",
    "reshape": "transform",
    "central": "main",
    "primary": "main",
    "structure": "organize",
}


def _paraphrase(text: str, rng: random.Random) -> str:
    """Deterministic shallow paraphrase: synonym substitution + sentence reorder."""
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    rng.shuffle(sentences)
    transformed: list[str] = []
    for s in sentences:
        words = s.split(" ")
        out_words = []
        for w in words:
            lw = w.lower().strip(",;:")
            if lw in _SYNONYMS:
                out_words.append(_SYNONYMS[lw])
            else:
                out_words.append(w)
        transformed.append(" ".join(out_words))
    return ". ".join(transformed) + "."


def generate_cohort(
    n_unrelated: int = 60,
    n_exact: int = 20,
    n_paraphrase: int = 20,
    seed: int = 0,
) -> list[CohortExample]:
    rng = random.Random(seed)
    out: list[CohortExample] = []
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"s-{counter:04d}"

    # Exact copies.
    for _ in range(n_exact):
        a = rng.choice(_CLEAN_TEXTS)
        out.append(CohortExample(next_id(), next_id(), a, a, "exact_copy"))

    # Paraphrases.
    for _ in range(n_paraphrase):
        a = rng.choice(_CLEAN_TEXTS)
        b = _paraphrase(a, rng)
        out.append(CohortExample(next_id(), next_id(), a, b, "paraphrase"))

    # Unrelated pairs from different source texts.
    pool = list(_CLEAN_TEXTS)
    for _ in range(n_unrelated):
        a, b = rng.sample(pool, 2)
        out.append(CohortExample(next_id(), next_id(), a, b, "unrelated"))

    rng.shuffle(out)
    return out
