"""
Renders individual PDF pages to optimized images for AI analysis.

Each page is rendered independently (never the whole book at once), sized to
a resolution that's good for OCR/text recognition without being unnecessarily
huge, and compressed before it's handed to the Gemini service.
"""
from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# Cap the longest image edge to keep payloads small even at high render DPI.
MAX_LONG_EDGE_PX = 2000
JPEG_QUALITY = 85


def render_page_to_image_bytes(doc: "fitz.Document", page_number_1_indexed: int, dpi: int) -> bytes:
    """Render a single page (1-indexed) to compressed JPEG bytes."""
    idx = page_number_1_indexed - 1
    if idx < 0 or idx >= doc.page_count:
        raise ValueError(f"Page {page_number_1_indexed} out of range")

    page = doc.load_page(idx)
    zoom = dpi / 72.0  # PDF base unit is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # Downscale if the render exceeded our max edge, to keep upload size sane.
    longest = max(img.width, img.height)
    if longest > MAX_LONG_EDGE_PX:
        scale = MAX_LONG_EDGE_PX / longest
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def save_page_image(image_bytes: bytes, pages_dir: Path, book_id: str, page_number: int) -> Path:
    """Persist a rendered page image temporarily on disk (deleted after processing)."""
    book_dir = pages_dir / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    out_path = book_dir / f"page_{page_number:05d}.jpg"
    out_path.write_bytes(image_bytes)
    return out_path
