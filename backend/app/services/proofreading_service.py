"""
Orchestrates the page-by-page proofreading pipeline.

For every page, independently:
  render page -> extract adjacent-page text (context only) -> deterministic
  checks -> Gemini analysis (current page image ONLY) -> validate -> persist.

A failure on one page is caught and recorded; it never aborts the whole book.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.database import session_scope
from app.models.models import Book, Issue, Page
from app.services import pdf_processor
from app.services.deterministic_checks import run_deterministic_checks
from app.services.gemini_service import gemini_service
from app.services.page_renderer import render_page_to_image_bytes, save_page_image
from app.services.queue import page_semaphore

logger = logging.getLogger("proofreader.pipeline")


def _book_pdf_path(book: Book) -> Path:
    return settings.uploads_path / book.filename


async def process_book(book_id: str) -> None:
    """Process every page of a book from scratch."""
    with session_scope() as db:
        book = db.get(Book, book_id)
        if book is None:
            logger.error("process_book: book %s not found", book_id)
            return
        pdf_path = _book_pdf_path(book)
        book.status = "processing"
        page_numbers = list(range(1, book.page_count + 1))

        # Ensure a Page row exists for every page (idempotent).
        existing = {p.page_number for p in book.pages}
        for n in page_numbers:
            if n not in existing:
                db.add(Page(book_id=book.id, page_number=n, status="pending"))
        db.flush()

    await _run_pages(book_id, pdf_path, page_numbers)
    await _finalize_book(book_id)


async def process_failed_pages(book_id: str) -> None:
    """Retry only pages currently marked as failed."""
    with session_scope() as db:
        book = db.get(Book, book_id)
        if book is None:
            logger.error("process_failed_pages: book %s not found", book_id)
            return
        pdf_path = _book_pdf_path(book)
        failed_numbers = [p.page_number for p in book.pages if p.status == "failed"]
        if not failed_numbers:
            return
        book.status = "processing"

    await _run_pages(book_id, pdf_path, failed_numbers)
    await _finalize_book(book_id)


async def _run_pages(book_id: str, pdf_path: Path, page_numbers: list[int]) -> None:
    if not pdf_path.exists():
        logger.error("PDF missing on disk for book %s at %s", book_id, pdf_path)
        with session_scope() as db:
            book = db.get(Book, book_id)
            if book:
                book.status = "failed"
        return

    tasks = [_process_single_page(book_id, pdf_path, n) for n in page_numbers]
    await asyncio.gather(*tasks)


async def _process_single_page(book_id: str, pdf_path: Path, page_number: int) -> None:
    async with page_semaphore:
        with session_scope() as db:
            page = _get_page(db, book_id, page_number)
            if page:
                page.status = "processing"

        try:
            image_bytes, current_text, prev_text, next_text = await asyncio.to_thread(
                _render_and_extract, pdf_path, page_number
            )

            deterministic_issues = run_deterministic_checks(current_text)

            gemini_result = await gemini_service.analyze_page(
                page_number=page_number,
                image_bytes=image_bytes,
                prev_text=prev_text,
                next_text=next_text,
            )

            if not gemini_result.success:
                _mark_page_failed(book_id, page_number, gemini_result.error or "Unknown Gemini error")
                return

            with session_scope() as db:
                page = _get_page(db, book_id, page_number)
                if page is None:
                    return

                # Clear any previous issues for this page (in case of retry).
                db.query(Issue).filter(Issue.page_id == page.id).delete()

                count = 0
                for d in deterministic_issues:
                    db.add(
                        Issue(
                            book_id=book_id,
                            page_id=page.id,
                            page_number=page_number,
                            type=d.type,
                            severity=d.severity,
                            confidence=d.confidence,
                            found_text=d.found_text,
                            suggested_text=d.suggested_text,
                            explanation=d.explanation,
                            location=d.location,
                            source="deterministic",
                        )
                    )
                    count += 1

                for issue in gemini_result.result.issues:
                    db.add(
                        Issue(
                            book_id=book_id,
                            page_id=page.id,
                            page_number=page_number,
                            type=issue.type.value,
                            severity=issue.severity.value,
                            confidence=issue.confidence.value,
                            found_text=issue.found_text,
                            suggested_text=issue.suggested_text,
                            explanation=issue.explanation,
                            location=issue.location,
                            source="ai",
                        )
                    )
                    count += 1

                page.status = "completed"
                page.issue_count = count
                page.error_message = None
                page.processed_at = datetime.utcnow()

        except pdf_processor.InvalidPDFError as exc:
            _mark_page_failed(book_id, page_number, f"PDF error: {exc}")
        except Exception as exc:  # noqa: BLE001 - a single page must never crash the job
            logger.exception("Unexpected failure on book %s page %s", book_id, page_number)
            _mark_page_failed(book_id, page_number, f"Unexpected error: {exc}")
        finally:
            _increment_book_progress(book_id)


def _render_and_extract(pdf_path: Path, page_number: int) -> tuple[bytes, str, str, str]:
    """Runs in a worker thread: open the doc fresh (per-call) for thread safety."""
    doc = pdf_processor.validate_and_open(pdf_path)
    try:
        image_bytes = render_page_to_image_bytes(doc, page_number, settings.PAGE_RENDER_DPI)
        current_text = pdf_processor.extract_page_text(doc, page_number)
        prev_text = pdf_processor.extract_page_text(doc, page_number - 1) if page_number > 1 else ""
        next_text = pdf_processor.extract_page_text(doc, page_number + 1)
        # Rendered image bytes are kept only in memory and never written to disk
        # unless a caller explicitly persists them (see page_renderer.save_page_image),
        # which this pipeline does not do -- honoring DELETE_TEMP_FILES / privacy by default.
        return image_bytes, current_text, prev_text, next_text
    finally:
        doc.close()


def _get_page(db, book_id: str, page_number: int) -> Page | None:
    return (
        db.query(Page)
        .filter(Page.book_id == book_id, Page.page_number == page_number)
        .one_or_none()
    )


def _mark_page_failed(book_id: str, page_number: int, reason: str) -> None:
    with session_scope() as db:
        page = _get_page(db, book_id, page_number)
        if page:
            page.status = "failed"
            page.error_message = reason[:1000]
            page.processed_at = datetime.utcnow()


def _increment_book_progress(book_id: str) -> None:
    with session_scope() as db:
        book = db.get(Book, book_id)
        if not book:
            return
        completed_or_failed = sum(1 for p in book.pages if p.status in ("completed", "failed"))
        book.processed_pages = completed_or_failed
        book.issue_count = sum(p.issue_count for p in book.pages)
        book.failed_page_count = sum(1 for p in book.pages if p.status == "failed")


async def _finalize_book(book_id: str) -> None:
    with session_scope() as db:
        book = db.get(Book, book_id)
        if not book:
            return
        statuses = {p.status for p in book.pages}
        if statuses <= {"completed"}:
            book.status = "completed"
        elif "pending" in statuses or "processing" in statuses:
            # Shouldn't normally happen once gather() completes, but guards against races.
            book.status = "processing"
        elif "failed" in statuses:
            book.status = "completed_with_errors"
        else:
            book.status = "completed"
        book.completed_at = datetime.utcnow()

    if settings.DELETE_TEMP_FILES:
        _cleanup_page_images(book_id)


def _cleanup_page_images(book_id: str) -> None:
    book_pages_dir = settings.pages_path / book_id
    if book_pages_dir.exists():
        for f in book_pages_dir.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            book_pages_dir.rmdir()
        except OSError:
            pass
