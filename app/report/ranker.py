from __future__ import annotations

from app.report.model import ScanReport, SubmissionReport


# Phase 1 ranker: a transparent weighted sum over per-signal counts/scores.
# This is intentionally simple and documented. Phase 5 evaluates and may
# tune the weights against NDCG / precision-at-k on the mixed-assignment
# eval set.
#
# Rationale for the current balance:
# - leakage hits are *high-precision-by-design* (every rule is a measured
#   operating point). One hit is strong evidence; we weight it heavily.
# - cohort matches on intro-CS problems (bubble_sort, fib, etc.) cluster
#   easily because the algorithm itself is a shared fingerprint. We weight
#   the *Jaccard score* of the match rather than the count, so two
#   submissions sharing ~all their tokens dominate two submissions sharing
#   the common idiom.
WEIGHTS = {
    "leakage": 3.0,
    "cohort_winnowing": 5.0,
    "cohort_ast": 3.0,
    "web": 3.0,
}


def submission_suspicion(report: SubmissionReport) -> float:
    score = 0.0
    score += WEIGHTS["leakage"] * len(report.leakage_hits)
    for m in report.cohort_matches:
        if m.channel == "winnowing":
            score += WEIGHTS["cohort_winnowing"] * m.score
        elif m.channel == "ast":
            score += WEIGHTS["cohort_ast"] * m.score
    score += WEIGHTS["web"] * sum(h.score for h in report.web_hits)
    return score


def rank_submissions(report: ScanReport) -> list[SubmissionReport]:
    return sorted(report.submissions, key=submission_suspicion, reverse=True)
