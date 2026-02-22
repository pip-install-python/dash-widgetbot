"""Crate Commands page -- toggle, notify, navigate, hide/show."""

import os

import dash
from dash import html, callback, Input, Output, State
import dash_mantine_components as dmc

from dash_widgetbot import (
    STORE_IDS,
    crate_toggle,
    crate_notify,
    crate_navigate,
    crate_hide,
    crate_show,
)

dash.register_page(__name__, path="/crate-commands", title="Commands", name="Commands")

CHANNEL_2 = os.getenv("WIDGETBOT_CHANNEL_2", "")

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("Crate Commands", order=2, mb="md"),
        dmc.Text(
            "Control the floating Crate via Python callbacks. "
            "Each button dispatches a command dict to the store bridge.",
            c="dimmed",
            mb="xl",
        ),
        # Toggle -----------------------------------------------------------
        dmc.Paper(
            [
                dmc.Title("Toggle", order=4, mb="xs"),
                dmc.Text("Open or close the Crate widget.", size="sm", c="dimmed", mb="sm"),
                dmc.Group(
                    [
                        dmc.Button("Open", id="cmd-open-btn", color="green"),
                        dmc.Button("Close", id="cmd-close-btn", variant="outline"),
                    ]
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Notify -----------------------------------------------------------
        dmc.Paper(
            [
                dmc.Title("Notifications", order=4, mb="xs"),
                dmc.Text(
                    "Display a notification bubble on the Crate button. "
                    "Optionally set a custom avatar image and timeout.",
                    size="sm", c="dimmed", mb="sm",
                ),
                dmc.TextInput(
                    id="cmd-notify-text",
                    placeholder="Type a notification message...",
                    value="Hello from Dash!",
                    label="Message",
                    mb="xs",
                ),
                dmc.TextInput(
                    id="cmd-notify-avatar",
                    placeholder="https://cdn.discordapp.com/embed/avatars/0.png",
                    value="https://cdn.discordapp.com/embed/avatars/0.png",
                    label="Avatar URL",
                    mb="xs",
                ),
                dmc.NumberInput(
                    id="cmd-notify-timeout",
                    label="Timeout (ms, 0 = sticky)",
                    value=0,
                    min=0,
                    step=1000,
                    mb="xs",
                ),
                dmc.Button("Send Notification", id="cmd-notify-btn"),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Navigate ---------------------------------------------------------
        dmc.Paper(
            [
                dmc.Title("Navigate", order=4, mb="xs"),
                dmc.Text("Switch to a different Discord channel.", size="sm", c="dimmed", mb="sm"),
                dmc.TextInput(
                    id="cmd-nav-channel",
                    placeholder="Channel ID",
                    value=CHANNEL_2,
                    mb="xs",
                ),
                dmc.Button("Navigate", id="cmd-nav-btn"),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Visibility -------------------------------------------------------
        dmc.Paper(
            [
                dmc.Title("Visibility", order=4, mb="xs"),
                dmc.Text("Hide or show the entire Crate element.", size="sm", c="dimmed", mb="sm"),
                dmc.Group(
                    [
                        dmc.Button("Hide", id="cmd-hide-btn", variant="outline", color="red"),
                        dmc.Button("Show", id="cmd-show-btn", color="green"),
                    ]
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Status display ---------------------------------------------------
        dmc.Paper(
            [
                dmc.Title("Crate Status", order=4, mb="xs"),
                html.Pre(
                    id="cmd-status-display",
                    children="Waiting for status updates...",
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


# Callbacks ----------------------------------------------------------------

@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-open-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_crate(_n):
    return crate_toggle(True)


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-close-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_crate(_n):
    return crate_toggle(False)


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-notify-btn", "n_clicks"),
    State("cmd-notify-text", "value"),
    State("cmd-notify-avatar", "value"),
    State("cmd-notify-timeout", "value"),
    prevent_initial_call=True,
)
def send_notification(_n, text, avatar, timeout):
    return crate_notify(
        text or "Hello!",
        avatar=avatar or None,
        timeout=timeout if timeout else None,
    )


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-nav-btn", "n_clicks"),
    State("cmd-nav-channel", "value"),
    prevent_initial_call=True,
)
def navigate_channel(_n, channel_id):
    if not channel_id:
        return dash.no_update
    return crate_navigate(channel_id)


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-hide-btn", "n_clicks"),
    prevent_initial_call=True,
)
def hide_crate(_n):
    return crate_hide()


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Input("cmd-show-btn", "n_clicks"),
    prevent_initial_call=True,
)
def show_crate(_n):
    return crate_show()


@callback(
    Output("cmd-status-display", "children"),
    Input(STORE_IDS["status"], "data"),
    prevent_initial_call=True,
)
def update_status_display(data):
    import json

    if not data:
        return "No status yet"
    return json.dumps(data, indent=2)
