"""
Database layer.

Uses SQLite for the MVP via SQLAlchemy's ORM. Because all access goes through
SQLAlchemy's engine/session abstraction (rather than raw sqlite3 calls), moving
to PostgreSQL later is just a matter of changing DATABASE_URL and installing a
driver (e.g. psycopg) -- no application code needs to change.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite requires this connect_arg when used with multiple threads (FastAPI's
# threadpool for sync endpoints). This is a no-op for other databases.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    # Import models so they are registered on Base.metadata before create_all.
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for use outside of request handlers (e.g. background tasks)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
