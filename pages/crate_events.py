"""Crate Events page -- real-time event log, message card, user status."""

import json

import dash
from dash import html, callback, Input, Output, State
import dash_mantine_components as dmc

from dash_widgetbot import STORE_IDS

dash.register_page(__name__, path="/crate-events", title="Events", name="Events")

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("Crate Events", order=2, mb="md"),
        dmc.Text(
            "Events fired by the WidgetBot embed are pushed into stores via "
            "set_props and consumed by Python callbacks in real time.",
            c="dimmed",
            mb="xl",
        ),
        dmc.SimpleGrid(
            [
                # Event log ------------------------------------------------
                dmc.Paper(
                    [
                        dmc.Title("Event Log", order=4, mb="xs"),
                        dmc.Text("Generic events (newest first, max 50)", size="sm", c="dimmed", mb="sm"),
                        html.Div(
                            id="evt-log",
                            className="event-log",
                            children="Waiting for events...",
                        ),
                        # Hidden store to accumulate log entries
                        html.Div(
                            dmc.JsonInput(id="evt-log-data", value="[]", style={"display": "none"}),
                            style={"display": "none"},
                        ),
                    ],
                    p="lg",
                    withBorder=True,
                ),
                # Right column
                html.Div(
                    [
                        # Last message card --------------------------------
                        dmc.Paper(
                            [
                                dmc.Title("Last Message", order=4, mb="xs"),
                                html.Div(
                                    id="evt-message-card",
                                    children=dmc.Text("No messages yet", c="dimmed", size="sm"),
                                ),
                            ],
                            p="lg",
                            withBorder=True,
                            mb="md",
                        ),
                        # User status card ---------------------------------
                        dmc.Paper(
                            [
                                dmc.Title("User Status", order=4, mb="xs"),
                                html.Div(
                                    id="evt-user-card",
                                    children=dmc.Badge("Signed Out", color="gray"),
                                ),
                            ],
                            p="lg",
                            withBorder=True,
                        ),
                    ]
                ),
            ],
            cols={"base": 1, "md": 2},
        ),
        dmc.Space(h="xl"),
    ],
    size="lg",
    py="xl",
)


# Callbacks ----------------------------------------------------------------

@callback(
    Output("evt-log", "children"),
    Output("evt-log-data", "value"),
    Input(STORE_IDS["event"], "data"),
    State("evt-log-data", "value"),
    prevent_initial_call=True,
)
def update_event_log(event, existing_json):
    if not event:
        return dash.no_update, dash.no_update

    try:
        entries = json.loads(existing_json) if existing_json else []
    except (json.JSONDecodeError, TypeError):
        entries = []

    entry = f"[{event.get('type', '?')}] {json.dumps({k: v for k, v in event.items() if k not in ('_ts',)})}"
    entries.insert(0, entry)
    entries = entries[:50]

    log_children = [
        html.Div(e, className="event-log-entry") for e in entries
    ]

    return log_children, json.dumps(entries)


@callback(
    Output("evt-message-card", "children"),
    Input(STORE_IDS["message"], "data"),
    prevent_initial_call=True,
)
def update_message_card(msg):
    if not msg:
        return dmc.Text("No messages yet", c="dimmed", size="sm")

    author = msg.get("author", {})
    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Avatar(src=author.get("avatar", ""), radius="xl", size="sm"),
                    dmc.Text(author.get("username", "Unknown"), fw=600, size="sm"),
                    dmc.Text(f"#{msg.get('channel', '')}", c="dimmed", size="xs"),
                ],
                gap="xs",
            ),
            dmc.Text(msg.get("content", ""), size="sm"),
        ],
        gap="xs",
    )


@callback(
    Output("evt-user-card", "children"),
    Input(STORE_IDS["user"], "data"),
    prevent_initial_call=True,
)
def update_user_card(user):
    if not user:
        return dmc.Badge("Signed Out", color="gray")

    if user.get("signed_in"):
        return dmc.Group(
            [
                dmc.Badge("Signed In", color="green"),
                dmc.Text(user.get("username", ""), fw=500, size="sm"),
                dmc.Text(f"({user.get('provider', '')})", c="dimmed", size="xs"),
            ],
            gap="xs",
        )

    return dmc.Badge("Signed Out", color="gray")
