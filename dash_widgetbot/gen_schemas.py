"""Pydantic models for /gen command responses.

The AI selects a format (article, code, data_table, image, callout)
and fills only the matching content field. ``gen_renderer.py`` reads
the format discriminator to pick the right DMC component.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GenFormat = Literal["article", "code", "data_table", "image", "callout"]


class ArticleContent(BaseModel):
    """Rich text: explanations, tutorials, how-tos."""
    body: str = Field(..., description="Markdown-formatted body text")
    summary: str | None = Field(None, description="One-line summary")


class CodeContent(BaseModel):
    """Code block with syntax highlighting."""
    language: str = Field(..., description="Programming language (python, rust, js, etc.)")
    code: str = Field(..., description="The source code")
    explanation: str | None = Field(None, description="Brief explanation of the code")
    filename: str | None = Field(None, description="Suggested filename")


class DataTableContent(BaseModel):
    """Tabular data for comparisons."""
    columns: list[str] = Field(..., min_length=1, description="Column headers")
    rows: list[list[str]] = Field(..., min_length=1, description="Row data (list of lists)")
    caption: str | None = Field(None, description="Table caption")


class ImageContent(BaseModel):
    """Triggers server-side image generation."""
    prompt: str = Field(..., description="Detailed image generation prompt")
    caption: str | None = Field(None, description="Caption for the generated image")


class CalloutContent(BaseModel):
    """Short advisory, tip, or warning."""
    variant: Literal["info", "warning", "tip", "success", "danger"] = Field(
        "info", description="Callout style"
    )
    title: str = Field(..., description="Callout title")
    body: str = Field(..., description="Callout body text")


class GenResponse(BaseModel):
    """Structured AI response for the /gen command.

    Discriminated by ``format`` -- only the matching content field is filled.
    """
    format: GenFormat = Field(..., description="Output format type")
    title: str = Field(..., max_length=80, description="Card title")
    color: str = Field(
        "#5865F2",
        description="Accent color hex (default blurple)",
    )
    footer: str | None = Field(None, description="Small footer text")

    article: ArticleContent | None = None
    code: CodeContent | None = None
    data_table: DataTableContent | None = None
    image: ImageContent | None = None
    callout: CalloutContent | None = None
