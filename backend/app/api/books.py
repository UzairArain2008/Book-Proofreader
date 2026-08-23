"""Book listing, detail, progress, issues, retry, and delete endpoints."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Book, Issue, Page
from app.schemas.schemas import (
    BookDetailOut,
    BookOut,
    BookProgressOut,
    IssueOut,
    PageOut,
)
from app.services.proofreading_service import process_failed_pages
from app.services.queue import is_book_running, submit_book_job

router = APIRouter(prefix="/api/books", tags=["books"])


def _get_book_or_404(db: Session, book_id: str) -> Book:
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    return book


@router.get("", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db)) -> list[Book]:
    return db.query(Book).order_by(Book.created_at.desc()).all()


@router.get("/{book_id}", response_model=BookDetailOut)
def get_book(book_id: str, db: Session = Depends(get_db)) -> BookDetailOut:
    book = _get_book_or_404(db, book_id)
    issue_types = Counter(i.type for i in book.issues)
    return BookDetailOut(
        **BookOut.model_validate(book).model_dump(),
        issues_by_type=dict(issue_types),
        pages=[PageOut.model_validate(p) for p in book.pages],
    )


@router.get("/{book_id}/progress", response_model=BookProgressOut)
def get_progress(book_id: str, db: Session = Depends(get_db)) -> BookProgressOut:
    book = _get_book_or_404(db, book_id)
    pages = book.pages
    remaining = book.page_count - book.processed_pages
    current_page = next((p.page_number for p in pages if p.status == "processing"), None)
    percent = (book.processed_pages / book.page_count * 100) if book.page_count else 0.0

    return BookProgressOut(
        book_id=book.id,
        status=book.status,
        page_count=book.page_count,
        processed_pages=book.processed_pages,
        remaining_pages=max(remaining, 0),
        issue_count=book.issue_count,
        failed_page_count=book.failed_page_count,
        progress_percent=round(percent, 1),
        current_page=current_page,
        pages=[PageOut.model_validate(p) for p in pages],
    )


@router.get("/{book_id}/issues", response_model=list[IssueOut])
def get_issues(book_id: str, db: Session = Depends(get_db)) -> list[Issue]:
    _get_book_or_404(db, book_id)
    return (
        db.query(Issue)
        .filter(Issue.book_id == book_id)
        .order_by(Issue.page_number.asc())
        .all()
    )


@router.post("/{book_id}/retry-failed", response_model=BookOut)
def retry_failed(book_id: str, db: Session = Depends(get_db)) -> Book:
    book = _get_book_or_404(db, book_id)
    if is_book_running(book_id):
        raise HTTPException(status_code=409, detail="This book is already being processed.")

    failed_count = db.query(Page).filter(Page.book_id == book_id, Page.status == "failed").count()
    if failed_count == 0:
        raise HTTPException(status_code=400, detail="No failed pages to retry.")

    book.status = "processing"
    db.commit()
    submit_book_job(book_id, lambda: process_failed_pages(book_id))
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204, response_model=None)
def delete_book(book_id: str, db: Session = Depends(get_db)) -> None:
    book = _get_book_or_404(db, book_id)
    if is_book_running(book_id):
        raise HTTPException(status_code=409, detail="Cannot delete a book while it is processing.")

    # Remove files from disk (uploaded PDF, any leftover rendered pages, reports).
    pdf_path = settings.uploads_path / book.filename
    pdf_path.unlink(missing_ok=True)

    pages_dir = settings.pages_path / book_id
    if pages_dir.exists():
        for f in pages_dir.glob("*"):
            f.unlink(missing_ok=True)
        pages_dir.rmdir()

    reports_dir = settings.reports_path / book_id
    if reports_dir.exists():
        for f in reports_dir.glob("*"):
            f.unlink(missing_ok=True)
        reports_dir.rmdir()

    db.delete(book)
    db.commit()
