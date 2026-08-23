"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookDetail, Issue } from "@/types";

const TYPE_LABELS: Record<string, string> = {
  spelling: "Spelling",
  grammar: "Grammar",
  punctuation: "Punctuation",
  typographical: "Typographical",
  sentence_structure: "Sentence structure",
  logical: "Logical",
  factual: "Factual",
  duplication: "Duplication",
  other: "Other",
};

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const bookId = params.id;

  const [book, setBook] = useState<BookDetail | null>(null);
  const [issues, setIssues] = useState<Issue[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getBook(bookId), api.getIssues(bookId)])
      .then(([b, i]) => {
        setBook(b);
        setIssues(i);
      })
      .catch(() => setError("Could not load the report. Has processing finished yet?"));
  }, [bookId]);

  if (error) return <p className="text-sm text-signal-red">{error}</p>;
  if (!book || !issues) return <p className="text-sm text-ink/60">Loading…</p>;

  const byType = Object.entries(book.issues_by_type).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">Book report</h1>
          <p className="mt-1 text-sm text-ink/60">{book.original_filename}</p>
        </div>
        <Link href={`/books/${book.id}`} className="text-sm font-medium text-accent hover:text-accent-dark">
          Back to book
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-card">
          <p className="font-mono-data text-3xl font-semibold text-ink">{book.page_count}</p>
          <p className="mt-1 text-sm text-ink/60">Pages</p>
        </div>
        <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-card">
          <p className="font-mono-data text-3xl font-semibold text-ink">{book.issue_count}</p>
          <p className="mt-1 text-sm text-ink/60">Issues</p>
        </div>
        <a
          href={api.reportTxtUrl(book.id)}
          className="flex flex-col justify-center rounded-lg border border-ink/10 bg-white p-5 text-center shadow-card hover:border-accent"
        >
          <span className="text-sm font-medium text-accent">Download TXT</span>
        </a>
        <a
          href={api.reportCsvUrl(book.id)}
          className="flex flex-col justify-center rounded-lg border border-ink/10 bg-white p-5 text-center shadow-card hover:border-accent"
        >
          <span className="text-sm font-medium text-accent">Download CSV</span>
        </a>
      </div>

      {byType.length > 0 && (
        <div className="mt-8 rounded-lg border border-ink/10 bg-white p-6 shadow-card">
          <h2 className="mark font-display text-lg text-ink">Issues by type</h2>
          <div className="mt-4 space-y-3">
            {byType.map(([type, count]) => (
              <div key={type} className="flex items-center gap-4">
                <span className="w-40 text-sm text-ink/70">{TYPE_LABELS[type] || type}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink/10">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${(count / Math.max(...byType.map(([, c]) => c))) * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right font-mono-data text-sm text-ink">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <h2 className="mark font-display text-lg text-ink">All issues</h2>
        {issues.length === 0 && <p className="mt-3 text-sm text-ink/60">No issues were found in this book.</p>}
        <ul className="mt-4 space-y-3">
          {issues.map((issue) => (
            <li key={issue.id} className="rounded-lg border border-ink/10 bg-white p-4 shadow-card">
              <div className="flex items-center justify-between">
                <span className="font-mono-data text-xs uppercase tracking-wide text-ink/50">
                  Page {issue.page_number} · {TYPE_LABELS[issue.type] || issue.type}
                </span>
                <span className="text-xs uppercase tracking-wide text-ink/40">
                  {issue.confidence} confidence
                </span>
              </div>
              <p className="mt-2 text-sm text-ink">
                <span className="rounded bg-signal-red/10 px-1.5 py-0.5 font-mono-data text-signal-red">
                  {issue.found_text}
                </span>
                {issue.suggested_text && (
                  <>
                    {" "}
                    →{" "}
                    <span className="rounded bg-signal-green/10 px-1.5 py-0.5 font-mono-data text-signal-green">
                      {issue.suggested_text}
                    </span>
                  </>
                )}
              </p>
              <p className="mt-2 text-sm text-ink/60">{issue.explanation}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
