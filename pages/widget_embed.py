"""Widget Embed page -- inline <widgetbot> element in the page."""

import os
import json

import dash
from dash import html, callback, Input, Output
import dash_mantine_components as dmc

from dash_widgetbot import discord_widget_container, get_widget_store_ids

SERVER = os.getenv("WIDGETBOT_SERVER", "299881420891881473")
CHANNEL = os.getenv("WIDGETBOT_CHANNEL", "355719584830980096")
CONTAINER_ID = "wgt-embed-container"

# Registration happens in app.py before Dash() -- same pattern as multi_instance.py.
# Here we just retrieve the pre-registered store IDs.
WIDGET_IDS = get_widget_store_ids(CONTAINER_ID)

dash.register_page(__name__, path="/widget-embed", title="Widget", name="Widget")

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("Inline Widget", order=2, mb="md"),
        dmc.Text(
            "An inline <widgetbot> element embedded directly in the page. "
            "No floating button -- the chat is right here.",
            c="dimmed",
            mb="xl",
        ),
        dmc.Paper(
            discord_widget_container(
                server=SERVER,
                channel=CHANNEL,
                width="100%",
                height="500px",
                container_id=CONTAINER_ID,
            ),
            p="md",
            withBorder=True,
            mb="md",
        ),
        # Event display
        dmc.Paper(
            [
                dmc.Title("Widget Events", order=4, mb="xs"),
                html.Pre(
                    id="wgt-event-display",
                    children="Waiting for widget events...",
                    className="code-block",
                ),
            ],
            p="lg",
            withBorder=True,
        ),
        dmc.Space(h="xl"),
    ],
    size="lg",
    py="xl",
)


@callback(
    Output("wgt-event-display", "children"),
    Input(WIDGET_IDS["event"], "data"),
    Input(WIDGET_IDS["message"], "data"),
    prevent_initial_call=True,
)
def show_widget_event(event, message):
    data = event or message
    if not data:
        return "No events yet"
    return json.dumps(data, indent=2)
