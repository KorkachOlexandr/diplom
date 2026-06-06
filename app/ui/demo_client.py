from __future__ import annotations

from dataclasses import dataclass

from app.classroom.client import Assignment, Course, DriveAttachment, Submission


# Demo mode mirrors the live test bed the thesis demos against:
# - Assignment A "Originals & Copies": one true AI-leakage positive (Cyril),
#   plus an acc1==acc4 cohort match and an acc2 web-plagiarism target that
#   are placeholders for Phase 2 / Phase 4 signals respectively.
# - Assignment B "Known limitations": each submission trips a different
#   rule on legitimate text — this is the false-positive showcase that
#   feeds the limitations chapter.
# - Assignment C "All clean": four distinct honest essays. Nothing should
#   fire. Includes one empty submission to exercise the no-attachment path.


_COURSE = Course(id="demo-course", name="Diplom Demo Course", section="Section A")

_ASSIGNMENTS: list[Assignment] = [
    Assignment(
        id="assignment-a",
        course_id="demo-course",
        title="A. Originals & Copies",
        description="Mix of original, copied, and AI-pasted submissions.",
    ),
    Assignment(
        id="assignment-b",
        course_id="demo-course",
        title="B. Known limitations (false positives)",
        description="Each submission trips a leakage rule on legitimate text.",
    ),
    Assignment(
        id="assignment-c",
        course_id="demo-course",
        title="C. All clean",
        description="Four honest, distinct essays. Nothing should fire.",
    ),
]


@dataclass(frozen=True)
class _DemoSub:
    sid: str
    student_name: str
    text: str
    mime_type: str = "text/plain"


# Four students enrolled across the course (mirrors the live setup with 4 accs).
_STUDENTS = ["Anna Aiken", "Boris Borrowed", "Cyril Chatgpt", "Daria Duplicate"]


_ORIGINAL_TEXT = (
    "Climate change refers to long-term shifts in temperatures and weather "
    "patterns. While some of these shifts are natural, human activities — "
    "particularly the burning of fossil fuels — have been the dominant driver "
    "since the industrial revolution."
)


_ASSIGNMENT_SUBS: dict[str, list[_DemoSub]] = {
    "assignment-a": [
        # acc1: original honest essay
        _DemoSub("a-anna", _STUDENTS[0], _ORIGINAL_TEXT),
        # acc2: copied from a web source — Phase 4 (CopyLeaks) target
        _DemoSub(
            "a-boris",
            _STUDENTS[1],
            "Climate change includes both global warming driven by human "
            "emissions of greenhouse gases and the resulting large-scale "
            "shifts in weather patterns. Though there have been previous "
            "periods of climatic change, since the mid-20th century humans "
            "have had an unprecedented impact on Earth's climate system.",
        ),
        # acc3: AI-pasted with multiple leakage signals — the Phase 1 true positive
        _DemoSub(
            "a-cyril",
            _STUDENTS[2],
            "Certainly! Here's an essay on climate change.\n\n"
            "As an AI language model, I should note that climate change is one "
            "of the most significant challenges of our time. The primary cause "
            "is the emission of greenhouse gases. My knowledge cutoff is 2023.",
        ),
        # acc4: copies acc1 verbatim — Phase 2 (cohort) target
        _DemoSub("a-daria", _STUDENTS[3], _ORIGINAL_TEXT),
    ],
    "assignment-b": [
        # FP 1: essay legitimately about LLMs, contains "as an AI language model"
        _DemoSub(
            "b-anna",
            _STUDENTS[0],
            "The phrase \"as an AI language model\" has become cultural "
            "shorthand for evasive, hedged writing. Critics use it to mock "
            "corporate prose; researchers use it to spot pasted ChatGPT "
            "output. Both groups are right for different reasons.",
        ),
        # FP 2: a writing-skills tutorial that legitimately demonstrates the
        # exact placeholder syntax our rule is designed to catch. The rule
        # cannot tell "student pasted a template" from "student wrote a
        # tutorial *about* the template" — a defensible limitation.
        _DemoSub(
            "b-boris",
            _STUDENTS[1],
            "When you write a cover letter, start by replacing [Your Name] "
            "at the top with your full name. Then update [Date] with today's "
            "date in long form, and the [Company] placeholder with the "
            "recipient's organization. Always proofread.",
        ),
        # FP 3: tutorial that quotes a prompt template
        _DemoSub(
            "b-cyril",
            _STUDENTS[2],
            "When configuring a custom GPT, please enter your name into the "
            "system prompt template. The following is an essay about how to "
            "structure prompts so that the assistant behaves predictably.",
        ),
        # FP 4: film review with assistant-style opener
        _DemoSub(
            "b-daria",
            _STUDENTS[3],
            "Certainly, here is my take on Dune Part Two: it is a rare "
            "sequel that earns its scale. Villeneuve's restraint with the "
            "spectacle is exactly what the source material asks for.",
        ),
    ],
    "assignment-c": [
        _DemoSub(
            "c-anna",
            _STUDENTS[0],
            "Photosynthesis is the process by which green plants convert "
            "sunlight into chemical energy stored in glucose. Chloroplasts "
            "contain chlorophyll, which absorbs light primarily in the blue "
            "and red wavelengths.",
        ),
        _DemoSub(
            "c-boris",
            _STUDENTS[1],
            "The French Revolution of 1789 reshaped European political "
            "order. The fall of the Bastille on 14 July became the symbolic "
            "break with the old regime and is still commemorated each year.",
        ),
        _DemoSub(
            "c-cyril",
            _STUDENTS[2],
            "Newton's three laws describe the relationship between forces "
            "and motion. An object at rest stays at rest unless acted upon "
            "by an external force; force equals mass times acceleration; "
            "every action has an equal and opposite reaction.",
        ),
        # Daria turned in with no attachment — exercises the empty-submission path
        _DemoSub("c-daria", _STUDENTS[3], ""),
    ],
}


class DemoClient:
    """Drop-in replacement for ClassroomClient that serves synthetic data."""

    def list_courses(self) -> list[Course]:
        return [_COURSE]

    def list_assignments(self, course_id: str) -> list[Assignment]:
        if course_id != _COURSE.id:
            return []
        return list(_ASSIGNMENTS)

    def list_submissions(self, course_id: str, assignment_id: str) -> list[Submission]:
        subs = _ASSIGNMENT_SUBS.get(assignment_id, [])
        out: list[Submission] = []
        for sub in subs:
            attachments: list[DriveAttachment] = []
            if sub.text:
                attachments.append(
                    DriveAttachment(
                        file_id=sub.sid,
                        title=f"{sub.student_name} — submission.txt",
                        mime_type=sub.mime_type,
                    )
                )
            out.append(
                Submission(
                    id=sub.sid,
                    assignment_id=assignment_id,
                    course_id=course_id,
                    user_id=f"user-{sub.sid}",
                    student_name=sub.student_name,
                    student_email=None,
                    state="TURNED_IN",
                    attachments=attachments,
                )
            )
        return out

    def download_drive_file(self, file_id: str, mime_type: str) -> bytes:
        for subs in _ASSIGNMENT_SUBS.values():
            for sub in subs:
                if sub.sid == file_id:
                    return sub.text.encode("utf-8")
        return b""
