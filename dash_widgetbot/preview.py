"""Shared Discord-dark preview renderer for AIResponse objects.

Converts an ``AIResponse`` into DMC components styled like a Discord message.
Used by both the ``/ai-chat`` and ``/slash-commands`` pages.
"""

from dash import html
import dash_mantine_components as dmc

from .ai_builder import DC_BG, DC_EMBED_BG, DC_TEXT, DC_MUTED, DC_ACCENT_MAP


def render_discord_preview(ai_response):
    """Render an AIResponse as Discord-dark-themed DMC components.

    Parameters
    ----------
    ai_response : AIResponse or None
        Structured AI response.  Returns a placeholder when ``None``.

    Returns
    -------
    dash.html.Div or dmc.Text
    """
    if ai_response is None:
        return dmc.Text(
            "Send a message to see a preview here",
            c=DC_MUTED, size="sm", ta="center", py="xl",
        )

    accent = DC_ACCENT_MAP.get(ai_response.color, DC_ACCENT_MAP["primary"])
    children = []

    # Title
    children.append(
        dmc.Text(ai_response.title, fw=700, size="lg", c=DC_TEXT, mb="xs")
    )
    children.append(dmc.Divider(color=DC_MUTED, mb="sm"))

    # Content blocks
    for block in ai_response.components:
        if block.text is not None:
            children.append(
                dmc.Text(
                    block.text.content,
                    size="sm", c=DC_TEXT, mb="xs",
                    style={"whiteSpace": "pre-wrap"},
                )
            )
        elif block.section is not None:
            children.append(
                dmc.Group([
                    dmc.Text(
                        block.section.text,
                        size="sm", c=DC_TEXT,
                        style={"flex": 1, "whiteSpace": "pre-wrap"},
                    ),
                    dmc.Image(
                        src=block.section.thumbnail_url,
                        w=60, h=60, radius="sm",
                        fallbackSrc="https://placehold.co/60x60?text=IMG",
                    ),
                ], align="flex-start", mb="xs")
            )
        elif block.gallery is not None:
            children.append(
                dmc.Group([
                    dmc.Image(
                        src=img.url, h=100, radius="sm",
                        fallbackSrc="https://placehold.co/100x100?text=IMG",
                    )
                    for img in block.gallery.items
                ], gap="xs", mb="xs")
            )
        elif block.button_row is not None:
            children.append(
                dmc.Group([
                    dmc.Anchor(
                        f"{btn.emoji + ' ' if btn.emoji else ''}{btn.label}",
                        href=btn.url, target="_blank",
                        size="xs", c="gray",
                        style={
                            "padding": "4px 8px",
                            "border": "1px solid #4a4d52",
                            "borderRadius": "4px",
                            "textDecoration": "none",
                        },
                    )
                    for btn in block.button_row.buttons
                ], gap="xs", mb="xs")
            )
        elif block.separator:
            children.append(dmc.Divider(color=DC_MUTED, my="xs"))

    # Footer
    if ai_response.footer:
        children.append(dmc.Divider(color=DC_MUTED, mt="sm", mb="xs"))
        children.append(
            dmc.Text(ai_response.footer, size="xs", c=DC_MUTED)
        )

    # Sources from Google Search grounding
    if ai_response.sources:
        children.append(dmc.Divider(color=DC_MUTED, mt="sm", mb="xs"))
        children.append(
            dmc.Text("Sources", size="xs", c=DC_MUTED, mb=4)
        )
        children.append(
            dmc.Group([
                dmc.Anchor(
                    f"🔗 {src.title[:38]}",
                    href=src.url, target="_blank",
                    size="xs", c="gray",
                    style={
                        "padding": "4px 8px",
                        "border": "1px solid #4a4d52",
                        "borderRadius": "4px",
                        "textDecoration": "none",
                    },
                )
                for src in ai_response.sources
            ], gap="xs", mb="xs")
        )

    # Image prompt indicator
    if ai_response.image_prompt:
        children.append(
            dmc.Alert(
                f"Image would be generated: {ai_response.image_prompt[:100]}",
                title="Image Generation",
                color="violet",
                variant="light",
                mt="sm",
            )
        )

    return html.Div(
        children,
        style={
            "background": DC_EMBED_BG,
            "borderLeft": f"4px solid {accent}",
            "borderRadius": "4px",
            "padding": "12px 16px",
        },
    )


def render_action_badges(ai_response):
    """Render Dash app action badges for an AIResponse.

    Parameters
    ----------
    ai_response : AIResponse or None

    Returns
    -------
    list[dmc.Badge]
    """
    if not ai_response or not ai_response.actions:
        return []
    return [
        dmc.Badge(
            f"{a.get('type', '?')}: {str(a.get('data', ''))[:30]}",
            color="teal", variant="light", size="sm",
        )
        for a in ai_response.actions
    ]
