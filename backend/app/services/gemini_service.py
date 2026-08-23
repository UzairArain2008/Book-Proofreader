"""
Gemini integration.

Responsibilities:
- Build the strict, single-page proofreading prompt (+ optional adjacent-page
  TEXT context, never adjacent-page images).
- Call the Gemini API with ONLY the current page image + prompt.
- Enforce a JSON response schema, parse it, and validate it with Pydantic.
- Retry a bounded number of times on transient failures / malformed JSON,
  with exponential backoff for rate limits.

This is the only module that talks to Google. If Gemini is swapped for
another vision model later, only this file needs to change.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import ValidationError

from app.config import settings
from app.schemas.schemas import GeminiPageResult
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger("proofreader.gemini")

SYSTEM_INSTRUCTION = """You are a professional book proofreader working for a publishing company.

Analyze ONLY the CURRENT PAGE image provided.

IMPORTANT CONTEXT: Many books you review are children's textbooks, ESL/EFL
workbooks, and grammar exercise books. These intentionally contain:
- Simplified, repetitive sentence patterns aimed at young learners
- Worked example answers (often marked with a star, arrow, or number) that
  demonstrate the exact pattern students should copy -- these are the
  official answer key, not free prose
- Exercise prompts deliberately phrased in a non-standard or incomplete way
  because rewriting them into "correct" adult English IS the exercise
  (e.g. "Change into negative commands", "Join using 'or'", "Use of 'me,
  you, it, him, her, them'")
- Regional/dialect English conventions that are correct for the book's
  intended audience even if they differ from another English variety
Before flagging a grammar, sentence-structure, or wording issue, check
whether the sentence is a lesson heading's own worked example, a starred
model answer, or part of a drill whose entire point is that exact pattern.
If so, do NOT report it as an error -- it is functioning as intended.
Only flag grammar/wording issues in sentences that are clearly meant to
already be correct, finished prose (not an exercise pattern to be learned).

Find genuine problems in:
1. Spelling
2. Grammar
3. Punctuation
4. Sentence structure
5. Typographical errors
6. Obvious logical inconsistencies
7. Obvious factual inconsistencies
8. Incorrect or contradictory wording
9. Text that appears to be accidentally duplicated or missing

Do NOT invent mistakes.
Do NOT rewrite sentences merely because you prefer a different writing style.
Do NOT report stylistic preferences as errors.
Do NOT report information from other pages as an error on this page.
Do NOT report an exercise's intentional model pattern as a grammar error.
If a possible issue is uncertain, mark the confidence as MEDIUM or LOW.
Only report issues that have reasonable evidence.
Never claim the page is "guaranteed error-free" -- if nothing is found, simply return an empty issues list.
For logical or factual concerns, prefer describing them as "potential" issues unless the evidence is strong.

Analyze ONLY the current page. The previous and next page text (if provided) is for
CONTEXT ONLY, to help you understand continuing sentences or numbering. Do not report
mistakes that actually belong to the previous or next page.

Return ONLY valid JSON matching the required schema. No Markdown, no commentary, no code fences.
"""

# JSON Schema enforced via Gemini's response_schema / response_mime_type=application/json.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {"type": "integer"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "spelling", "grammar", "punctuation", "typographical",
                            "sentence_structure", "logical", "factual", "duplication", "other",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "found_text": {"type": "string"},
                    "suggested_text": {"type": "string"},
                    "explanation": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["type", "severity", "confidence", "found_text", "explanation"],
            },
        },
    },
    "required": ["page", "issues"],
}


@dataclass
class GeminiCallResult:
    success: bool
    result: GeminiPageResult | None = None
    error: str | None = None


class GeminiService:
    def __init__(self) -> None:
        self._client: genai.Client | None = None
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. Gemini calls will fail until configured.")
        self._rate_limiter = RateLimiter(max_calls=settings.GEMINI_REQUESTS_PER_MINUTE)

    @property
    def client(self) -> genai.Client:
        # Created lazily so the app can start (and show a clear warning) even
        # before GEMINI_API_KEY has been configured in .env.
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _build_contents(
        self, page_number: int, image_bytes: bytes, prev_text: str, next_text: str
    ) -> list:
        context_block = ""
        if prev_text or next_text:
            context_block = (
                "\n\nPREVIOUS PAGE TEXT (context only, do not analyze):\n"
                f"{prev_text or '(none)'}\n\n"
                "NEXT PAGE TEXT (context only, do not analyze):\n"
                f"{next_text or '(none)'}\n"
            )

        prompt_text = (
            f"CURRENT PAGE: page {page_number} of the book (image attached below).{context_block}\n\n"
            f'Respond with JSON like: {{"page": {page_number}, "issues": [...]}}'
        )

        return [
            types.Part.from_text(text=prompt_text),
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ]

    async def analyze_page(
        self,
        page_number: int,
        image_bytes: bytes,
        prev_text: str = "",
        next_text: str = "",
    ) -> GeminiCallResult:
        """Call Gemini for a single page with bounded retries and backoff."""
        max_retries = settings.GEMINI_MAX_RETRIES
        last_error = "unknown error"

        for attempt in range(1, max_retries + 1):
            try:
                await self._rate_limiter.acquire()

                response = await self.client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=self._build_contents(page_number, image_bytes, prev_text, next_text),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.1,
                    ),
                )
                raw_text = (response.text or "").strip()
                parsed = self._parse_and_validate(raw_text, page_number)
                return GeminiCallResult(success=True, result=parsed)

            except genai_errors.ClientError as exc:
                # Rate limit / quota (HTTP 429) -> exponential backoff and retry.
                status = getattr(exc, "code", None)
                last_error = f"Gemini client error: {exc}"
                if status == 429 and attempt < max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.info("Rate limited on page %s, backing off %ss", page_number, wait)
                    await asyncio.sleep(wait)
                    continue
                logger.error("Gemini client error on page %s: %s", page_number, exc)
                break

            except genai_errors.ServerError as exc:
                last_error = f"Gemini server error: {exc}"
                if attempt < max_retries:
                    wait = min(2 ** attempt, 30)
                    await asyncio.sleep(wait)
                    continue
                break

            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = f"Malformed/invalid JSON from Gemini: {exc}"
                logger.warning("Page %s attempt %s: %s", page_number, attempt, last_error)
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                break

            except asyncio.TimeoutError:
                last_error = "Gemini request timed out"
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                break

            except Exception as exc:  # noqa: BLE001 - defensive catch-all so one page can't crash the job
                last_error = f"Unexpected error: {exc}"
                logger.exception("Unexpected Gemini error on page %s", page_number)
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                break

        return GeminiCallResult(success=False, error=last_error)

    @staticmethod
    def _parse_and_validate(raw_text: str, page_number: int) -> GeminiPageResult:
        # Defensive cleanup in case the model wraps JSON in code fences despite instructions.
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        result = GeminiPageResult.model_validate(data)

        # Force the page number to the one we actually sent, regardless of what the model echoed.
        if result.page != page_number:
            result = result.model_copy(update={"page": page_number})
        return result


gemini_service = GeminiService()
