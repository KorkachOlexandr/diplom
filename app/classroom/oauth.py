from __future__ import annotations

import os
from pathlib import Path

# Google's consent screen sometimes substitutes equivalent scopes (e.g.
# classroom.coursework.students.readonly -> classroom.student-submissions.students.readonly).
# Without this, oauthlib raises Warning on any granted-vs-requested scope mismatch.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import settings


SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
    "https://www.googleapis.com/auth/drive.readonly",
]


class MissingCredentialsError(RuntimeError):
    pass


def load_credentials(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
) -> Credentials:
    """Return a usable Credentials object, running the installed-app flow if needed.

    Raises MissingCredentialsError if the OAuth client JSON is not present.
    """
    credentials_path = credentials_path or settings.credentials_path
    token_path = token_path or settings.token_path

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return creds

    if not credentials_path.exists():
        raise MissingCredentialsError(
            f"OAuth client file not found at {credentials_path}. "
            "Create a Desktop OAuth client in Google Cloud Console "
            "and save the downloaded JSON there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds
