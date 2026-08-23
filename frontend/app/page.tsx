"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import BookCard from "@/components/BookCard";
import type { Book } from "@/types";
import { api } from "@/lib/api";

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-card">
      <p className="font-mono-data text-3xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink/60">{label}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [books, setBooks] = useState<Book[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listBooks()
      .then((data) => !cancelled && setBooks(data))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const totalBooks = books?.length ?? 0;
  const processing = books?.filter((b) => b.status === "processing" || b.status === "queued").length ?? 0;
  const completed = books?.filter((b) => b.status === "completed" || b.status === "completed_with_errors").length ?? 0;
  const totalIssues = books?.reduce((sum, b) => sum + b.issue_count, 0) ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">Dashboard</h1>
          <p className="mt-1 text-sm text-ink/60">An overview of proofreading activity across your books.</p>
        </div>
        <Link
          href="/upload"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
        >
          Upload a book
        </Link>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Total Books" value={totalBooks} />
        <StatTile label="Processing" value={processing} />
        <StatTile label="Completed" value={completed} />
        <StatTile label="Total Issues" value={totalIssues} />
      </div>

      <div className="mt-10">
        <div className="flex items-center justify-between">
          <h2 className="mark font-display text-xl text-ink">Recent books</h2>
          <Link href="/books" className="text-sm font-medium text-accent hover:text-accent-dark">
            View all
          </Link>
        </div>

        {books && books.length === 0 && (
          <div className="mt-6 rounded-lg border border-dashed border-ink/20 bg-white p-12 text-center">
            <p className="font-display text-lg text-ink">No books yet</p>
            <p className="mt-1 text-sm text-ink/60">Upload a PDF to start your first proofreading run.</p>
          </div>
        )}

        {books && books.length > 0 && (
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {books.slice(0, 4).map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
