"""dash-widgetbot example application.

Demonstrates DiscordCrate and DiscordWidget across 10 pages,
including Phase 2 Discord bot integration examples.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from dash_widgetbot import add_discord_crate, add_discord_widget, add_discord_interactions, register_command

# Register the global Crate BEFORE creating the Dash app
SERVER = os.getenv("WIDGETBOT_SERVER", "299881420891881473")
CHANNEL = os.getenv("WIDGETBOT_CHANNEL", "355719584830980096")
COLOR = os.getenv("WIDGETBOT_COLOR", "#5865f2")

add_discord_crate(
    server=SERVER,
    channel=CHANNEL,
    color=COLOR,
    defer=True,
)

# Multi-instance demo: register additional Crate instances BEFORE Dash()
CHANNEL_2 = os.getenv("WIDGETBOT_CHANNEL_2", "355719584830980096")

SUPPORT_IDS = add_discord_crate(
    server=SERVER,
    channel=CHANNEL,
    prefix="support",
    color="#e74c3c",
    location=["top", "right"],
    defer=False,
    pages=["/multi-instance"],
)

COMMUNITY_IDS = add_discord_crate(
    server=SERVER,
    channel=CHANNEL_2,
    prefix="community",
    color="#2ecc71",
    location=["top", "left"],
    defer=False,
    pages=["/multi-instance"],
)

# Widget embed -- must be registered before Dash() like the Crates above
WIDGET_IDS = add_discord_widget(
    server=SERVER,
    channel=CHANNEL,
    width="100%",
    height="500px",
    container_id="wgt-embed-container",
)

# Register Discord interactions endpoint (only if configured)
if os.getenv("DISCORD_PUBLIC_KEY"):
    add_discord_interactions()

    # Demo command handlers
    def _handle_ask(interaction):
        """Handle /ask -- sends question to Gemini AI."""
        from dash_widgetbot.ai_responder import generate_response

        options = interaction.get("data", {}).get("options", [])
        question = next((o["value"] for o in options if o["name"] == "question"), "")
        if not question:
            return "Please provide a question."
        result = generate_response(question)
        if result["error"]:
            return f"Error: {result['error']}"
        return result["text"]

    def _handle_navigate(interaction):
        """Handle /navigate -- returns an action tag."""
        options = interaction.get("data", {}).get("options", [])
        path = next((o["value"] for o in options if o["name"] == "path"), "/")
        return f"Navigating to {path} [ACTION:navigate:{path}]"

    def _handle_status(interaction):
        """Handle /status -- returns app info."""
        return (
            "**dash-widgetbot** v0.1.0\n"
            f"Server: `{SERVER}`\n"
            f"Channel: `{CHANNEL}`\n"
            "Pages: Home, Commands, Events, Styling, Widget, "
            "Multi-Instance, Bot Bridge, Slash Commands, AI Chat, Webhook"
        )

    register_command("ask", _handle_ask)
    register_command("navigate", _handle_navigate)
    register_command("status", _handle_status)

# Now create the app ---------------------------------------------------------
import dash
from dash import html
import dash_mantine_components as dmc

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=dmc.styles.ALL,
)

NAV_LINKS = [
    {"label": "Home", "href": "/"},
    {"label": "Commands", "href": "/crate-commands"},
    {"label": "Events", "href": "/crate-events"},
    {"label": "Styling", "href": "/crate-styling"},
    {"label": "Widget", "href": "/widget-embed"},
    {"label": "Multi-Instance", "href": "/multi-instance"},
    {"label": "Bot Bridge", "href": "/bot-bridge"},
    {"label": "Slash Cmds", "href": "/slash-commands"},
    {"label": "AI Chat", "href": "/ai-chat"},
    {"label": "Webhook", "href": "/webhook-send"},
]

app.layout = dmc.MantineProvider(
    dmc.AppShell(
        [
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        dmc.Text("dash-widgetbot", fw=700, size="lg"),
                        dmc.Group(
                            [
                                dmc.Anchor(
                                    link["label"],
                                    href=link["href"],
                                    underline="never",
                                    c="dimmed",
                                    fw=500,
                                    size="sm",
                                )
                                for link in NAV_LINKS
                            ],
                            gap="md",
                        ),
                    ],
                    justify="space-between",
                    px="md",
                    h="100%",
                ),
            ),
            dmc.AppShellMain(
                dash.page_container,
            ),
        ],
        header={"height": 56},
        padding="md",
    ),
)

if __name__ == "__main__":
    app.run(debug=True, port=8150)
