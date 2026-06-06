"""Winnowing fingerprinting (Schleimer, Wilkerson & Aiken, 2003).

This is the algorithm behind Moss. Concept in one sentence: slide a window
of size w over the rolling-hashed token sequence, pick the minimum hash in
each window (ties: rightmost), keep those as the document's fingerprints.
Guarantees that any matching substring of length ≥ w + k - 1 tokens
(noise threshold k, guarantee threshold w + k - 1) produces a shared
fingerprint, with documented density bounds.

We work on the normalized token sequence from tokenize_code.py, so
renaming variables, swapping literals, and changing whitespace all
collapse to identical fingerprints.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.signals.cohort.tokenize_code import Token


@dataclass(frozen=True)
class Fingerprint:
    """One winnowing fingerprint, with provenance for evidence rendering."""

    hash_value: int
    token_start_index: int   # index into the original Token list
    token_end_index: int     # exclusive
    start: int               # character offset (start of first token in the k-gram)
    end: int                 # character offset (end of last token in the k-gram)


# Rolling hash constants. Karp–Rabin with a Mersenne-prime modulus is
# overkill here; a 64-bit FNV-like multiplier is simpler and collision
# behavior matches the original paper closely enough for our scale.
_BASE = 257
_MOD = (1 << 61) - 1  # 2^61 - 1, a Mersenne prime


def _kgram_hashes(token_kinds: list[str], k: int) -> list[int]:
    """Rolling hash over k-grams of token kinds."""
    n = len(token_kinds)
    if n < k:
        return []
    base_pow = pow(_BASE, k - 1, _MOD)
    hashes: list[int] = []
    h = 0
    for i in range(k):
        h = (h * _BASE + (hash(token_kinds[i]) & 0xFFFFFFFF)) % _MOD
    hashes.append(h)
    for i in range(1, n - k + 1):
        out_tok = hash(token_kinds[i - 1]) & 0xFFFFFFFF
        in_tok = hash(token_kinds[i + k - 1]) & 0xFFFFFFFF
        h = ((h - out_tok * base_pow) * _BASE + in_tok) % _MOD
        hashes.append(h)
    return hashes


def fingerprints(tokens: list[Token], k: int = 5, w: int = 4) -> list[Fingerprint]:
    """Produce winnowed fingerprints. Defaults: k=5 token k-grams, window w=4.

    Following the original paper: of every w consecutive hashes, keep the
    minimum (and on ties, the rightmost). This gives the density guarantee
    while suppressing redundant fingerprints for long matches.
    """
    if len(tokens) < k:
        return []
    kinds = [t.kind for t in tokens]
    hashes = _kgram_hashes(kinds, k)
    n = len(hashes)
    out: list[Fingerprint] = []
    last_selected = -1

    for i in range(n - w + 1):
        window = hashes[i : i + w]
        # rightmost-minimum selection (Schleimer et al. §4)
        min_val = window[0]
        min_idx = 0
        for j in range(1, w):
            if window[j] <= min_val:
                min_val = window[j]
                min_idx = j
        absolute_idx = i + min_idx
        if absolute_idx == last_selected:
            continue
        last_selected = absolute_idx
        token_start = absolute_idx
        token_end = absolute_idx + k
        out.append(
            Fingerprint(
                hash_value=min_val,
                token_start_index=token_start,
                token_end_index=token_end,
                start=tokens[token_start].start,
                end=tokens[token_end - 1].end,
            )
        )
    return out


@dataclass(frozen=True)
class FingerprintMatch:
    other_id: str
    score: float                 # shared / min(|fp_a|, |fp_b|)
    shared_hashes: int
    spans: list[tuple[tuple[int, int], tuple[int, int]]]  # ((start_a, end_a), (start_b, end_b))


def compare_submissions(
    submissions: list[tuple[str, list[Fingerprint]]],
    min_score: float = 0.20,
    max_spans_per_pair: int = 6,
) -> list[tuple[str, str, FingerprintMatch]]:
    """Compute pairwise overlap between submissions by shared fingerprints.

    Returns symmetric list of (id_a, id_b, FingerprintMatch). Only pairs
    above min_score appear.
    """
    by_hash: dict[int, list[tuple[str, Fingerprint]]] = defaultdict(list)
    fp_count: dict[str, int] = {}
    for sub_id, fps in submissions:
        fp_count[sub_id] = len(fps)
        for fp in fps:
            by_hash[fp.hash_value].append((sub_id, fp))

    # collect shared hashes per ordered pair
    pair_shares: dict[tuple[str, str], list[tuple[Fingerprint, Fingerprint]]] = defaultdict(list)
    for _, owners in by_hash.items():
        if len(owners) < 2:
            continue
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                sa, fa = owners[i]
                sb, fb = owners[j]
                if sa == sb:
                    continue
                key = tuple(sorted((sa, sb)))
                if key[0] == sa:
                    pair_shares[key].append((fa, fb))
                else:
                    pair_shares[key].append((fb, fa))

    out: list[tuple[str, str, FingerprintMatch]] = []
    for (id_a, id_b), shares in pair_shares.items():
        # Jaccard over the fingerprint sets: |A ∩ B| / |A ∪ B|. More
        # conservative than the shared/min(...) ratio Moss originally
        # used; less prone to inflating scores when one submission is
        # much shorter than the other (a common edge case in mixed-
        # length student work).
        shared = len(shares)
        union = fp_count[id_a] + fp_count[id_b] - shared
        score = shared / union if union else 0.0
        if score < min_score:
            continue
        # pick the most-informative spans: longest character-span first
        shares.sort(key=lambda p: (p[0].end - p[0].start), reverse=True)
        spans: list[tuple[tuple[int, int], tuple[int, int]]] = [
            ((fa.start, fa.end), (fb.start, fb.end))
            for fa, fb in shares[:max_spans_per_pair]
        ]
        out.append(
            (
                id_a,
                id_b,
                FingerprintMatch(
                    other_id=id_b,
                    score=score,
                    shared_hashes=len(shares),
                    spans=spans,
                ),
            )
        )
    return out
