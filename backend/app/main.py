"""FastAPI application entrypoint for AI Book Proofreader."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import books, reports, upload
from app.config import settings
from app.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("proofreader.main")

app = FastAPI(
    title="AI Book Proofreader",
    description="Uploads a book PDF, proofreads it page-by-page with Gemini, and produces TXT/CSV reports.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(books.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if not settings.GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY is not set. Set it in backend/.env before uploading books, "
            "or page processing will fail."
        )
    logger.info("AI Book Proofreader backend ready. Storage dir: %s", settings.storage_path.resolve())


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}
