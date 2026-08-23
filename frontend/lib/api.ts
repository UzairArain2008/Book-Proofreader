import type { Book, BookDetail, BookProgress, Issue, UploadResponse } from "@/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options?.body && !(options.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...options?.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors, fall back to statusText
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  uploadBook: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/api/books/upload", { method: "POST", body: form });
  },
  listBooks: () => request<Book[]>("/api/books"),
  getBook: (id: string) => request<BookDetail>(`/api/books/${id}`),
  getProgress: (id: string) => request<BookProgress>(`/api/books/${id}/progress`),
  getIssues: (id: string) => request<Issue[]>(`/api/books/${id}/issues`),
  retryFailed: (id: string) => request<Book>(`/api/books/${id}/retry-failed`, { method: "POST" }),
  deleteBook: (id: string) => request<void>(`/api/books/${id}`, { method: "DELETE" }),
  reportTxtUrl: (id: string) => `${API_BASE_URL}/api/books/${id}/report/txt`,
  reportCsvUrl: (id: string) => `${API_BASE_URL}/api/books/${id}/report/csv`,
};

export { ApiError };
