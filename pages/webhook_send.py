"""Webhook Send page -- outbound Discord webhook composer."""

import json
import os
import time

import dash
from dash import html, callback, Input, Output, State, no_update
import dash_mantine_components as dmc

from dash_widgetbot.webhook import send_webhook_message

dash.register_page(__name__, path="/webhook-send", title="Webhook Send", name="Webhook")

WEBHOOK_URL_DEFAULT = os.getenv("DISCORD_WEBHOOK_URL", "")

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("Webhook Send", order=2, mb="md"),
        dmc.Text(
            "Send messages to Discord via a webhook URL. "
            "Create a webhook in your Discord server settings (Integrations > Webhooks).",
            c="dimmed",
            mb="xl",
        ),
        # Composer
        dmc.Paper(
            [
                dmc.Title("Compose Message", order=4, mb="xs"),
                dmc.TextInput(
                    id="wh-webhook-url",
                    label="Webhook URL",
                    placeholder="https://discord.com/api/webhooks/...",
                    value=WEBHOOK_URL_DEFAULT,
                    mb="sm",
                ),
                dmc.Textarea(
                    id="wh-content",
                    label="Message",
                    placeholder="Type your message...",
                    value="Hello from dash-widgetbot!",
                    minRows=3,
                    autosize=True,
                    mb="sm",
                ),
                dmc.Grid(
                    [
                        dmc.GridCol(
                            dmc.TextInput(
                                id="wh-username",
                                label="Username (optional)",
                                placeholder="Bot display name",
                            ),
                            span=4,
                        ),
                        dmc.GridCol(
                            dmc.TextInput(
                                id="wh-avatar-url",
                                label="Avatar URL (optional)",
                                placeholder="https://...",
                            ),
                            span=4,
                        ),
                        dmc.GridCol(
                            dmc.TextInput(
                                id="wh-thread-id",
                                label="Thread ID (optional)",
                                placeholder="Thread snowflake",
                            ),
                            span=4,
                        ),
                    ],
                    mb="md",
                ),
                dmc.Group(
                    [
                        dmc.Button("Send", id="wh-send-btn", color="green"),
                        html.Div(id="wh-result-badge"),
                    ]
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # History
        dmc.Paper(
            [
                dmc.Title("Send History", order=4, mb="xs"),
                html.Div(
                    id="wh-history",
                    className="event-log",
                    children="No messages sent yet.",
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
    Output("wh-result-badge", "children"),
    Output("wh-history", "children"),
    Input("wh-send-btn", "n_clicks"),
    State("wh-webhook-url", "value"),
    State("wh-content", "value"),
    State("wh-username", "value"),
    State("wh-avatar-url", "value"),
    State("wh-thread-id", "value"),
    State("wh-history", "children"),
    prevent_initial_call=True,
)
def send_message(_n, webhook_url, content, username, avatar_url, thread_id, history):
    if not content:
        return dmc.Badge("No content", color="yellow"), no_update

    result = send_webhook_message(
        content,
        webhook_url=webhook_url or None,
        username=username or None,
        avatar_url=avatar_url or None,
        thread_id=thread_id or None,
    )

    if result["success"]:
        badge = dmc.Badge(f"Sent (ID: {result['message_id']})", color="green")
    else:
        badge = dmc.Badge(f"Error: {result['error'][:60]}", color="red")

    ts = time.strftime("%H:%M:%S")
    status = "OK" if result["success"] else f"ERR {result['status_code']}"
    entry = html.Div(
        f"[{ts}] {status} -- {content[:80]}",
        className="event-log-entry",
    )

    if isinstance(history, str):
        history = []
    elif not isinstance(history, list):
        history = [history] if history else []

    return badge, [entry] + history[:49]
