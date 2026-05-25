from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run app/ui/home.py` to resolve `app.*` imports.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from app.classroom.client import ClassroomClient
from app.classroom.oauth import MissingCredentialsError
from app.config import settings
from app.pipeline import runner, store
from app.ui import assignment_view, submission_view
from app.ui.demo_client import DemoClient


st.set_page_config(page_title="diplom — Classroom screening", layout="wide")


def _get_client():
    if "client" in st.session_state:
        return st.session_state["client"], st.session_state["client_mode"]

    if not settings.has_google_credentials:
        st.session_state["client"] = DemoClient()
        st.session_state["client_mode"] = "demo"
        return st.session_state["client"], "demo"

    try:
        client = ClassroomClient.connect()
        st.session_state["client"] = client
        st.session_state["client_mode"] = "live"
        return client, "live"
    except MissingCredentialsError:
        st.session_state["client"] = DemoClient()
        st.session_state["client_mode"] = "demo"
        return st.session_state["client"], "demo"


def _sidebar(mode: str) -> None:
    st.sidebar.title("diplom")
    if mode == "demo":
        st.sidebar.warning(
            "Demo mode. No `credentials.json` found at the repo root — "
            "showing synthetic data so the pipeline can be exercised."
        )
    else:
        st.sidebar.success("Connected to Google Classroom.")

    view = st.session_state.get("view", "home")
    if view != "home" and st.sidebar.button("← Back to courses"):
        st.session_state["view"] = "home"
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption("Recent scans")
    for s in store.list_scans()[:10]:
        label = f"{s['assignment_title']} — {s['created_at']:%Y-%m-%d %H:%M}"
        if st.sidebar.button(label, key=f"recent-{s['scan_id']}"):
            st.session_state["scan_id"] = s["scan_id"]
            st.session_state["view"] = "assignment"
            st.rerun()


def _render_home(client) -> None:
    st.header("Courses")
    courses = client.list_courses()
    if not courses:
        st.info("No active courses found.")
        return
    for course in courses:
        with st.container(border=True):
            st.subheader(course.name)
            if course.section:
                st.caption(course.section)
            assignments = client.list_assignments(course.id)
            for a in assignments:
                col_title, col_action = st.columns([4, 1])
                col_title.write(f"**{a.title}**")
                if a.description:
                    col_title.caption(a.description[:200])
                if col_action.button("Scan", key=f"scan-{a.id}"):
                    with st.spinner(f"Scanning {a.title}..."):
                        report = runner.scan_assignment(
                            course_id=course.id,
                            assignment_id=a.id,
                            assignment_title=a.title,
                            client=client,
                        )
                        store.save_scan(report)
                    st.session_state["scan_id"] = report.scan_id
                    st.session_state["view"] = "assignment"
                    st.rerun()


def main() -> None:
    client, mode = _get_client()
    _sidebar(mode)
    view = st.session_state.get("view", "home")
    if view == "home":
        _render_home(client)
    elif view == "assignment":
        assignment_view.render(st.session_state["scan_id"])
    elif view == "submission":
        submission_view.render(
            st.session_state["scan_id"], st.session_state["submission_id"]
        )
    else:
        st.session_state["view"] = "home"
        st.rerun()


main()
