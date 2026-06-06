from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LeakageHit(BaseModel):
    rule_id: str
    rule_family: str
    description: str
    start: int
    end: int
    evidence: str


class CohortMatch(BaseModel):
    other_submission_id: str
    other_student_name: str
    channel: Literal["winnowing", "ast"]
    score: float
    this_span: tuple[int, int]
    other_span: tuple[int, int]
    this_excerpt: str
    other_excerpt: str


class WebHit(BaseModel):
    url: str
    score: float
    snippet: str


class SubmissionReport(BaseModel):
    submission_id: str
    student_id: str
    student_name: str
    text: str = ""
    extraction_error: str | None = None
    leakage_hits: list[LeakageHit] = Field(default_factory=list)
    cohort_matches: list[CohortMatch] = Field(default_factory=list)
    web_hits: list[WebHit] = Field(default_factory=list)


class ScanReport(BaseModel):
    scan_id: str
    course_id: str
    assignment_id: str
    assignment_title: str
    created_at: datetime
    submissions: list[SubmissionReport] = Field(default_factory=list)
