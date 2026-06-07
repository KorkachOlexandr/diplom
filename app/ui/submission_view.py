from __future__ import annotations

import html

import streamlit as st

from app.pipeline import store
from app.report.model import LeakageHit, SubmissionReport


def render(scan_id: str, submission_id: str) -> None:
    report = store.load_scan(scan_id)
    if report is None:
        st.error(f"Scan {scan_id} not found.")
        return
    sub = next((s for s in report.submissions if s.submission_id == submission_id), None)
    if sub is None:
        st.error(f"Submission {submission_id} not in scan.")
        return

    st.header(sub.student_name)
    st.caption(f"Assignment: {report.assignment_title} · Submission {sub.submission_id}")

    if sub.extraction_error:
        st.warning(f"Extraction notes: {sub.extraction_error}")

    tabs = st.tabs(
        [
            f"AI leakage ({len(sub.leakage_hits)})",
            f"Cohort matches ({len(sub.cohort_matches)})",
            f"Web hits ({len(sub.web_hits)})",
            "Full text",
        ]
    )

    with tabs[0]:
        _render_leakage(sub)
    with tabs[1]:
        _render_cohort(sub)
    with tabs[2]:
        _render_web(sub)
    with tabs[3]:
        st.text_area("Extracted text", sub.text, height=400)


def _render_leakage(sub: SubmissionReport) -> None:
    if not sub.leakage_hits:
        st.info("No AI-leakage rules fired on this submission.")
        return
    st.caption(
        "Each rule below is high-precision by design. A hit indicates a specific, "
        "named failure mode of careless LLM use — not an AI-authorship verdict."
    )
    for hit in sub.leakage_hits:
        with st.container(border=True):
            st.markdown(f"**{hit.rule_id}** · _{hit.rule_family}_")
            st.caption(hit.description)
            st.markdown(f"> {html.escape(hit.evidence)}")
    st.divider()
    st.subheader("Submission with highlights")
    st.markdown(_highlighted_html(sub.text, sub.leakage_hits), unsafe_allow_html=True)


def _render_cohort(sub: SubmissionReport) -> None:
    if not sub.cohort_matches:
        st.info(
            "Cohort similarity is stubbed in Phase 1 — Phase 2 will fill in "
            "MinHash and embedding evidence with side-by-side aligned spans."
        )
        return
    for m in sub.cohort_matches:
        with st.container(border=True):
            st.markdown(
                f"**Match with {m.other_student_name}** · channel: `{m.channel}` · "
                f"Jaccard score: {m.score:.2f} · {len(m.spans)} span(s)"
            )
            for i, span in enumerate(m.spans, 1):
                if len(m.spans) > 1:
                    st.caption(f"Span {i}")
                col_a, col_b = st.columns(2)
                col_a.caption("This submission")
                col_a.markdown(f"```\n{span.this_excerpt}\n```")
                col_b.caption("Other submission")
                col_b.markdown(f"```\n{span.other_excerpt}\n```")


def _render_web(sub: SubmissionReport) -> None:
    if not sub.web_hits:
        st.info("No external web hits. (CopyLeaks integration arrives in Phase 4.)")
        return
    for h in sub.web_hits:
        with st.container(border=True):
            st.markdown(f"[{h.url}]({h.url}) · score: {h.score:.2f}")
            st.markdown(f"> {html.escape(h.snippet)}")


def _highlighted_html(text: str, hits: list[LeakageHit]) -> str:
    if not hits:
        return f"<pre style='white-space:pre-wrap'>{html.escape(text)}</pre>"
    spans = sorted({(h.start, h.end) for h in hits})
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    out: list[str] = []
    cursor = 0
    for start, end in merged:
        out.append(html.escape(text[cursor:start]))
        out.append(
            f"<mark style='background:#fde68a'>{html.escape(text[start:end])}</mark>"
        )
        cursor = end
    out.append(html.escape(text[cursor:]))
    return f"<pre style='white-space:pre-wrap'>{''.join(out)}</pre>"
