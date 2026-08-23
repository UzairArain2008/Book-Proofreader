"""SQLAlchemy ORM models: books, pages, issues."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=gen_id)
    filename: Mapped[str] = mapped_column(String(255))  # safe, stored-on-disk name
    original_filename: Mapped[str] = mapped_column(String(255))  # user-facing name
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)

    # queued | processing | completed | completed_with_errors | failed
    status: Mapped[str] = mapped_column(String(32), default="queued")

    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_page_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    pages: Mapped[list["Page"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="Page.page_number"
    )
    issues: Mapped[list["Issue"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=gen_id)
    book_id: Mapped[str] = mapped_column(String(32), ForeignKey("books.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)

    # pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(32), default="pending")
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="pages")
    issues: Mapped[list["Issue"]] = relationship(back_populates="page", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=gen_id)
    book_id: Mapped[str] = mapped_column(String(32), ForeignKey("books.id", ondelete="CASCADE"))
    page_id: Mapped[str] = mapped_column(String(32), ForeignKey("pages.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)

    type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[str] = mapped_column(String(16))
    found_text: Mapped[str] = mapped_column(Text)
    suggested_text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(255), default="")

    # "ai" or "deterministic"
    source: Mapped[str] = mapped_column(String(16), default="ai")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    book: Mapped["Book"] = relationship(back_populates="issues")
    page: Mapped["Page"] = relationship(back_populates="issues")
