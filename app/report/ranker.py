from __future__ import annotations

from app.report.model import ScanReport, SubmissionReport


# Phase 1 ranker: a transparent weighted sum over per-signal counts/scores.
# This is intentionally simple and documented. Phase 5 evaluates and may tune
# the weights against NDCG / precision-at-k on the mixed-assignment eval set.
WEIGHTS = {
    "leakage": 1.0,        # per high-precision rule hit
    "cohort_minhash": 2.0, # per near-duplicate cohort match
    "cohort_embedding": 1.5,
    "web": 1.5,            # per external web hit above threshold
}


def submission_suspicion(report: SubmissionReport) -> float:
    score = 0.0
    score += WEIGHTS["leakage"] * len(report.leakage_hits)
    for m in report.cohort_matches:
        if m.channel == "minhash":
            score += WEIGHTS["cohort_minhash"] * m.score
        else:
            score += WEIGHTS["cohort_embedding"] * m.score
    score += WEIGHTS["web"] * sum(h.score for h in report.web_hits)
    return score


def rank_submissions(report: ScanReport) -> list[SubmissionReport]:
    return sorted(report.submissions, key=submission_suspicion, reverse=True)
