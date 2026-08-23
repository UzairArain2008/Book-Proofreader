"""
Cheap, non-AI proofreading checks.

These run on the page's extracted text before/alongside the Gemini call.
They catch obvious mechanical problems reliably and cheaply, reducing
unnecessary AI work. They are NOT treated as automatically authoritative --
they're tagged with source="deterministic" and a fixed MEDIUM confidence,
since regex heuristics can still be wrong (e.g. intentional repetition).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DeterministicIssue:
    type: str
    severity: str
    confidence: str
    found_text: str
    suggested_text: str
    explanation: str
    location: str
    source: str = "deterministic"


_DUPLICATE_WORD_RE = re.compile(r"\b(\w+)\b(?:\s+\1\b)+", re.IGNORECASE)
_DOUBLE_SPACE_RE = re.compile(r"[ \t]{2,}")
_REPEATED_PUNCT_RE = re.compile(r"([!?.,;:]){2,}")
_UNUSUAL_CHARS_RE = re.compile(r"[\uFFFD\u25A1]")  # replacement char / tofu box


def run_deterministic_checks(page_text: str) -> list[DeterministicIssue]:
    """Run all deterministic checks against a page's extracted text."""
    if not page_text or not page_text.strip():
        return [
            DeterministicIssue(
                type="other",
                severity="low",
                confidence="medium",
                found_text="(empty page text)",
                suggested_text="",
                explanation="No extractable text was found on this page (may be image-only or blank).",
                location="Whole page",
            )
        ]

    issues: list[DeterministicIssue] = []

    for m in _DUPLICATE_WORD_RE.finditer(page_text):
        word = m.group(1)
        repeat_count = len(m.group(0).split())

        if not any(c.isalpha() for c in word):
            # Runs of underscores, dashes, digits, etc. (e.g. "___________"
            # fill-in-the-blank answer lines) are formatting, never real text.
            continue

        if repeat_count >= 3:
            # 3+ consecutive identical words is a strong signature of a design
            # artifact (e.g. drop-shadow/outline text effects stack the same
            # word 2-3 times in the PDF's hidden text layer), not a real typo.
            # Real accidental duplication is almost always exactly 2 repeats.
            issues.append(
                DeterministicIssue(
                    type="other",
                    severity="low",
                    confidence="low",
                    found_text=m.group(0),
                    suggested_text=word,
                    explanation=(
                        f"The word '{word}' appears {repeat_count} times in a row in this page's "
                        "text layer. This is often a rendering artifact from stylized/decorative "
                        "text (e.g. a drop-shadow or outline effect on a cover or heading) rather "
                        "than an actual duplicated word -- check the rendered page before treating "
                        "this as an error."
                    ),
                    location=f"Character offset {m.start()}",
                )
            )
        else:
            issues.append(
                DeterministicIssue(
                    type="duplication",
                    severity="medium",
                    confidence="medium",
                    found_text=m.group(0),
                    suggested_text=word,
                    explanation="A word appears to be accidentally repeated.",
                    location=f"Character offset {m.start()}",
                )
            )

    for m in _DOUBLE_SPACE_RE.finditer(page_text):
        issues.append(
            DeterministicIssue(
                type="typographical",
                severity="low",
                confidence="medium",
                found_text=repr(m.group(0)),
                suggested_text=" ",
                explanation="Unusual spacing detected (multiple consecutive spaces/tabs).",
                location=f"Character offset {m.start()}",
            )
        )

    for m in _REPEATED_PUNCT_RE.finditer(page_text):
        # Ignore ellipses ("...") which are usually intentional.
        if m.group(0) == "...":
            continue
        issues.append(
            DeterministicIssue(
                type="punctuation",
                severity="low",
                confidence="medium",
                found_text=m.group(0),
                suggested_text=m.group(1),
                explanation="Repeated punctuation marks detected.",
                location=f"Character offset {m.start()}",
            )
        )

    for m in _UNUSUAL_CHARS_RE.finditer(page_text):
        issues.append(
            DeterministicIssue(
                type="other",
                severity="medium",
                confidence="medium",
                found_text=m.group(0),
                suggested_text="",
                explanation="An unusual or unrecognized character was found, which may indicate a rendering or encoding problem.",
                location=f"Character offset {m.start()}",
            )
        )

    return issues[:25]  # keep noise bounded; this is a supplement, not the main analysis