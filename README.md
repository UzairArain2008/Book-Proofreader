# AI Book Proofreader

An MVP web application for publishing teams: upload a book as a PDF, and it
gets proofread **one page at a time** by a vision-capable Google Gemini
model. The result is a plain-language `.txt` report and a `.csv` report that
nontechnical staff can open in Excel.

The book is never sent to the AI in one piece — each page is rendered to an
image and analyzed independently, with only a small amount of adjacent-page
*text* (not images) provided as optional context.

---

## Project layout

```text
ai-book-proofreader/
├── backend/     FastAPI + PyMuPDF + Gemini
├── frontend/    Next.js + React + TypeScript + Tailwind
└── storage/     (created automatically) uploaded PDFs, temp page images, reports
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key: https://aistudio.google.com/apikey

## 1. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Open `backend/.env` and set:

```env
GEMINI_API_KEY=your-key-here
```

Everything else has a sensible default (see "Configuration" below).

Start the API:

```bash
uvicorn app.main:app --reload
```

The backend runs at **http://localhost:8000**. Interactive API docs are
available at http://localhost:8000/docs.

## 2. Frontend setup

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_URL defaults to http://localhost:8000
npm run dev
```

The dashboard runs at **http://localhost:3000**.

## 3. Use it

1. Open http://localhost:3000/upload
2. Drag a PDF onto the upload area (or click to choose a file)
3. Watch the page-by-page progress bar
4. Open the book's report page to see issues grouped by type
5. Download `proofreading_report.txt` and `proofreading_report.csv`

---

## How the pipeline works

```text
Upload PDF → validate → extract metadata (page count)
   ↓
For each page (bounded concurrency, MAX_CONCURRENT_PAGES):
   render page → PyMuPDF → JPEG image
   run cheap deterministic checks (duplicate words, double spaces, etc.)
   send ONLY that page's image (+ small previous/next page TEXT for context)
      to Gemini with a strict proofreading prompt
   parse + validate the JSON response
   on success: store issues
   on failure: mark the page FAILED, keep processing the rest of the book
   ↓
Generate proofreading_report.txt and proofreading_report.csv
```

A failed page never stops the whole book. Failed pages can be retried
individually from the book's detail page (`Retry failed pages`), and only
those pages are re-sent to Gemini.

## Configuration (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Your Gemini API key. Required. | *(empty)* |
| `GEMINI_MODEL` | Gemini model name. Change here if Google renames/retires a model. | `gemini-2.5-flash-lite` |
| `DATABASE_URL` | SQLAlchemy connection string. Swap to a `postgresql://...` URL later without code changes. | `sqlite:///./storage/proofreader.db` |
| `MAX_FILE_SIZE_MB` | Reject uploads larger than this. | `500` |
| `MAX_CONCURRENT_PAGES` | How many pages are sent to Gemini at the same time. Keep this low to respect rate limits. | `3` |
| `PAGE_RENDER_DPI` | Resolution used when rendering PDF pages to images. | `200` |
| `DELETE_TEMP_FILES` | Delete rendered page images after processing. | `true` |
| `STORAGE_DIR` | Where uploads/pages/reports are stored. | `./storage` |
| `FRONTEND_ORIGIN` | Allowed CORS origin for the frontend. | `http://localhost:3000` |

## Notes on scope (intentionally left out of this MVP)

Per the project brief, this MVP does **not** include authentication,
payments, multi-tenant teams, Kubernetes/microservices, or a CorelDRAW (CDR)
conversion step. Publishers should export CDR/DOCX/PPTX/INDD files to PDF
before uploading; the backend's page-rendering and Gemini services are
already isolated behind clear module boundaries (`pdf_processor`,
`page_renderer`, `gemini_service`) so a conversion layer or a different AI
provider can be dropped in later without touching the rest of the app.

## Privacy

Uploaded books may be unpublished commercial material. By default this app:

- never sends the whole book to Gemini, only one page image at a time
- deletes rendered page images from disk after each book finishes processing
  (`DELETE_TEMP_FILES=true`)
- never logs full page text or full API responses
- keeps the Gemini API key on the backend only — it is never exposed to the
  frontend or the browser

Deleting a book (from the Books page) removes its uploaded PDF, any
leftover page images, and its generated reports from disk.
