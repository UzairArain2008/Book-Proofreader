"""
PDF validation and metadata/text extraction.

This module never sends the whole book anywhere -- it only opens the PDF
locally with PyMuPDF to determine page count and to pull lightweight text
per page (used later for previous/next-page *context*, never as a bulk
payload to the AI).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


class InvalidPDFError(Exception):
    """Raised when a file is not a valid, readable, non-empty PDF."""


@dataclass
class PDFMetadata:
    page_count: int
    title: str | None
    is_encrypted: bool


def validate_and_open(path: Path) -> "fitz.Document":
    """
    Open a PDF defensively. Raises InvalidPDFError for corrupted, empty,
    encrypted (without password), or non-PDF files.
    """
    if not path.exists() or path.stat().st_size == 0:
        raise InvalidPDFError("File is missing or empty.")

    try:
        doc = fitz.open(path)
    except Exception as exc:  # PyMuPDF raises various exceptions for bad files
        raise InvalidPDFError(f"Could not open file as a PDF: {exc}") from exc

    if doc.is_encrypted:
        # Try an empty password (some PDFs are "encrypted" with no real password)
        if not doc.authenticate(""):
            doc.close()
            raise InvalidPDFError("PDF is password-protected and cannot be processed.")

    if doc.page_count == 0:
        doc.close()
        raise InvalidPDFError("PDF contains no pages.")

    return doc


def get_metadata(path: Path) -> PDFMetadata:
    doc = validate_and_open(path)
    try:
        meta = doc.metadata or {}
        return PDFMetadata(
            page_count=doc.page_count,
            title=meta.get("title") or None,
            is_encrypted=doc.is_encrypted,
        )
    finally:
        doc.close()


def extract_page_text(doc: "fitz.Document", page_number_1_indexed: int) -> str:
    """Extract plain text for a single page (1-indexed). Returns '' if out of range."""
    idx = page_number_1_indexed - 1
    if idx < 0 or idx >= doc.page_count:
        return ""
    page = doc.load_page(idx)
    text = page.get_text("text") or ""
    # Keep context small and cheap -- this is only for adjacent-page hints, not analysis.
    return text.strip()[:4000]
