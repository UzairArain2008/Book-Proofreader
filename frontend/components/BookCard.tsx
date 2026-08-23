import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import type { Book } from "@/types";

export default function BookCard({ book }: { book: Book }) {
  return (
    <Link
      href={`/books/${book.id}`}
      className="block rounded-lg border border-ink/10 bg-white p-5 shadow-card transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-display text-lg text-ink">{book.original_filename}</p>
          <p className="mt-1 font-mono-data text-sm text-ink/50">{book.page_count} pages</p>
        </div>
        <StatusBadge status={book.status} />
      </div>
      <div className="mt-4 flex items-center gap-6 text-sm text-ink/60">
        <span>
          <span className="font-mono-data font-medium text-ink">{book.issue_count}</span> issues
        </span>
        <span>
          <span className="font-mono-data font-medium text-ink">
            {book.processed_pages}/{book.page_count}
          </span>{" "}
          processed
        </span>
        {book.failed_page_count > 0 && (
          <span className="text-signal-red">{book.failed_page_count} failed</span>
        )}
      </div>
    </Link>
  );
}
