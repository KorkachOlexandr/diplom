from __future__ import annotations

from app.config import settings
from app.report.model import WebHit


def check_text(text: str) -> list[WebHit]:
    """External web plagiarism check.

    Phase 1: stub. Returns [] unless CopyLeaks credentials are configured,
    in which case the real client (to be implemented in Phase 4) would run.
    Kept behind this function so the pipeline can call it unconditionally.
    """
    if not settings.has_copyleaks:
        return []
    # Phase 4: implement actual CopyLeaks REST flow here.
    return []
