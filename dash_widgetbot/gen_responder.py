"""Generate structured AI responses for the /gen command.

Uses Gemini to analyze a prompt, pick the best output format
(article, code, data_table, image, callout), and return a
validated ``GenResponse``.

Reuses ``_get_client()`` from ``ai_responder`` for the shared
lazy-loaded Gemini client.
"""

from __future__ import annotations

import json
import os

from .ai_responder import _get_client
from .gen_schemas import GenResponse

GEN_SYSTEM_PROMPT = """\
You are an AI that generates structured content for a Dash web application.
Given a user prompt, analyze what they want and pick the BEST output format.
Return valid JSON matching the schema below.

## Output Schema

```json
{
  "format": "article" | "code" | "data_table" | "image" | "callout",
  "title": "string (max 80 chars, descriptive title for the card)",
  "color": "#hex color (default #5865F2)",
  "footer": "string or null (small attribution/note)",

  // Fill ONLY the field matching `format`. Leave all others null.

  "article": {
    "body": "markdown text (explanations, tutorials, how-tos)",
    "summary": "one-line summary or null"
  },
  "code": {
    "language": "python|javascript|rust|go|etc",
    "code": "the source code",
    "explanation": "brief explanation or null",
    "filename": "suggested filename or null"
  },
  "data_table": {
    "columns": ["Col1", "Col2", ...],
    "rows": [["val1", "val2", ...], ...],
    "caption": "table caption or null"
  },
  "image": {
    "prompt": "detailed image generation prompt",
    "caption": "caption for the image or null"
  },
  "callout": {
    "variant": "info" | "warning" | "tip" | "success" | "danger",
    "title": "callout title",
    "body": "callout body text"
  }
}
```

## Format Selection Rules

Pick the format that best serves the user's intent:

- **article** -- explanations, tutorials, how-tos, essays, summaries of topics.
  Use when the user asks "explain", "describe", "what is", "how does", etc.

- **code** -- programming tasks, code examples, algorithms, scripts.
  Use when the user asks to "write", "code", "implement", "create a function", etc.

- **data_table** -- comparisons, specs, feature matrices, structured data.
  Use when the user asks to "compare", "list differences", "show features", etc.

- **image** -- visual content, illustrations, diagrams, art.
  Use when the user asks to "draw", "generate an image", "show me", "illustrate", etc.

- **callout** -- tips, warnings, best practices, quick facts, advisories.
  Use when the user asks about "best practice", "important tip", "warning about", \
"key thing to know", etc. Also use for very short factual answers.

## Color Guidelines

- Default: #5865F2 (blurple)
- Code: #2B2D31 (dark)
- Success/tips: #57F287 (green)
- Warnings: #FEE75C (yellow)
- Errors/danger: #ED4245 (red)
- Data: #5865F2 (blurple)

## Rules

1. Return ONLY valid JSON -- no markdown fences, no extra text.
2. Fill ONLY the content field that matches `format`. All others must be null.
3. For articles, use proper markdown formatting (headers, bold, lists, code spans).
4. For code, always specify the language and write clean, well-commented code.
5. For data tables, ensure all rows have the same number of columns.
6. For images, write a detailed, descriptive prompt suitable for image generation.
7. For callouts, keep body text concise and actionable.
8. Always include a footer like "Powered by 2plot.ai".

## Web Search

You have access to Google Search. Use it for factual, current, or specific information.
"""


def generate_gen_response(prompt: str) -> dict:
    """Generate a structured /gen response.

    Parameters
    ----------
    prompt : str
        The user's generation prompt.

    Returns
    -------
    dict
        ``{"response": GenResponse | None, "raw_json": dict | None, "error": str | None}``
    """
    try:
        client = _get_client()
        from google.genai import types
    except (ImportError, ValueError) as exc:
        return {"response": None, "raw_json": None, "error": str(exc)}

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Google Search grounding
    search_enabled = os.getenv("GEMINI_SEARCH_GROUNDING", "true").lower() == "true"
    tools = [types.Tool(google_search=types.GoogleSearch())] if search_enabled else None

    try:
        result = client.models.generate_content(
            model=model_name,
            contents=[f"{GEN_SYSTEM_PROMPT}\n\nUser prompt: {prompt}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                tools=tools,
            ),
        )
        raw_text = result.text or ""

        # Parse JSON
        try:
            raw_json = json.loads(raw_text)
        except json.JSONDecodeError as je:
            return {
                "response": None,
                "raw_json": None,
                "error": f"JSON parse error: {je}. Raw: {raw_text[:300]}",
            }

        # Validate with Pydantic
        try:
            gen_resp = GenResponse.model_validate(raw_json)
        except Exception as ve:
            return {
                "response": None,
                "raw_json": raw_json,
                "error": f"Validation error: {ve}",
            }

        return {"response": gen_resp, "raw_json": raw_json, "error": None}

    except Exception as exc:
        return {"response": None, "raw_json": None, "error": str(exc)}
