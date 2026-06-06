from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    credentials_path: Path = REPO_ROOT / "credentials.json"
    token_path: Path = REPO_ROOT / "token.json"
    db_path: Path = REPO_ROOT / "data" / "diplom.sqlite"

    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    copyleaks_email: str | None = None
    copyleaks_api_key: str | None = None
    copyleaks_webhook_url: str | None = None  # public base URL for CopyLeaks callbacks

    @property
    def has_google_credentials(self) -> bool:
        return self.credentials_path.exists()

    @property
    def has_copyleaks(self) -> bool:
        return bool(self.copyleaks_email and self.copyleaks_api_key)


settings = Settings()
