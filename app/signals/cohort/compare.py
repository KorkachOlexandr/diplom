from __future__ import annotations

from app.report.model import CohortMatch, SubmissionReport


def find_matches(submissions: list[SubmissionReport]) -> dict[str, list[CohortMatch]]:
    """Compute intra-cohort matches across submissions.

    Phase 1: stub. Phase 2 will populate this by combining MinHash and
    embedding evidence into CohortMatch entries with aligned spans.

    Returns a mapping {submission_id: [CohortMatch, ...]}.
    """
    return {s.submission_id: [] for s in submissions}
