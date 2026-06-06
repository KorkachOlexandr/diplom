from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    credentials_path: Path = REPO_ROOT / "credentials.json"
    token_path: Path = REPO_ROOT / "token.json"
    db_path: Path = REPO_ROOT / "data" / "diplom.sqlite"

    @property
    def has_google_credentials(self) -> bool:
        return self.credentials_path.exists()


settings = Settings()
