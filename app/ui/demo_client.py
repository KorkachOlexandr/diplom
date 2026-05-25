from __future__ import annotations

from app.classroom.client import Assignment, Course, DriveAttachment, Submission


# Demo mode: lets the UI run end-to-end without Google credentials so the
# pipeline, store, AI-leakage rules, and dashboard can be exercised locally.
# Texts include obvious leakage so the rules engine has something to surface.


_DEMO_COURSE = Course(id="demo-course", name="Demo Course 101", section="Section A")
_DEMO_ASSIGNMENT = Assignment(
    id="demo-assignment",
    course_id="demo-course",
    title="Essay: Climate Change",
    description="Write a 300-word essay on the causes and effects of climate change.",
)


_DEMO_TEXTS = {
    "sub-1": (
        "Alice Honest",
        "Climate change refers to long-term shifts in temperatures and weather patterns. "
        "While some of these shifts are natural, human activities — particularly the burning "
        "of fossil fuels — have been the dominant driver since the industrial revolution. "
        "The effects include rising sea levels, more frequent extreme weather, and disruption "
        "of agricultural systems.",
    ),
    "sub-2": (
        "Bob Pastesalot",
        "Certainly! Here's a 300-word essay on climate change.\n\n"
        "Climate change is one of the most pressing issues of our time. As an AI language model, "
        "I can tell you that the primary cause is the emission of greenhouse gases. "
        "The effects are far-reaching and include rising sea levels and extreme weather.",
    ),
    "sub-3": (
        "Carol Templater",
        "[Your Name]\nClimate Change Essay\n\n"
        "Please enter your name above. The following is an essay about climate change.\n\n"
        "Climate change is a major issue. Human activity contributes to global warming.",
    ),
    "sub-4": (
        "Dan Refuser",
        "I cannot provide a complete essay, but here is an overview. Climate change is driven "
        "by greenhouse gas emissions. My knowledge cutoff is 2023, so newer data may be missing.",
    ),
}


class DemoClient:
    """Drop-in replacement for ClassroomClient that serves synthetic data."""

    def list_courses(self) -> list[Course]:
        return [_DEMO_COURSE]

    def list_assignments(self, course_id: str) -> list[Assignment]:
        return [_DEMO_ASSIGNMENT] if course_id == _DEMO_COURSE.id else []

    def list_submissions(self, course_id: str, assignment_id: str) -> list[Submission]:
        if assignment_id != _DEMO_ASSIGNMENT.id:
            return []
        out = []
        for sid, (name, _text) in _DEMO_TEXTS.items():
            out.append(
                Submission(
                    id=sid,
                    assignment_id=assignment_id,
                    course_id=course_id,
                    user_id=f"user-{sid}",
                    student_name=name,
                    student_email=None,
                    state="TURNED_IN",
                    attachments=[
                        DriveAttachment(
                            file_id=sid,
                            title=f"{name} — submission.txt",
                            mime_type="text/plain",
                        )
                    ],
                )
            )
        return out

    def download_drive_file(self, file_id: str, mime_type: str) -> bytes:
        _name, text = _DEMO_TEXTS.get(file_id, ("", ""))
        return text.encode("utf-8")
