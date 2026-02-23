"""Convert an AIResponse into a Discord Components V2 message dict.

Uses the existing builders from ``components.py`` — no direct type-number
manipulation outside of ``components.py``.
"""

from __future__ import annotations

from .ai_schemas import AIResponse, ComponentBlock
from .components import (
    action_row,
    button,
    container,
    media_gallery,
    section,
    separator,
    text_display,
    thumbnail,
    unfurl_media,
)
from ._constants import IS_COMPONENTS_V2

# Semantic color → integer RGB (decimal)
COLOR_MAP: dict[str, int] = {
    "primary": 0x5865F2,   # Discord Blurple
    "success": 0x57F287,   # Green
    "warning": 0xFEE75C,   # Yellow
    "danger": 0xED4245,    # Red
    "neutral": 0x99AAB5,   # Gray-blue
}

# Discord-dark theme colors for the Dash preview page
DC_BG = "#313338"
DC_EMBED_BG = "#2B2D31"
DC_TEXT = "#DCDDDE"
DC_MUTED = "#72767D"
DC_ACCENT_MAP: dict[str, str] = {
    "primary": "#5865F2",
    "success": "#57F287",
    "warning": "#FEE75C",
    "danger": "#ED4245",
    "neutral": "#99AAB5",
}


def _build_block(block: ComponentBlock) -> dict | None:
    """Map a single ComponentBlock to a Discord component dict."""
    if block.text is not None:
        return text_display(block.text.content)

    if block.section is not None:
        acc = thumbnail(
            unfurl_media(block.section.thumbnail_url),
            description=block.section.thumbnail_alt,
        )
        return section(acc, text_display(block.section.text))

    if block.gallery is not None:
        items = []
        for img in block.gallery.items:
            item = {"media": unfurl_media(img.url)}
            if img.alt:
                item["description"] = img.alt
            items.append(item)
        return media_gallery(*items)

    if block.button_row is not None:
        buttons = []
        for btn in block.button_row.buttons:
            kw: dict = {}
            if btn.emoji:
                kw["emoji"] = {"name": btn.emoji}
            buttons.append(
                button(btn.label, style="link", url=btn.url, **kw)
            )
        return action_row(*buttons)

    if block.separator:
        return separator()

    return None


def build_components_v2(
    ai_response: AIResponse,
    *,
    image_url: str | None = None,
) -> dict:
    """Convert an ``AIResponse`` into a Components V2 message payload.

    Parameters
    ----------
    ai_response : AIResponse
        Validated structured response from the AI.
    image_url : str, optional
        URL (or ``attachment://filename``) for a generated image.

    Returns
    -------
    dict
        Ready-to-send Discord message payload with ``components`` and
        ``flags`` (``IS_COMPONENTS_V2``).
    """
    accent = COLOR_MAP.get(ai_response.color, COLOR_MAP["primary"])
    children: list[dict] = []

    # Title
    children.append(text_display(f"# {ai_response.title}"))
    children.append(separator())

    # Content blocks
    for block in ai_response.components:
        comp = _build_block(block)
        if comp is not None:
            children.append(comp)

    # Generated image
    if image_url:
        children.append(
            media_gallery({"media": unfurl_media(image_url), "description": "AI-generated image"})
        )

    # Footer
    if ai_response.footer:
        children.append(separator())
        children.append(text_display(ai_response.footer))

    # Sources from Google Search grounding
    if ai_response.sources:
        children.append(separator())
        children.append(text_display("-# Sources"))
        # Discord allows max 5 buttons per action row
        for i in range(0, len(ai_response.sources), 5):
            batch = ai_response.sources[i : i + 5]
            buttons = [
                button(src.title[:38], style="link", url=src.url, emoji={"name": "🔗"})
                for src in batch
            ]
            children.append(action_row(*buttons))

    wrapped = container(*children, color=accent)
    return {"components": [wrapped], "flags": IS_COMPONENTS_V2}
