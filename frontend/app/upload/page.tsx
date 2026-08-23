"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import FileDropzone from "@/components/FileDropzone";
import ProgressBar from "@/components/ProgressBar";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import type { Book, BookProgress } from "@/types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export default function UploadPage() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [book, setBook] = useState<Book | null>(null);
  const [progress, setProgress] = useState<BookProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setUploading(true);
    try {
      const res = await api.uploadBook(file);
      setBook(res.book);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    if (!book) return;
    const tick = async () => {
      try {
        const p = await api.getProgress(book.id);
        setProgress(p);
        if (p.status === "completed" || p.status === "completed_with_errors" || p.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // transient polling error; keep trying
      }
    };
    tick();
    pollRef.current = setInterval(tick, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [book]);

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-display text-3xl font-semibold text-ink">Upload a book</h1>
      <p className="mt-2 text-sm text-ink/60">
        Upload a PDF and it will be proofread one page at a time. Larger books take longer;
        you can leave this page and check progress later from the Books list.
      </p>

      <div className="mt-8">
        {!book && <FileDropzone onFileSelected={handleFile} disabled={uploading} />}
        {uploading && <p className="mt-4 text-sm text-ink/60">Uploading and validating your PDF…</p>}
        {error && (
          <p className="mt-4 rounded-md bg-signal-red/10 px-4 py-3 text-sm text-signal-red">{error}</p>
        )}
      </div>

      {book && (
        <div className="mt-4 rounded-lg border border-ink/10 bg-white p-6 shadow-card">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-display text-lg text-ink">{book.original_filename}</p>
              <p className="mt-1 font-mono-data text-sm text-ink/50">
                {book.page_count} pages · {formatBytes(book.file_size)}
              </p>
            </div>
            <StatusBadge status={progress?.status ?? book.status} />
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between text-sm text-ink/60">
              <span>
                {progress?.current_page
                  ? `Page ${progress.current_page} / ${book.page_count}`
                  : `${progress?.processed_pages ?? 0} / ${book.page_count} pages`}
              </span>
              <span className="font-mono-data">{progress?.progress_percent ?? 0}%</span>
            </div>
            <ProgressBar percent={progress?.progress_percent ?? 0} />
          </div>

          {progress && (progress.status === "completed" || progress.status === "completed_with_errors") && (
            <div className="mt-6 flex items-center justify-between rounded-md bg-accent/5 px-4 py-3">
              <p className="text-sm text-ink">
                Done. Found <strong>{progress.issue_count}</strong> issue
                {progress.issue_count === 1 ? "" : "s"}
                {progress.failed_page_count > 0 && (
                  <> ({progress.failed_page_count} page{progress.failed_page_count === 1 ? "" : "s"} failed)</>
                )}
                .
              </p>
              <button
                onClick={() => router.push(`/books/${book.id}/report`)}
                className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
              >
                View report
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
