from __future__ import annotations

from dataclasses import dataclass

from app.classroom.client import Assignment, Course, DriveAttachment, Submission


# Demo mode mirrors the live test bed the thesis demos against. All samples
# are short Python solutions to introductory CS problems — chosen so the
# winnowing and AST channels actually have signal to fire on.


_COURSE = Course(id="demo-course", name="CS101: Programming Fundamentals", section="Section A")

_ASSIGNMENTS: list[Assignment] = [
    Assignment(
        id="assignment-a",
        course_id="demo-course",
        title="A. Originals & Copies — implement bubble_sort",
        description="Implement bubble_sort(lst) in Python.",
    ),
    Assignment(
        id="assignment-b",
        course_id="demo-course",
        title="B. Known limitations (false positives)",
        description="Submissions that legitimately trip leakage rules.",
    ),
    Assignment(
        id="assignment-c",
        course_id="demo-course",
        title="C. All clean — implement fibonacci",
        description="Four distinct honest implementations of fib(n).",
    ),
]


@dataclass(frozen=True)
class _DemoSub:
    sid: str
    student_name: str
    text: str
    mime_type: str = "text/x-python"


_STUDENTS = ["Anna Aiken", "Boris Borrowed", "Cyril Chatgpt", "Daria Duplicate"]


# Assignment A: bubble_sort, same problem statement.
_BUBBLE_ORIGINAL = '''\
def bubble_sort(lst):
    n = len(lst)
    for i in range(n):
        for j in range(0, n - i - 1):
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
    return lst
'''


# acc4: same control flow as acc1 but renamed variables — tests the cohort
# signal's resistance to lexical renaming.
_BUBBLE_RENAMED = '''\
def bubble_sort(arr):
    length = len(arr)
    for outer in range(length):
        for inner in range(0, length - outer - 1):
            if arr[inner] > arr[inner + 1]:
                arr[inner], arr[inner + 1] = arr[inner + 1], arr[inner]
    return arr
'''


# acc2: lifted from a well-known stackoverflow-style snippet — placeholder
# for the external web plagiarism signal that lives in Phase 4 / Moss-equivalent.
_BUBBLE_WEB_COPY = '''\
def bubble_sort(nums):
    # See https://realpython.com/sorting-algorithms-python/#the-bubble-sort-algorithm-in-python
    for i in range(len(nums) - 1, 0, -1):
        for j in range(i):
            if nums[j] > nums[j + 1]:
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
    return nums
'''


# acc3: AI-pasted with multiple leakage signals, Phase 3 true positive.
_BUBBLE_AI_PASTED = '''\
# Certainly! Here's the bubble_sort function you requested.
# Time complexity: O(n^2).
"""
This function takes a list and returns it sorted in ascending order using
the bubble sort algorithm.

I hope this helps! Let me know if you have any questions.
"""

```python
def bubble_sort(lst):
    n = len(lst)
    for i in range(n):
        for j in range(0, n - i - 1):
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
    return lst
```

# Example usage:
print(bubble_sort([3, 1, 4, 1, 5]))
'''


# Assignment B: legitimate code that nonetheless trips leakage rules — the
# false-positive showcase for the limitations chapter.
_FP_DOCS_TUTORIAL = '''\
"""
This function takes a list and returns its reverse.
Example usage:
    >>> reverse([1, 2, 3])
    [3, 2, 1]
"""

def reverse(lst):
    return lst[::-1]
'''

_FP_AI_TOPIC = '''\
# A small linear regression toy for a homework about how AI language models
# learn from data. As an AI language model would put it: minimize loss.
def fit(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den
    return slope, mean_y - slope * mean_x
'''

_FP_FENCE_IN_DOCSTRING = '''\
def parse_markdown_code_blocks(text):
    """Strip ``` fences from a markdown string and return inner code.

    ```python
    parse_markdown_code_blocks("```\\nx = 1\\n```")
    ```
    """
    out = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return "\\n".join(out)
'''

_FP_NOTES_HONEST = '''\
# Note: edge case for empty input handled below.
def average(xs):
    if not xs:
        return 0.0
    return sum(xs) / len(xs)

# Note: another helper, deliberately separate for testability.
def variance(xs, mean):
    return sum((x - mean) ** 2 for x in xs) / max(len(xs), 1)
'''


# Assignment C: four distinct, honest implementations of fib(n). None
# should fire either signal. One submission is empty to exercise the
# no-attachment extraction path.
_FIB_ITERATIVE = '''\
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''

_FIB_RECURSIVE = '''\
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
'''

_FIB_MEMO = '''\
def fib(n, _cache={0: 0, 1: 1}):
    if n not in _cache:
        _cache[n] = fib(n - 1) + fib(n - 2)
    return _cache[n]
'''


_ASSIGNMENT_SUBS: dict[str, list[_DemoSub]] = {
    "assignment-a": [
        _DemoSub("a-anna", _STUDENTS[0], _BUBBLE_ORIGINAL),
        _DemoSub("a-boris", _STUDENTS[1], _BUBBLE_WEB_COPY),
        _DemoSub("a-cyril", _STUDENTS[2], _BUBBLE_AI_PASTED),
        _DemoSub("a-daria", _STUDENTS[3], _BUBBLE_RENAMED),
    ],
    "assignment-b": [
        _DemoSub("b-anna", _STUDENTS[0], _FP_DOCS_TUTORIAL),
        _DemoSub("b-boris", _STUDENTS[1], _FP_AI_TOPIC),
        _DemoSub("b-cyril", _STUDENTS[2], _FP_FENCE_IN_DOCSTRING),
        _DemoSub("b-daria", _STUDENTS[3], _FP_NOTES_HONEST),
    ],
    "assignment-c": [
        _DemoSub("c-anna", _STUDENTS[0], _FIB_ITERATIVE),
        _DemoSub("c-boris", _STUDENTS[1], _FIB_RECURSIVE),
        _DemoSub("c-cyril", _STUDENTS[2], _FIB_MEMO),
        _DemoSub("c-daria", _STUDENTS[3], ""),  # empty — extraction-error path
    ],
}


class DemoClient:
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
                        title=f"{sub.student_name} — solution.py",
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
