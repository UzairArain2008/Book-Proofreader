"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import ProgressBar from "@/components/ProgressBar";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import type { BookDetail, BookProgress } from "@/types";

const TERMINAL_STATUSES = new Set(["completed", "completed_with_errors", "failed"]);

export default function BookDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const bookId = params.id;

  const [book, setBook] = useState<BookDetail | null>(null);
  const [progress, setProgress] = useState<BookProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function loadBook() {
    try {
      const data = await api.getBook(bookId);
      setBook(data);
    } catch {
      setError("Could not load this book.");
    }
  }

  useEffect(() => {
    loadBook();
    const tick = async () => {
      try {
        const p = await api.getProgress(bookId);
        setProgress(p);
        if (TERMINAL_STATUSES.has(p.status) && pollRef.current) {
          clearInterval(pollRef.current);
          loadBook();
        }
      } catch {
        // ignore transient errors while polling
      }
    };
    tick();
    pollRef.current = setInterval(tick, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  async function handleRetry() {
    setBusy(true);
    setError(null);
    try {
      await api.retryFailed(bookId);
      pollRef.current = setInterval(async () => {
        const p = await api.getProgress(bookId);
        setProgress(p);
        if (TERMINAL_STATUSES.has(p.status) && pollRef.current) {
          clearInterval(pollRef.current);
          loadBook();
        }
      }, 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not retry failed pages.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this book and all of its reports? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.deleteBook(bookId);
      router.push("/books");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete this book.");
      setBusy(false);
    }
  }

  if (!book) {
    return <p className="text-sm text-ink/60">{error ?? "Loading…"}</p>;
  }

  const status = progress?.status ?? book.status;
  const isDone = TERMINAL_STATUSES.has(status);
  const failedPages = progress?.pages.filter((p) => p.status === "failed") ?? book.pages.filter((p) => p.status === "failed");

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">{book.original_filename}</h1>
          <p className="mt-1 font-mono-data text-sm text-ink/50">{book.page_count} pages</p>
        </div>
        <StatusBadge status={status} />
      </div>

      {error && <p className="mt-4 rounded-md bg-signal-red/10 px-4 py-3 text-sm text-signal-red">{error}</p>}

      <div className="mt-8 rounded-lg border border-ink/10 bg-white p-6 shadow-card">
        <h2 className="mark font-display text-lg text-ink">Processing</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="font-mono-data text-2xl font-semibold text-ink">{book.page_count}</p>
            <p className="text-sm text-ink/60">Pages</p>
          </div>
          <div>
            <p className="font-mono-data text-2xl font-semibold text-ink">{progress?.processed_pages ?? book.processed_pages}</p>
            <p className="text-sm text-ink/60">Processed</p>
          </div>
          <div>
            <p className="font-mono-data text-2xl font-semibold text-ink">
              {progress?.remaining_pages ?? Math.max(book.page_count - book.processed_pages, 0)}
            </p>
            <p className="text-sm text-ink/60">Remaining</p>
          </div>
          <div>
            <p className="font-mono-data text-2xl font-semibold text-ink">{progress?.issue_count ?? book.issue_count}</p>
            <p className="text-sm text-ink/60">Issues found</p>
          </div>
        </div>

        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between text-sm text-ink/60">
            <span>
              {progress?.current_page ? `Currently on page ${progress.current_page}` : isDone ? "Finished" : "Waiting to start…"}
            </span>
            <span className="font-mono-data">{progress?.progress_percent ?? 0}%</span>
          </div>
          <ProgressBar percent={progress?.progress_percent ?? (isDone ? 100 : 0)} />
        </div>
      </div>

      {failedPages.length > 0 && (
        <div className="mt-6 rounded-lg border border-signal-red/20 bg-signal-red/5 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-display text-lg text-ink">
                {failedPages.length} page{failedPages.length === 1 ? "" : "s"} failed
              </p>
              <p className="mt-1 text-sm text-ink/60">
                These pages could not be analyzed. You can retry just the failed pages.
              </p>
            </div>
            <button
              onClick={handleRetry}
              disabled={busy}
              className="rounded-md bg-signal-red px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              Retry failed pages
            </button>
          </div>
          <ul className="mt-4 space-y-1 text-sm text-ink/70">
            {failedPages.map((p) => (
              <li key={p.id} className="font-mono-data">
                Page {p.page_number} — {p.error_message || "Unknown error"}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 flex items-center gap-3">
        {isDone && (
          <Link
            href={`/books/${book.id}/report`}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
          >
            View report
          </Link>
        )}
        <button
          onClick={handleDelete}
          disabled={busy}
          className="rounded-md border border-ink/20 px-4 py-2 text-sm font-medium text-ink/70 hover:bg-ink/5 disabled:opacity-50"
        >
          Delete book
        </button>
      </div>
    </div>
  );
}