"""Fuse the winnowing and AST-subtree channels into CohortMatch lists.

Both channels are CPU-cheap and use only the stdlib; both always run.
The thesis discusses the complementary failure modes:

- Winnowing survives renaming and reformatting but is sensitive to
  statement reordering and function extraction.
- AST subtree hashing survives structural-equivalence edits but is
  empty for any file that doesn't parse.

For unparseable submissions (very common in student work) only the
winnowing channel produces evidence — that fallback is deliberate.
"""
from __future__ import annotations

import logging

from app.report.model import CohortMatch, CohortSpan, SubmissionReport
from app.signals.cohort.ast_hash import compare_subtrees, subtree_hashes
from app.signals.cohort.tokenize_code import detect_language, tokenize_source
from app.signals.cohort.winnowing import compare_submissions, fingerprints


log = logging.getLogger(__name__)

# Tuning knobs documented in Phase 5 evaluation chapter.
# WINNOW_MIN_SCORE is intentionally above the noise floor for small
# functions: at ~30 tokens, unrelated Python files share common k-grams
# like `def IDENT ( IDENT ) :` that drag the false-match rate up. 0.40
# is the empirical knee where exact and renamed copies still register
# (~0.9+) while unrelated short functions stay below.
WINNOW_K = 5
WINNOW_W = 4
WINNOW_MIN_SCORE = 0.40
# AST_MIN_SCORE is set above the empirical noise floor for small functions.
# Below ~0.45, two unrelated recursive functions can collide on shared
# patterns like `f(n - NUM) + f(n - NUM)` after identifier normalization
# (recursive vs memoized fib hit ~0.30 on default settings).
AST_MIN_SCORE = 0.45
MAX_SPANS_PER_MATCH = 4


def find_matches(submissions: list[SubmissionReport]) -> dict[str, list[CohortMatch]]:
    matches: dict[str, list[CohortMatch]] = {s.submission_id: [] for s in submissions}
    if len(submissions) < 2:
        return matches

    sub_by_id = {s.submission_id: s for s in submissions}
    name_by_id = {s.submission_id: s.student_name for s in submissions}

    _run_winnowing_channel(submissions, sub_by_id, name_by_id, matches)
    _run_ast_channel(submissions, sub_by_id, name_by_id, matches)

    for sid in matches:
        matches[sid].sort(key=lambda m: m.score, reverse=True)
    return matches


def _run_winnowing_channel(
    submissions: list[SubmissionReport],
    sub_by_id: dict[str, SubmissionReport],
    name_by_id: dict[str, str],
    matches: dict[str, list[CohortMatch]],
) -> None:
    fps_by_sub: list[tuple[str, list]] = []
    for s in submissions:
        if not s.text:
            continue
        try:
            tokens = tokenize_source(s.text)
        except Exception as e:  # noqa: BLE001 — never fail the whole scan on one file
            log.warning("tokenize failed for %s: %s", s.submission_id, e)
            continue
        fps = fingerprints(tokens, k=WINNOW_K, w=WINNOW_W)
        fps_by_sub.append((s.submission_id, fps))

    pairs = compare_submissions(fps_by_sub, min_score=WINNOW_MIN_SCORE)

    for id_a, id_b, m in pairs:
        text_a = sub_by_id[id_a].text
        text_b = sub_by_id[id_b].text
        spans_a_to_b: list[CohortSpan] = []
        spans_b_to_a: list[CohortSpan] = []
        for (a_start, a_end), (b_start, b_end) in m.spans[:MAX_SPANS_PER_MATCH]:
            spans_a_to_b.append(
                CohortSpan(
                    this_span=(a_start, a_end),
                    other_span=(b_start, b_end),
                    this_excerpt=_truncate(text_a[a_start:a_end]),
                    other_excerpt=_truncate(text_b[b_start:b_end]),
                )
            )
            spans_b_to_a.append(
                CohortSpan(
                    this_span=(b_start, b_end),
                    other_span=(a_start, a_end),
                    this_excerpt=_truncate(text_b[b_start:b_end]),
                    other_excerpt=_truncate(text_a[a_start:a_end]),
                )
            )
        matches[id_a].append(
            CohortMatch(
                other_submission_id=id_b,
                other_student_name=name_by_id[id_b],
                channel="winnowing",
                score=float(m.score),
                spans=spans_a_to_b,
            )
        )
        matches[id_b].append(
            CohortMatch(
                other_submission_id=id_a,
                other_student_name=name_by_id[id_a],
                channel="winnowing",
                score=float(m.score),
                spans=spans_b_to_a,
            )
        )


def _run_ast_channel(
    submissions: list[SubmissionReport],
    sub_by_id: dict[str, SubmissionReport],
    name_by_id: dict[str, str],
    matches: dict[str, list[CohortMatch]],
) -> None:
    hashes_by_sub: list[tuple[str, list]] = []
    for s in submissions:
        if not s.text:
            continue
        hashes_by_sub.append((s.submission_id, subtree_hashes(s.text)))

    pairs = compare_subtrees(hashes_by_sub, min_score=AST_MIN_SCORE)

    for id_a, id_b, m in pairs:
        excerpt = (
            f"{m.shared_subtrees} shared AST subtrees "
            f"(largest = {m.largest_subtree} nodes)"
        )
        summary_span = CohortSpan(
            this_span=(0, 0),
            other_span=(0, 0),
            this_excerpt=excerpt,
            other_excerpt=excerpt,
        )
        matches[id_a].append(
            CohortMatch(
                other_submission_id=id_b,
                other_student_name=name_by_id[id_b],
                channel="ast",
                score=float(m.score),
                spans=[summary_span],
            )
        )
        matches[id_b].append(
            CohortMatch(
                other_submission_id=id_a,
                other_student_name=name_by_id[id_a],
                channel="ast",
                score=float(m.score),
                spans=[summary_span],
            )
        )


def _truncate(s: str, n: int = 500) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
