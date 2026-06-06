"""MinHash + LSH channel for near-duplicate detection across submissions.

Word k-shingling produces sets of overlapping word n-grams; MinHash LSH gives
us an estimated Jaccard similarity per pair in near-constant time. After LSH
identifies a candidate pair we use stdlib difflib.SequenceMatcher to surface
the longest contiguous matching span, which becomes the side-by-side evidence
in the teacher UI.
"""
from __future__ import annotations

import difflib
import re

from datasketch import MinHash, MinHashLSH


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def shingle(text: str, k: int = 5) -> set[str]:
    """Word k-shingles. Returns the set of overlapping k-grams as space-joined strings."""
    words = tokenize(text)
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def minhash(shingles: set[str], num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for s in shingles:
        m.update(s.encode("utf-8"))
    return m


def near_duplicate_pairs(
    submissions: list[tuple[str, str]],
    threshold: float = 0.3,
    k: int = 5,
    num_perm: int = 128,
) -> list[tuple[str, str, float]]:
    """Return (id_a, id_b, estimated_jaccard) for every candidate pair.

    threshold is the LSH approximate-Jaccard threshold; we go below the
    "exact duplicate" line (~0.8) on purpose so the same MinHash pass also
    surfaces partial reuse, which the span finder will then localize.
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    sigs: dict[str, MinHash] = {}

    for sid, text in submissions:
        sh = shingle(text, k=k)
        if not sh:
            continue
        sig = minhash(sh, num_perm=num_perm)
        sigs[sid] = sig
        lsh.insert(sid, sig)

    pairs: list[tuple[str, str, float]] = []
    seen: set[tuple[str, str]] = set()
    for sid, sig in sigs.items():
        for other in lsh.query(sig):
            if other == sid:
                continue
            key = tuple(sorted((sid, other)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((key[0], key[1], sigs[key[0]].jaccard(sigs[key[1]])))
    return pairs


def longest_matching_span(
    text_a: str, text_b: str, min_chars: int = 60
) -> tuple[tuple[int, int], tuple[int, int], str, str] | None:
    """Return the longest contiguous matching span between two texts.

    Uses difflib.SequenceMatcher (Ratcliff–Obershelp). Returns None if no
    match meets min_chars.
    """
    matcher = difflib.SequenceMatcher(None, text_a, text_b, autojunk=False)
    match = matcher.find_longest_match(0, len(text_a), 0, len(text_b))
    if match.size < min_chars:
        return None
    a_start, b_start, size = match.a, match.b, match.size
    return (
        (a_start, a_start + size),
        (b_start, b_start + size),
        text_a[a_start : a_start + size],
        text_b[b_start : b_start + size],
    )
