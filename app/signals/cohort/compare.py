"""Fuse the MinHash and embedding channels into per-submission CohortMatch lists.

MinHash always runs (datasketch is a hard dep). Embedding paraphrase
detection is optional — if sentence-transformers isn't installed, we log
once and continue with MinHash-only output, which is what the thesis
defends as the "always available" cohort signal.
"""
from __future__ import annotations

import logging

from app.report.model import CohortMatch, SubmissionReport
from app.signals.cohort.shingles import longest_matching_span, near_duplicate_pairs


log = logging.getLogger(__name__)


# Tuning. Both thresholds are documented in the plan's evaluation chapter
# and will be revisited in Phase 5 after the PR curves come in.
MINHASH_LSH_THRESHOLD = 0.3   # LSH candidate band; pair-level score still reported
MIN_SPAN_CHARS = 60           # ignore short coincidental matches
EMBEDDING_THRESHOLD = 0.85    # cosine cutoff for paraphrase pairs
MAX_EMBEDDING_HITS_PER_PAIR = 3


def find_matches(submissions: list[SubmissionReport]) -> dict[str, list[CohortMatch]]:
    matches: dict[str, list[CohortMatch]] = {s.submission_id: [] for s in submissions}
    if len(submissions) < 2:
        return matches

    sub_by_id = {s.submission_id: s for s in submissions}
    name_by_id = {s.submission_id: s.student_name for s in submissions}

    _run_minhash_channel(submissions, sub_by_id, name_by_id, matches)
    _run_embedding_channel(submissions, name_by_id, matches)

    # Sort each submission's matches highest-score first for the UI.
    for sid in matches:
        matches[sid].sort(key=lambda m: m.score, reverse=True)
    return matches


def _run_minhash_channel(
    submissions: list[SubmissionReport],
    sub_by_id: dict[str, SubmissionReport],
    name_by_id: dict[str, str],
    matches: dict[str, list[CohortMatch]],
) -> None:
    items = [(s.submission_id, s.text) for s in submissions if s.text]
    pairs = near_duplicate_pairs(items, threshold=MINHASH_LSH_THRESHOLD)

    for id_a, id_b, jaccard in pairs:
        text_a = sub_by_id[id_a].text
        text_b = sub_by_id[id_b].text
        span = longest_matching_span(text_a, text_b, min_chars=MIN_SPAN_CHARS)
        if span is None:
            continue
        (a_start, a_end), (b_start, b_end), exc_a, exc_b = span
        matches[id_a].append(
            CohortMatch(
                other_submission_id=id_b,
                other_student_name=name_by_id[id_b],
                channel="minhash",
                score=float(jaccard),
                this_span=(a_start, a_end),
                other_span=(b_start, b_end),
                this_excerpt=_truncate(exc_a),
                other_excerpt=_truncate(exc_b),
            )
        )
        matches[id_b].append(
            CohortMatch(
                other_submission_id=id_a,
                other_student_name=name_by_id[id_a],
                channel="minhash",
                score=float(jaccard),
                this_span=(b_start, b_end),
                other_span=(a_start, a_end),
                this_excerpt=_truncate(exc_b),
                other_excerpt=_truncate(exc_a),
            )
        )


def _run_embedding_channel(
    submissions: list[SubmissionReport],
    name_by_id: dict[str, str],
    matches: dict[str, list[CohortMatch]],
) -> None:
    try:
        from app.signals.cohort.embeddings import EmbeddingIndex
    except ImportError:
        log.info("sentence-transformers not installed; skipping embedding channel")
        return

    index = EmbeddingIndex()
    try:
        for s in submissions:
            if s.text:
                index.add(s.submission_id, s.text)
        pairs = index.paraphrase_pairs(threshold=EMBEDDING_THRESHOLD)
    except Exception as e:  # noqa: BLE001 — embedding path is non-critical; degrade gracefully
        log.warning("embedding channel failed: %s: %s", type(e).__name__, e)
        return

    # Group by (a, b) so we can cap how many sentence pairs per submission pair.
    grouped: dict[tuple[str, str], list[tuple]] = {}
    for entry in pairs:
        id_a, id_b = entry[0], entry[1]
        grouped.setdefault((id_a, id_b), []).append(entry)

    for (id_a, id_b), entries in grouped.items():
        entries.sort(key=lambda e: e[6], reverse=True)
        for id_a_, id_b_, span_a, span_b, sent_a, sent_b, cosine in entries[
            :MAX_EMBEDDING_HITS_PER_PAIR
        ]:
            matches[id_a].append(
                CohortMatch(
                    other_submission_id=id_b,
                    other_student_name=name_by_id[id_b],
                    channel="embedding",
                    score=cosine,
                    this_span=span_a,
                    other_span=span_b,
                    this_excerpt=_truncate(sent_a),
                    other_excerpt=_truncate(sent_b),
                )
            )
            matches[id_b].append(
                CohortMatch(
                    other_submission_id=id_a,
                    other_student_name=name_by_id[id_a],
                    channel="embedding",
                    score=cosine,
                    this_span=span_b,
                    other_span=span_a,
                    this_excerpt=_truncate(sent_b),
                    other_excerpt=_truncate(sent_a),
                )
            )


def _truncate(s: str, n: int = 500) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
