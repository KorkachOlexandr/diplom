"""External web plagiarism check — stub interface.

The code-plagiarism analogues of CopyLeaks/Turnitin are Moss (Stanford,
https://theory.stanford.edu/~aiken/moss/) and JPlag (Karlsruhe,
https://github.com/jplag/JPlag). Both are CLI-based services that
upload source code to an external server for cross-corpus comparison,
not REST APIs, so a polished integration is a deployment concern
rather than something the thesis methodology depends on.

This module preserves the `check_text(text) -> list[WebHit]` interface
so the pipeline can call it unconditionally. The Phase-1 behavior is to
return [] — the cohort signal (winnowing + AST) covers intra-cohort
plagiarism, which is what the thesis defends as the core contribution.
A future Moss client would slot in here.
"""
from __future__ import annotations

from app.report.model import WebHit


def check_text(text: str) -> list[WebHit]:
    return []
