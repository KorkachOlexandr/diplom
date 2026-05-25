from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass
class Course:
    id: str
    name: str
    section: str | None = None


@dataclass
class Assignment:
    id: str
    course_id: str
    title: str
    description: str | None = None


@dataclass
class DriveAttachment:
    file_id: str
    title: str
    mime_type: str


@dataclass
class Submission:
    id: str
    assignment_id: str
    course_id: str
    user_id: str
    student_name: str
    student_email: str | None
    state: str
    attachments: list[DriveAttachment]


class ClassroomClient:
    """Thin facade over the Classroom + Drive APIs.

    Construct with `ClassroomClient.connect()` to use real Google APIs,
    or instantiate directly with provided services for testing.
    """

    def __init__(self, classroom_service, drive_service):
        self._classroom = classroom_service
        self._drive = drive_service

    @classmethod
    def connect(cls) -> "ClassroomClient":
        from googleapiclient.discovery import build

        from app.classroom.oauth import load_credentials

        creds = load_credentials()
        classroom = build("classroom", "v1", credentials=creds, cache_discovery=False)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        return cls(classroom, drive)

    def list_courses(self) -> list[Course]:
        resp = self._classroom.courses().list(courseStates=["ACTIVE"]).execute()
        return [
            Course(id=c["id"], name=c["name"], section=c.get("section"))
            for c in resp.get("courses", [])
        ]

    def list_assignments(self, course_id: str) -> list[Assignment]:
        resp = (
            self._classroom.courses()
            .courseWork()
            .list(courseId=course_id)
            .execute()
        )
        return [
            Assignment(
                id=a["id"],
                course_id=course_id,
                title=a.get("title", "(untitled)"),
                description=a.get("description"),
            )
            for a in resp.get("courseWork", [])
        ]

    def list_submissions(self, course_id: str, assignment_id: str) -> list[Submission]:
        resp = (
            self._classroom.courses()
            .courseWork()
            .studentSubmissions()
            .list(courseId=course_id, courseWorkId=assignment_id)
            .execute()
        )
        out: list[Submission] = []
        for s in resp.get("studentSubmissions", []):
            user_id = s.get("userId", "")
            student_name, student_email = self._lookup_student(course_id, user_id)
            attachments = []
            for att in (
                s.get("assignmentSubmission", {}).get("attachments", []) or []
            ):
                drive = att.get("driveFile")
                if not drive:
                    continue
                file_id = drive.get("id")
                if not file_id:
                    continue
                meta = (
                    self._drive.files()
                    .get(fileId=file_id, fields="id, name, mimeType")
                    .execute()
                )
                attachments.append(
                    DriveAttachment(
                        file_id=meta["id"],
                        title=meta.get("name", "(unnamed)"),
                        mime_type=meta.get("mimeType", ""),
                    )
                )
            out.append(
                Submission(
                    id=s["id"],
                    assignment_id=assignment_id,
                    course_id=course_id,
                    user_id=user_id,
                    student_name=student_name,
                    student_email=student_email,
                    state=s.get("state", "UNKNOWN"),
                    attachments=attachments,
                )
            )
        return out

    def _lookup_student(self, course_id: str, user_id: str) -> tuple[str, str | None]:
        if not user_id:
            return ("(unknown)", None)
        try:
            student = (
                self._classroom.courses()
                .students()
                .get(courseId=course_id, userId=user_id)
                .execute()
            )
            profile = student.get("profile", {})
            name = profile.get("name", {}).get("fullName") or user_id
            email = profile.get("emailAddress")
            return (name, email)
        except Exception:
            return (user_id, None)

    def download_drive_file(self, file_id: str, mime_type: str) -> bytes:
        """Return raw bytes for a Drive file. For Google-native docs, exports as text/plain."""
        from googleapiclient.http import MediaIoBaseDownload

        if mime_type.startswith("application/vnd.google-apps."):
            export_mime = _native_export_mime(mime_type)
            request = self._drive.files().export_media(
                fileId=file_id, mimeType=export_mime
            )
        else:
            request = self._drive.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()


def _native_export_mime(google_mime: str) -> str:
    if google_mime == "application/vnd.google-apps.document":
        return "text/plain"
    if google_mime == "application/vnd.google-apps.presentation":
        return "text/plain"
    if google_mime == "application/vnd.google-apps.spreadsheet":
        return "text/csv"
    return "text/plain"
