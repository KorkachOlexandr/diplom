from __future__ import annotations

# Phase 2: sentence-transformer encoding + FAISS index for paraphrase pairs.
# Stubbed for Phase 1.


def build_index(submissions: list[tuple[str, str]], model_name: str | None = None) -> object:
    """Return a placeholder index for (submission_id, text) pairs."""
    return None


def paraphrase_pairs(index: object, threshold: float = 0.85) -> list[tuple[str, str, float]]:
    """Return list of (id_a, id_b, cosine) above threshold."""
    return []
