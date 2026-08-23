import type { BookStatus, PageStatus } from "@/types";

const STYLES: Record<string, string> = {
  queued: "bg-ink/5 text-ink/60",
  pending: "bg-ink/5 text-ink/60",
  processing: "bg-accent/10 text-accent-dark",
  completed: "bg-signal-green/10 text-signal-green",
  completed_with_errors: "bg-signal-amber/10 text-signal-amber",
  failed: "bg-signal-red/10 text-signal-red",
};

const LABELS: Record<string, string> = {
  queued: "Queued",
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  completed_with_errors: "Completed (some errors)",
  failed: "Failed",
};

export default function StatusBadge({ status }: { status: BookStatus | PageStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
        STYLES[status] || "bg-ink/5 text-ink/60"
      }`}
    >
      {LABELS[status] || status}
    </span>
  );
}
