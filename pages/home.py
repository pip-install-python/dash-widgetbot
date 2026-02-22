"""Home page -- overview and quick start."""

import dash
from dash import html
import dash_mantine_components as dmc

dash.register_page(__name__, path="/", title="dash-widgetbot", name="Home")

QUICK_START = """\
from dash_widgetbot import add_discord_crate

# Register before creating the Dash app
add_discord_crate(
    server="YOUR_SERVER_ID",
    channel="YOUR_CHANNEL_ID",
)

import dash
app = dash.Dash(__name__, use_pages=True)
app.run(debug=True)
"""

CALLBACK_EXAMPLE = """\
from dash import callback, Input, Output
from dash_widgetbot import crate_toggle, crate_notify, STORE_IDS

@callback(
    Output(STORE_IDS['command'], 'data', allow_duplicate=True),
    Input('open-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def open_chat(n):
    return crate_toggle(True)
"""

DEMOS = [
    {
        "title": "Commands",
        "href": "/crate-commands",
        "desc": "Toggle, notify, navigate, and control Crate visibility.",
    },
    {
        "title": "Events",
        "href": "/crate-events",
        "desc": "Real-time event log, message cards, and user status.",
    },
    {
        "title": "Styling",
        "href": "/crate-styling",
        "desc": "Button color, position, and embed color customisation.",
    },
    {
        "title": "Widget",
        "href": "/widget-embed",
        "desc": "Inline <widgetbot> element embedded in the page.",
    },
    {
        "title": "Multi-Instance",
        "href": "/multi-instance",
        "desc": "Two independent Crate instances with prefix namespacing.",
    },
    {
        "title": "Bot Bridge",
        "href": "/bot-bridge",
        "desc": "Bidirectional action bridge -- parse [ACTION:...] tags and execute in Dash.",
    },
    {
        "title": "Slash Commands",
        "href": "/slash-commands",
        "desc": "HTTP-only Discord slash commands with deferred responses.",
    },
    {
        "title": "AI Chat",
        "href": "/ai-chat",
        "desc": "Chat with Gemini AI -- bot responses trigger Dash actions.",
    },
    {
        "title": "Webhook Send",
        "href": "/webhook-send",
        "desc": "Send messages from Dash to Discord via webhook.",
    },
]

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("dash-widgetbot", order=1),
        dmc.Text(
            "A Dash hooks plugin for embedding Discord chat via WidgetBot. "
            "No build toolchain -- pure Python + inline JS.",
            size="lg",
            c="dimmed",
            mb="xl",
        ),
        # Quick start
        dmc.Title("Quick Start", order=3, mb="xs"),
        html.Pre(QUICK_START, className="code-block"),
        dmc.Space(h="md"),
        dmc.Title("Callback Integration", order=3, mb="xs"),
        html.Pre(CALLBACK_EXAMPLE, className="code-block"),
        dmc.Space(h="xl"),
        # Demo cards
        dmc.Title("Demos", order=3, mb="md"),
        dmc.SimpleGrid(
            [
                dmc.Anchor(
                    dmc.Card(
                        [
                            dmc.Text(demo["title"], fw=600, size="lg"),
                            dmc.Text(demo["desc"], c="dimmed", size="sm"),
                        ],
                        withBorder=True,
                        padding="lg",
                    ),
                    href=demo["href"],
                    underline="never",
                )
                for demo in DEMOS
            ],
            cols={"base": 1, "sm": 2, "md": 3},
        ),
        dmc.Space(h="xl"),
    ],
    size="lg",
    py="xl",
)
