"""Bot Bridge page -- bidirectional action bridge demo.

Testable immediately, no Discord setup needed.
Demonstrates: bot message -> parse [ACTION:...] -> execute in Dash.
"""

import json
import time

import dash
from dash import html, callback, Input, Output, State, dcc, no_update
import dash_mantine_components as dmc

from dash_widgetbot import STORE_IDS, crate_toggle, crate_notify, crate_hide, crate_show
from dash_widgetbot.action_parser import parse_actions, strip_actions

dash.register_page(__name__, path="/bot-bridge", title="Bot Bridge", name="Bot Bridge")

SAMPLE_TEXT = (
    "Welcome! Let me show you around. "
    "[ACTION:navigate:/crate-commands] "
    "[ACTION:notify:Hello from the bot!]"
)

layout = dmc.Container(
    [
        dcc.Store(id="bridge-action-log", data=[]),
        dcc.Location(id="bridge-location", refresh=False),
        dmc.Space(h="xl"),
        dmc.Title("Bot Bridge", order=2, mb="md"),
        dmc.Text(
            "Bidirectional bridge between Discord bot messages and Dash actions. "
            "Paste or type text with [ACTION:type:data] tags to see them parsed and executed.",
            c="dimmed",
            mb="xl",
        ),
        # Simulate panel
        dmc.Paper(
            [
                dmc.Title("Simulate Bot Message", order=4, mb="xs"),
                dmc.Text(
                    "Type a message with action tags, then click Simulate.",
                    size="sm",
                    c="dimmed",
                    mb="sm",
                ),
                dmc.Textarea(
                    id="bridge-input",
                    value=SAMPLE_TEXT,
                    minRows=3,
                    autosize=True,
                    mb="sm",
                ),
                dmc.Button("Simulate", id="bridge-send-btn", color="violet"),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Live monitor
        dmc.Paper(
            [
                dmc.Title("Live Monitor", order=4, mb="xs"),
                dmc.Text("Raw content and parsed actions from the simulated message.", size="sm", c="dimmed", mb="sm"),
                dmc.Grid(
                    [
                        dmc.GridCol(
                            [
                                dmc.Text("Clean Text", fw=600, size="sm", mb="xs"),
                                html.Pre(
                                    id="bridge-clean-text",
                                    children="(nothing yet)",
                                    className="code-block",
                                ),
                            ],
                            span=6,
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text("Parsed Actions", fw=600, size="sm", mb="xs"),
                                html.Pre(
                                    id="bridge-parsed-actions",
                                    children="(nothing yet)",
                                    className="code-block",
                                ),
                            ],
                            span=6,
                        ),
                    ]
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Action log
        dmc.Paper(
            [
                dmc.Title("Action Log", order=4, mb="xs"),
                dmc.Text("Timestamped history of executed actions.", size="sm", c="dimmed", mb="sm"),
                html.Div(
                    id="bridge-log-display",
                    className="event-log",
                    children="No actions executed yet.",
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


# -- Callbacks ----------------------------------------------------------------

@callback(
    Output("bridge-clean-text", "children"),
    Output("bridge-parsed-actions", "children"),
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Output("bridge-location", "pathname"),
    Output("bridge-action-log", "data"),
    Input("bridge-send-btn", "n_clicks"),
    State("bridge-input", "value"),
    State("bridge-action-log", "data"),
    prevent_initial_call=True,
)
def simulate_message(_n, text, log):
    if not text:
        return no_update, no_update, no_update, no_update, no_update

    clean = strip_actions(text)
    actions = parse_actions(text)
    actions_json = json.dumps(actions, indent=2)

    log = list(log or [])

    # Execute actions
    crate_cmd = no_update
    nav_path = no_update

    for action in actions:
        ts = time.strftime("%H:%M:%S")
        a_type = action["type"]
        a_data = action["data"]
        log.insert(0, f"[{ts}] {a_type} -> {a_data}")

        if a_type == "navigate":
            nav_path = a_data
        elif a_type == "notify":
            crate_cmd = crate_notify(a_data)
        elif a_type == "toggle":
            crate_cmd = crate_toggle(a_data.lower() == "true" if a_data else None)
        elif a_type == "hide":
            crate_cmd = crate_hide()
        elif a_type == "show":
            crate_cmd = crate_show()

    # Keep log trimmed
    log = log[:50]

    return clean, actions_json, crate_cmd, nav_path, log


@callback(
    Output("bridge-log-display", "children"),
    Input("bridge-action-log", "data"),
)
def update_log_display(log):
    if not log:
        return "No actions executed yet."
    return [
        html.Div(entry, className="event-log-entry")
        for entry in log
    ]
