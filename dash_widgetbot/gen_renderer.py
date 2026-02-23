"""Render GenEntry objects as Dash Mantine Components cards.

Each format type (article, code, data_table, image, callout) maps to
a specific DMC component, wrapped in a consistent Paper card.
"""

from __future__ import annotations

import base64
from datetime import datetime

import dash_mantine_components as dmc
from dash import dcc, html

from .gen_schemas import GenResponse
from .gen_store import GenEntry

# Callout variant → DMC Alert color
_CALLOUT_COLORS = {
    "info": "blue",
    "warning": "yellow",
    "tip": "teal",
    "success": "green",
    "danger": "red",
}


def _render_article(resp: GenResponse) -> list:
    """Render article format as markdown."""
    content = resp.article
    if not content:
        return [dmc.Text("No article content", c="dimmed")]
    children = []
    if content.summary:
        children.append(dmc.Text(content.summary, size="sm", c="dimmed", fs="italic"))
    children.append(
        dcc.Markdown(
            content.body,
            dangerously_allow_html=False,
            style={"lineHeight": 1.7},
        )
    )
    return children


def _render_code(resp: GenResponse) -> list:
    """Render code format with syntax highlighting."""
    content = resp.code
    if not content:
        return [dmc.Text("No code content", c="dimmed")]
    children = []
    header_items = [dmc.Badge(content.language, variant="light", size="sm")]
    if content.filename:
        header_items.append(dmc.Code(content.filename))
    children.append(dmc.Group(header_items, gap="xs"))
    children.append(
        dmc.CodeHighlight(
            code=content.code,
            language=content.language,
        )
    )
    if content.explanation:
        children.append(dmc.Text(content.explanation, size="sm", c="dimmed"))
    return children


def _render_data_table(resp: GenResponse) -> list:
    """Render data_table format as a DMC Table."""
    content = resp.data_table
    if not content:
        return [dmc.Text("No table content", c="dimmed")]
    children = []
    head = dmc.TableThead(
        dmc.TableTr([dmc.TableTh(col) for col in content.columns])
    )
    rows = [
        dmc.TableTr([dmc.TableTd(cell) for cell in row])
        for row in content.rows
    ]
    body = dmc.TableTbody(rows)
    children.append(
        dmc.Table(
            [head, body],
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
            withColumnBorders=True,
        )
    )
    if content.caption:
        children.append(dmc.Text(content.caption, size="xs", c="dimmed", ta="center"))
    return children


def _render_image(entry: GenEntry, resp: GenResponse) -> list:
    """Render image format with base64 data URI or placeholder."""
    content = resp.image
    if not content:
        return [dmc.Text("No image content", c="dimmed")]
    children = []
    if entry.image_bytes:
        mime = entry.image_mime or "image/png"
        b64 = base64.b64encode(entry.image_bytes).decode()
        src = f"data:{mime};base64,{b64}"
        children.append(
            dmc.Image(
                src=src,
                radius="md",
                fit="contain",
                style={"maxHeight": "400px"},
            )
        )
    else:
        children.append(
            dmc.Paper(
                dmc.Text(
                    "Image generation pending or failed",
                    c="dimmed", ta="center", py="xl",
                ),
                withBorder=True,
                radius="md",
                p="xl",
                style={"minHeight": "200px", "display": "flex", "alignItems": "center", "justifyContent": "center"},
            )
        )
    if content.caption:
        children.append(dmc.Text(content.caption, size="sm", c="dimmed", ta="center"))
    return children


def _render_callout(resp: GenResponse) -> list:
    """Render callout format as a DMC Alert."""
    content = resp.callout
    if not content:
        return [dmc.Text("No callout content", c="dimmed")]
    color = _CALLOUT_COLORS.get(content.variant, "blue")
    return [
        dmc.Alert(
            content.body,
            title=content.title,
            color=color,
            variant="light",
            radius="md",
        )
    ]


def render_gen_card(entry: GenEntry) -> dmc.Paper:
    """Render a GenEntry as a styled DMC Paper card.

    Parameters
    ----------
    entry : GenEntry
        The gen store entry to render.

    Returns
    -------
    dmc.Paper
        A complete card component ready to insert into the page.
    """
    resp = entry.response

    # Error card
    if entry.error or resp is None:
        return dmc.Paper(
            dmc.Stack(
                [
                    dmc.Group(
                        [
                            dmc.Badge("error", color="red", variant="light", size="sm"),
                            dmc.Text(
                                datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S"),
                                size="xs", c="dimmed",
                            ),
                            dmc.Badge(entry.discord_user or "local", variant="dot", size="sm"),
                        ],
                        gap="xs",
                    ),
                    dmc.Text(entry.prompt, size="sm", c="dimmed", fs="italic"),
                    dmc.Divider(),
                    dmc.Alert(
                        entry.error or "Unknown error",
                        title="Generation Failed",
                        color="red",
                        variant="light",
                    ),
                ],
                gap="sm",
            ),
            p="lg",
            withBorder=True,
            radius="md",
            mb="md",
            style={"borderLeft": "4px solid #ED4245"},
        )

    # Format badge colors
    format_colors = {
        "article": "blue",
        "code": "dark",
        "data_table": "violet",
        "image": "pink",
        "callout": "teal",
    }

    accent_color = resp.color or "#5865F2"

    # Format-specific content
    if resp.format == "article":
        content_children = _render_article(resp)
    elif resp.format == "code":
        content_children = _render_code(resp)
    elif resp.format == "data_table":
        content_children = _render_data_table(resp)
    elif resp.format == "image":
        content_children = _render_image(entry, resp)
    elif resp.format == "callout":
        content_children = _render_callout(resp)
    else:
        content_children = [dmc.Text(f"Unknown format: {resp.format}", c="dimmed")]

    # Build card
    card_children = [
        dmc.Group(
            [
                dmc.Badge(
                    resp.format.replace("_", " "),
                    color=format_colors.get(resp.format, "gray"),
                    variant="light",
                    size="sm",
                ),
                dmc.Text(
                    datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S"),
                    size="xs",
                    c="dimmed",
                ),
                dmc.Badge(entry.discord_user or "local", variant="dot", size="sm"),
            ],
            gap="xs",
        ),
        dmc.Text(resp.title, fw=700, size="lg"),
        dmc.Text(entry.prompt, size="sm", c="dimmed", fs="italic"),
        dmc.Divider(),
        *content_children,
    ]

    if resp.footer:
        card_children.append(dmc.Text(resp.footer, size="xs", c="dimmed"))

    return dmc.Paper(
        dmc.Stack(card_children, gap="sm"),
        p="lg",
        withBorder=True,
        radius="md",
        mb="md",
        style={"borderLeft": f"4px solid {accent_color}"},
    )
