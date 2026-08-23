"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import BookCard from "@/components/BookCard";
import type { Book } from "@/types";
import { api } from "@/lib/api";

export default function BooksPage() {
  const [books, setBooks] = useState<Book[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listBooks()
      .then((data) => !cancelled && setBooks(data))
      .catch(() => !cancelled && setError("Could not load books. Is the backend running?"));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-semibold text-ink">Books</h1>
        <Link
          href="/upload"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
        >
          Upload a book
        </Link>
      </div>

      {error && <p className="mt-6 text-sm text-signal-red">{error}</p>}

      {books && books.length === 0 && (
        <div className="mt-10 rounded-lg border border-dashed border-ink/20 bg-white p-12 text-center">
          <p className="font-display text-lg text-ink">No books yet</p>
          <p className="mt-1 text-sm text-ink/60">Upload a PDF to start your first proofreading run.</p>
        </div>
      )}

      {books && books.length > 0 && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {books.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      )}
    </div>
  );
}
