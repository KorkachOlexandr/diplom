from __future__ import annotations

import streamlit as st

from app.pipeline import store
from app.report.ranker import rank_submissions, submission_suspicion


def render(scan_id: str) -> None:
    report = store.load_scan(scan_id)
    if report is None:
        st.error(f"Scan {scan_id} not found.")
        return

    st.header(report.assignment_title)
    st.caption(
        f"Scan {report.scan_id[:8]} · {report.created_at:%Y-%m-%d %H:%M UTC} · "
        f"{len(report.submissions)} submissions"
    )

    ranked = rank_submissions(report)
    if not ranked:
        st.info("No submissions in this scan.")
        return

    st.subheader("Ranked submissions")
    st.caption(
        "Ranked by a transparent weighted sum over per-signal counts. "
        "No single 'AI score' is shown by design — drill into a submission to see "
        "the evidence behind each flag."
    )

    for sub in ranked:
        score = submission_suspicion(sub)
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].write(f"**{sub.student_name}**")
            cols[1].metric("AI leakage", len(sub.leakage_hits))
            cols[2].metric("Cohort matches", len(sub.cohort_matches))
            cols[3].metric("Web hits", len(sub.web_hits))
            cols[4].metric("Suspicion", f"{score:.1f}")
            if sub.extraction_error:
                st.caption(f":warning: Extraction notes: {sub.extraction_error}")
            if st.button("Open submission", key=f"open-{sub.submission_id}"):
                st.session_state["scan_id"] = scan_id
                st.session_state["submission_id"] = sub.submission_id
                st.session_state["view"] = "submission"
                st.rerun()
