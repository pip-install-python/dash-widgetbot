"""Generate AI responses using Gemini.

Provides two modes:
- ``generate_response()`` — legacy plain-text with [ACTION:...] tags
- ``generate_structured_response()`` — JSON-mode structured output → AIResponse
"""

import json
import os

from .action_parser import parse_actions
from .ai_schemas import AIResponse

_client = None


def reset_client():
    """Force a fresh Gemini client on the next call (clears stale httpx connections)."""
    global _client
    _client = None

# ---------------------------------------------------------------------------
# Legacy system prompt (plain-text with action tags)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a helpful Discord bot assistant embedded in a Dash web application.

When your response should trigger an action in the Dash app, include action tags
using this exact format: [ACTION:type:data]

Available actions:
- [ACTION:navigate:/page-path] -- navigate to a page in the Dash app
- [ACTION:notify:message text] -- show a notification in the Crate widget
- [ACTION:toggle:true] or [ACTION:toggle:false] -- open or close the chat widget
- [ACTION:hide:] -- hide the chat widget entirely
- [ACTION:show:] -- show a hidden chat widget
- [ACTION:open_url:https://example.com] -- open a URL in a new tab

Rules:
- Place action tags at the END of your message, after the human-readable text.
- You can include multiple actions in one response.
- Only use actions when they are relevant to the user's request.
- Always provide a helpful text response alongside any actions.
"""

# ---------------------------------------------------------------------------
# Structured system prompt (JSON-mode → AIResponse schema)
# ---------------------------------------------------------------------------

STRUCTURED_SYSTEM_PROMPT = """\
You are a Discord bot that returns beautifully formatted responses using \
Discord's Components V2 message system. You MUST return valid JSON matching \
the schema below. Do NOT return anything except the JSON object.

## Output Schema

```json
{
  "title": "string (max 60 chars, start with emoji)",
  "color": "primary|success|warning|danger|neutral",
  "components": [
    // 1-8 blocks. Exactly ONE field per block:
    {"text": {"content": "markdown text"}},
    {"section": {"text": "markdown", "thumbnail_url": "url", "thumbnail_alt": "alt"}},
    {"gallery": {"items": [{"url": "url", "alt": "alt text"}]}},
    {"button_row": {"buttons": [{"label": "text", "url": "url", "emoji": "optional"}]}},
    {"separator": true}
  ],
  "footer": "string or null (small disclaimer text)",
  "image_prompt": "string or null (ONLY if user explicitly asks for an image)",
  "actions": [{"type": "navigate|notify|toggle|open_url", "data": "value"}]
}
```

## Discord Markdown Reference

Use these in "content" fields:
- `# Heading` — one per response (the title already serves as H1)
- `## Subheading` — major sections
- `### Sub-subheading` — minor sections
- `**bold**` — key values, important terms
- `*italic*` — secondary emphasis
- `-# small text` — disclaimers, footnotes, metadata
- `> quote` — quoting users or highlighting
- `` `code` `` — commands, IDs, technical terms
- `- item` — bulleted lists
- `1. item` — numbered lists
- `[text](url)` — hyperlinks

## Color Semantics

Map color to meaning:
- **primary** (#5865F2 blurple) — general info, default
- **success** (#57F287 green) — confirmations, positive outcomes
- **warning** (#FEE75C yellow) — cautions, important notices
- **danger** (#ED4245 red) — errors, destructive actions
- **neutral** (#99AAB5 gray) — muted, low-priority info

## Emoji Design System

Use emoji as semantic indicators (max 2 per line):
- ✅ success/complete  ❌ error/failed  ⚠️ warning/caution
- ℹ️ info/notice  ✨ new/feature  📊 data/stats
- 🔒 locked/restricted  🔗 link/external  ⚙️ settings
- 🕐 time/schedule  💰 financial  👤 user-related

## Formatting Rules

1. Title MUST start with a relevant emoji: "✨ Getting Started", "⚠️ Warning"
2. Use **bold for values**, not labels: "**42ms** response time" not "**Response Time:** 42ms"
3. Maximum 2 emoji per line of text
4. One heading per text block; use bold for sub-emphasis
5. Footer should be small text like "-# Powered by 2plot.ai"
6. Keep text blocks concise — break long content into multiple blocks
7. Use separators between thematic sections (but don't over-separate)

## Image Generation

Set `image_prompt` ONLY when the user explicitly asks you to:
- draw, create, generate, make, paint, sketch an image/picture/illustration
- show me what X looks like

Do NOT set image_prompt for general questions. The prompt should be a detailed
description suitable for an image generation model.

## Dash App Actions

Include actions only when relevant:
- `{"type": "navigate", "data": "/page-path"}` — navigate to a page
- `{"type": "notify", "data": "message"}` — show a notification
- `{"type": "toggle", "data": "true|false"}` — open/close chat widget
- `{"type": "open_url", "data": "https://..."}` — open URL in new tab

Available pages: /, /crate-commands, /crate-events, /crate-styling, \
/widget-embed, /multi-instance, /bot-bridge, /slash-commands, /ai-chat, \
/webhook-send, /rich-messages, /rich-message-preview

## Web Search

You have access to Google Search and can look up live information from the web.
When answering questions about specific websites, URLs, people, current events,
or anything that benefits from up-to-date information, use your search capability.
Include relevant [text](url) links in your content where helpful.

## Response Guidelines

- Be helpful, concise, and well-structured
- Use 2-5 content blocks for most responses
- Prefer text blocks for explanations; sections when you have a relevant image
- Always include a footer
- Match color to the tone of your response
"""


def _get_client():
    """Lazy-load the google.genai Client on first call."""
    global _client
    if _client is not None:
        return _client
    try:
        from google import genai  # noqa: F811
    except ImportError:
        raise ImportError(
            "google-genai is required for AI responses. "
            "Install it with: pip install google-genai>=1.0.0"
        )
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    _client = genai.Client(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Legacy: plain-text response
# ---------------------------------------------------------------------------

def generate_response(user_message, *, context=None, system_override=None):
    """Generate an AI response with optional action tags.

    Parameters
    ----------
    user_message : str
        The user's message.
    context : str, optional
        Extra context appended to the system prompt (e.g. available pages).
    system_override : str, optional
        Completely replace the default system prompt.

    Returns
    -------
    dict
        ``{text, actions, error}`` where actions is a list of parsed action dicts.
    """
    try:
        client = _get_client()
    except (ImportError, ValueError) as exc:
        return {"text": "", "actions": [], "error": str(exc)}

    system = system_override or SYSTEM_PROMPT
    if context:
        system += f"\n\nAdditional context:\n{context}"

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[f"{system}\n\nUser: {user_message}"],
        )
        text = response.text or ""
        return {
            "text": text,
            "actions": parse_actions(text),
            "error": None,
        }
    except Exception as exc:
        return {"text": "", "actions": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Structured: JSON → AIResponse
# ---------------------------------------------------------------------------

def generate_structured_response(
    user_message: str,
    *,
    system_override: str | None = None,
    on_progress=None,
) -> dict:
    """Generate a structured AI response as an ``AIResponse`` model.

    Parameters
    ----------
    user_message : str
        The user's question / message.
    system_override : str, optional
        Completely replace the structured system prompt.
    on_progress : callable, optional
        ``(chunk_bytes, total_bytes)`` callback for streaming progress.
        When provided, uses ``generate_content_stream()`` instead of
        ``generate_content()``.  Callback errors are silently ignored.

    Returns
    -------
    dict
        ``{"response": AIResponse | None, "raw_json": dict | None, "error": str | None}``
    """
    try:
        client = _get_client()
        from google.genai import types
    except (ImportError, ValueError) as exc:
        return {"response": None, "raw_json": None, "error": str(exc)}

    system = system_override or STRUCTURED_SYSTEM_PROMPT
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Google Search grounding (opt-out via env var)
    search_enabled = os.getenv("GEMINI_SEARCH_GROUNDING", "true").lower() == "true"
    tools = [types.Tool(google_search=types.GoogleSearch())] if search_enabled else None

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        tools=tools,
    )
    contents = [f"{system}\n\nUser: {user_message}"]

    try:
        raw_text = ""
        grounding_result = None  # Keep reference for grounding metadata

        # Streaming path: accumulate chunks and report progress
        if on_progress is not None:
            try:
                total_bytes = 0
                for chunk in client.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=config,
                ):
                    chunk_text = chunk.text or ""
                    raw_text += chunk_text
                    chunk_bytes = len(chunk_text.encode("utf-8"))
                    total_bytes += chunk_bytes
                    try:
                        on_progress(chunk_bytes, total_bytes)
                    except Exception:
                        pass  # Never let callback errors break generation
            except Exception as stream_exc:
                # Fallback to non-streaming on stream failure
                print(f"[ai_responder] Streaming failed ({stream_exc}), falling back to non-streaming")
                raw_text = ""
                grounding_result = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                raw_text = grounding_result.text or ""
        else:
            # Non-streaming path: unchanged behavior
            grounding_result = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            raw_text = grounding_result.text or ""

        # Parse JSON
        try:
            raw_json = json.loads(raw_text)
        except json.JSONDecodeError as je:
            return {
                "response": None,
                "raw_json": None,
                "error": f"JSON parse error: {je}. Raw: {raw_text[:300]}",
            }

        # Extract grounding sources from metadata (only available in non-streaming path)
        sources = []
        if grounding_result is not None:
            try:
                candidate = grounding_result.candidates[0] if grounding_result.candidates else None
                grounding_meta = getattr(candidate, "grounding_metadata", None)
                chunks = getattr(grounding_meta, "grounding_chunks", None) or []
                for chunk in chunks:
                    web = getattr(chunk, "web", None)
                    if web and getattr(web, "uri", None):
                        sources.append({
                            "title": getattr(web, "title", None) or web.uri,
                            "url": web.uri,
                        })
            except Exception:
                pass  # grounding metadata is optional

        if sources:
            raw_json["sources"] = sources

        # Validate with Pydantic
        try:
            ai_resp = AIResponse.model_validate(raw_json)
        except Exception as ve:
            return {
                "response": None,
                "raw_json": raw_json,
                "error": f"Validation error: {ve}",
            }

        return {"response": ai_resp, "raw_json": raw_json, "error": None}

    except Exception as exc:
        return {"response": None, "raw_json": None, "error": str(exc)}
