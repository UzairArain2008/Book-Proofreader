"""GET /api/books/{book_id}/report/{txt|csv}"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Book, Issue
from app.services.report_generator import build_csv_report, build_txt_report, write_reports_to_disk

router = APIRouter(prefix="/api/books", tags=["reports"])


def _generate_reports(db: Session, book: Book) -> tuple[str, str]:
    issues = (
        db.query(Issue)
        .filter(Issue.book_id == book.id)
        .order_by(Issue.page_number.asc())
        .all()
    )
    issues_by_page: dict[int, list[Issue]] = {}
    for issue in issues:
        issues_by_page.setdefault(issue.page_number, []).append(issue)

    txt_content = build_txt_report(book, book.pages, issues_by_page)
    csv_content = build_csv_report(issues)
    return txt_content, csv_content


@router.get("/{book_id}/report/txt")
def download_txt_report(book_id: str, db: Session = Depends(get_db)) -> FileResponse:
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if book.status not in ("completed", "completed_with_errors"):
        raise HTTPException(status_code=400, detail="Report is not ready until processing finishes.")

    txt_content, csv_content = _generate_reports(db, book)
    txt_path, _ = write_reports_to_disk(settings.reports_path, book_id, txt_content, csv_content)
    return FileResponse(
        path=txt_path,
        media_type="text/plain",
        filename="proofreading_report.txt",
    )


@router.get("/{book_id}/report/csv")
def download_csv_report(book_id: str, db: Session = Depends(get_db)) -> FileResponse:
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if book.status not in ("completed", "completed_with_errors"):
        raise HTTPException(status_code=400, detail="Report is not ready until processing finishes.")

    txt_content, csv_content = _generate_reports(db, book)
    _, csv_path = write_reports_to_disk(settings.reports_path, book_id, txt_content, csv_content)
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="proofreading_report.csv",
    )
