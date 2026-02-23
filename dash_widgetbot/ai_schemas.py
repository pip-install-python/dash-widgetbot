"""Pydantic models for structured AI responses.

The AI returns high-level semantic JSON which is then converted to
Discord Components V2 dicts by ``ai_builder.build_components_v2()``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    """A markdown text block."""
    content: str = Field(..., description="Markdown-formatted text content")


class SectionBlock(BaseModel):
    """Text content with a thumbnail image beside it."""
    text: str = Field(..., description="Markdown text displayed next to the thumbnail")
    thumbnail_url: str = Field(..., description="URL of the thumbnail image")
    thumbnail_alt: str | None = Field(None, description="Alt text for the thumbnail")


class GalleryItem(BaseModel):
    """A single image in a media gallery."""
    url: str = Field(..., description="Image URL")
    alt: str | None = Field(None, description="Alt text / description")


class GalleryBlock(BaseModel):
    """A grid of 1-4 images."""
    items: list[GalleryItem] = Field(..., min_length=1, max_length=4)


class ButtonItem(BaseModel):
    """A single link button."""
    label: str = Field(..., max_length=38, description="Button label text")
    url: str = Field(..., description="URL the button links to")
    emoji: str | None = Field(None, description="Optional emoji prefix")


class ButtonRow(BaseModel):
    """A row of 1-5 link buttons."""
    buttons: list[ButtonItem] = Field(..., min_length=1, max_length=5)


class SourceLink(BaseModel):
    """A web source from Google Search grounding."""
    title: str
    url: str


class ComponentBlock(BaseModel):
    """Exactly ONE field should be set per block."""
    text: TextBlock | None = None
    section: SectionBlock | None = None
    gallery: GalleryBlock | None = None
    button_row: ButtonRow | None = None
    separator: bool | None = None


class AIResponse(BaseModel):
    """Structured AI response from Gemini.

    The AI fills in semantic fields; the builder converts them to
    Discord Components V2 component dicts.
    """
    title: str = Field(
        ...,
        max_length=60,
        description="Title with emoji prefix, e.g. '✨ Getting Started'",
    )
    color: Literal["primary", "success", "warning", "danger", "neutral"] = Field(
        "primary",
        description="Semantic color for the container accent bar",
    )
    components: list[ComponentBlock] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Content blocks (text, section, gallery, button_row, separator)",
    )
    footer: str | None = Field(
        None,
        description="Small footer text, e.g. '-# Powered by 2plot.ai'",
    )
    image_prompt: str | None = Field(
        None,
        description="Image generation prompt (only if user explicitly asks for an image)",
    )
    actions: list[dict] | None = Field(
        None,
        description="Dash app actions like [{'type': 'navigate', 'data': '/page'}]",
    )
    sources: list[SourceLink] | None = Field(
        None,
        description="Web sources from search grounding (populated server-side)",
    )
