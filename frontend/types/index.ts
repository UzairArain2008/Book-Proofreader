export type BookStatus =
  | "queued"
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed";

export type PageStatus = "pending" | "processing" | "completed" | "failed";

export type IssueType =
  | "spelling"
  | "grammar"
  | "punctuation"
  | "typographical"
  | "sentence_structure"
  | "logical"
  | "factual"
  | "duplication"
  | "other";

export type Severity = "low" | "medium" | "high";
export type Confidence = "low" | "medium" | "high";

export interface Book {
  id: string;
  original_filename: string;
  file_size: number;
  page_count: number;
  status: BookStatus;
  processed_pages: number;
  issue_count: number;
  failed_page_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface BookDetail extends Book {
  issues_by_type: Record<string, number>;
  pages: Page[];
}

export interface Page {
  id: string;
  page_number: number;
  status: PageStatus;
  issue_count: number;
  error_message: string | null;
  processed_at: string | null;
}

export interface Issue {
  id: string;
  page_number: number;
  type: IssueType;
  severity: Severity;
  confidence: Confidence;
  found_text: string;
  suggested_text: string;
  explanation: string;
  location: string;
  source: "ai" | "deterministic";
}

export interface BookProgress {
  book_id: string;
  status: BookStatus;
  page_count: number;
  processed_pages: number;
  remaining_pages: number;
  issue_count: number;
  failed_page_count: number;
  progress_percent: number;
  current_page: number | null;
  pages: Page[];
}

export interface UploadResponse {
  book: Book;
  message: string;
}
