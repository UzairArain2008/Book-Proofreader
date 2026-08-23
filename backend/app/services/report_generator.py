"""Generates the two nontechnical-friendly report files: TXT and CSV."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from app.models.models import Book, Issue, Page

SEVERITY_LABEL = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}
TYPE_LABEL = {
    "spelling": "SPELLING ERROR",
    "grammar": "GRAMMAR ERROR",
    "punctuation": "PUNCTUATION ERROR",
    "typographical": "TYPOGRAPHICAL ERROR",
    "sentence_structure": "SENTENCE STRUCTURE ISSUE",
    "logical": "POTENTIAL LOGICAL ISSUE",
    "factual": "POTENTIAL FACTUAL ISSUE",
    "duplication": "DUPLICATED TEXT",
    "other": "OTHER ISSUE",
}


def build_txt_report(book: Book, pages: list[Page], issues_by_page: dict[int, list[Issue]]) -> str:
    lines: list[str] = []
    lines.append("=" * 40)
    lines.append("BOOK PROOFREADING REPORT")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Book: {book.original_filename}")
    lines.append(f"Total Pages: {book.page_count}")
    lines.append(f"Total Issues: {book.issue_count}")
    if book.failed_page_count:
        lines.append(f"Pages That Could Not Be Analyzed: {book.failed_page_count}")
    lines.append("")

    for page in pages:
        lines.append("=" * 40)
        lines.append(f"PAGE {page.page_number}")
        lines.append("=" * 40)
        lines.append("")

        if page.status == "failed":
            lines.append("THIS PAGE COULD NOT BE ANALYZED")
            lines.append(f"Reason: {page.error_message or 'Unknown error'}")
            lines.append("")
            continue

        page_issues = issues_by_page.get(page.page_number, [])
        if not page_issues:
            lines.append("NO ISSUES FOUND")
            lines.append("")
            continue

        for i, issue in enumerate(page_issues, start=1):
            label = TYPE_LABEL.get(issue.type, issue.type.upper())
            lines.append(f"[{i}] {label}")
            lines.append("")
            lines.append("Found:")
            lines.append(issue.found_text)
            lines.append("")
            if issue.suggested_text:
                lines.append("Suggested:")
                lines.append(issue.suggested_text)
                lines.append("")
            lines.append("Reason:")
            lines.append(issue.explanation)
            lines.append("")
            lines.append("Confidence:")
            lines.append(SEVERITY_LABEL.get(issue.confidence, issue.confidence.upper()))
            lines.append("")
            lines.append("")

    return "\n".join(lines)


def build_csv_report(issues: list[Issue]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["page", "type", "severity", "confidence", "found_text", "suggested_text", "explanation", "location"]
    )
    for issue in issues:
        writer.writerow(
            [
                issue.page_number,
                issue.type,
                issue.severity,
                issue.confidence,
                issue.found_text,
                issue.suggested_text,
                issue.explanation,
                issue.location,
            ]
        )
    return buf.getvalue()


def write_reports_to_disk(reports_dir: Path, book_id: str, txt_content: str, csv_content: str) -> tuple[Path, Path]:
    book_dir = reports_dir / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    txt_path = book_dir / "proofreading_report.txt"
    csv_path = book_dir / "proofreading_report.csv"
    txt_path.write_text(txt_content, encoding="utf-8")
    csv_path.write_text(csv_content, encoding="utf-8", newline="")
    return txt_path, csv_path
