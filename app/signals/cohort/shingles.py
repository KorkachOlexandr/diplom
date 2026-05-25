from __future__ import annotations

# Phase 2: MinHash/LSH on word k-shingles for cheap near-duplicate detection.
# Stubbed for Phase 1.


def build_index(submissions: list[tuple[str, str]]) -> object:
    """Return a placeholder index for (submission_id, text) pairs."""
    return None


def near_duplicate_pairs(index: object, threshold: float = 0.7) -> list[tuple[str, str, float]]:
    """Return list of (id_a, id_b, jaccard) above threshold."""
    return []
