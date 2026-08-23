"""Pydantic schemas: API request/response models + Gemini structured-output validation."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums shared between the Gemini contract and the database
# ---------------------------------------------------------------------------
class IssueType(str, Enum):
    spelling = "spelling"
    grammar = "grammar"
    punctuation = "punctuation"
    typographical = "typographical"
    sentence_structure = "sentence_structure"
    logical = "logical"
    factual = "factual"
    duplication = "duplication"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Confidence(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# Gemini structured output contract
# ---------------------------------------------------------------------------
class GeminiIssue(BaseModel):
    type: IssueType
    severity: Severity
    confidence: Confidence
    found_text: str = Field(min_length=1, max_length=2000)
    suggested_text: str = Field(default="", max_length=2000)
    explanation: str = Field(min_length=1, max_length=1000)
    location: str = Field(default="", max_length=255)

    @field_validator("found_text", "explanation")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class GeminiPageResult(BaseModel):
    page: int
    issues: list[GeminiIssue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API: Books
# ---------------------------------------------------------------------------
class BookOut(BaseModel):
    id: str
    original_filename: str
    file_size: int
    page_count: int
    status: str
    processed_pages: int
    issue_count: int
    failed_page_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PageOut(BaseModel):
    id: str
    page_number: int
    status: str
    issue_count: int
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IssueOut(BaseModel):
    id: str
    page_number: int
    type: str
    severity: str
    confidence: str
    found_text: str
    suggested_text: str
    explanation: str
    location: str
    source: str

    model_config = {"from_attributes": True}


class BookProgressOut(BaseModel):
    book_id: str
    status: str
    page_count: int
    processed_pages: int
    remaining_pages: int
    issue_count: int
    failed_page_count: int
    progress_percent: float
    current_page: Optional[int] = None
    pages: list[PageOut] = Field(default_factory=list)


class BookDetailOut(BookOut):
    issues_by_type: dict[str, int] = Field(default_factory=dict)
    pages: list[PageOut] = Field(default_factory=list)


class UploadResponse(BaseModel):
    book: BookOut
    message: str = "Upload received. Processing has started."
