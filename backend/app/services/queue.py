"""
Controlled processing queue.

Two responsibilities:
1. Bound how many pages are sent to Gemini concurrently (MAX_CONCURRENT_PAGES),
   so we respect API rate limits instead of firing hundreds of requests at once.
2. Track in-flight background jobs per book so a book isn't processed twice
   concurrently (e.g. double-clicking "retry").

This is intentionally a simple in-process asyncio queue, appropriate for an
MVP running as a single Uvicorn process. It is isolated behind this module so
it could be swapped for Celery/RQ later without touching the rest of the app.
"""
from __future__ import annotations

import asyncio
import logging

from app.config import settings

logger = logging.getLogger("proofreader.queue")

# Bounds concurrent Gemini calls (and the rendering work that feeds them).
page_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PAGES)

# Tracks book_id -> running asyncio.Task so we never double-process a book.
_running_jobs: dict[str, asyncio.Task] = {}


def is_book_running(book_id: str) -> bool:
    task = _running_jobs.get(book_id)
    return task is not None and not task.done()


def submit_book_job(book_id: str, coro_factory) -> bool:
    """
    Schedule a background job for a book if one isn't already running.
    `coro_factory` is a zero-arg callable returning the coroutine to run
    (kept lazy so we don't build it unless we're actually going to use it).
    Returns True if scheduled, False if a job was already running.
    """
    if is_book_running(book_id):
        logger.info("Book %s already has a running job; skipping duplicate submit", book_id)
        return False

    task = asyncio.create_task(_run_and_cleanup(book_id, coro_factory()))
    _running_jobs[book_id] = task
    return True


async def _run_and_cleanup(book_id: str, coro) -> None:
    try:
        await coro
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error while processing book %s", book_id)
    finally:
        _running_jobs.pop(book_id, None)
