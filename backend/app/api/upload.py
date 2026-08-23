"""POST /api/books/upload"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Book
from app.schemas.schemas import BookOut, UploadResponse
from app.services import pdf_processor
from app.services.proofreading_service import process_book
from app.services.queue import submit_book_job

logger = logging.getLogger("proofreader.upload")
router = APIRouter(prefix="/api/books", tags=["upload"])


def _safe_stored_filename(original_name: str) -> str:
    """Never trust the client-provided filename; generate a safe one on disk."""
    suffix = Path(original_name).suffix.lower()
    if suffix != ".pdf":
        suffix = ".pdf"
    return f"{uuid.uuid4().hex}{suffix}"


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_book(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadResponse:
    # --- Validate content type / extension up front ---
    original_name = file.filename or "upload.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # --- Read with a size cap (avoid loading unbounded data into memory) ---
    max_bytes = settings.max_file_size_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
            )
        chunks.append(chunk)
    data = b"".join(chunks)

    if total == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Persist with a safe, non-user-controlled filename ---
    stored_name = _safe_stored_filename(original_name)
    dest_path = settings.uploads_path / stored_name
    dest_path.write_bytes(data)

    # --- Validate it's actually a readable PDF and get its page count ---
    try:
        meta = pdf_processor.get_metadata(dest_path)
    except pdf_processor.InvalidPDFError as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    book = Book(
        filename=stored_name,
        original_filename=original_name,
        file_size=total,
        page_count=meta.page_count,
        status="queued",
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    submit_book_job(book.id, lambda: process_book(book.id))

    return UploadResponse(book=BookOut.model_validate(book))
