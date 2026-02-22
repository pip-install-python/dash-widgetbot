"""Multi-Instance page -- two independent Crate instances with prefix.

The additional Crate instances (support, community) are registered in app.py
BEFORE the Dash() constructor, because hooks must be registered before the app
processes them. This page just uses the store IDs.
"""

import dash
from dash import html, callback, Input, Output, State
import dash_mantine_components as dmc

from dash_widgetbot import (
    get_crate_store_ids,
    crate_toggle,
    crate_notify,
)

# Get store IDs for the instances registered in app.py
SUPPORT_IDS = get_crate_store_ids("support")
COMMUNITY_IDS = get_crate_store_ids("community")

dash.register_page(
    __name__, path="/multi-instance", title="Multi-Instance", name="Multi-Instance"
)

layout = dmc.Container(
    [
        dmc.Space(h="xl"),
        dmc.Title("Multi-Instance Crates", order=2, mb="md"),
        dmc.Text(
            "Three independent Crate instances using prefix namespacing. "
            "Default (bottom-right), Support (top-right, red), Community (top-left, green). "
            "Each has its own stores, position, and colour.",
            c="dimmed",
            mb="xl",
        ),
        dmc.SimpleGrid(
            [
                # Community crate controls ---------------------------------
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Title("Community", order=4),
                                dmc.Badge("Top Left", color="green"),
                            ],
                            justify="space-between",
                            mb="sm",
                        ),
                        dmc.Text('prefix="community"', size="sm", c="dimmed", mb="sm"),
                        dmc.Group(
                            [
                                dmc.Button("Open", id="multi-community-open", color="green"),
                                dmc.Button("Close", id="multi-community-close", variant="outline"),
                            ],
                            mb="sm",
                        ),
                        dmc.TextInput(
                            id="multi-community-notify-text",
                            placeholder="Notification...",
                            value="Join the chat!",
                            mb="xs",
                        ),
                        dmc.Button("Notify", id="multi-community-notify", color="green", variant="light"),
                    ],
                    p="lg",
                    withBorder=True,
                ),
                # Support crate controls -----------------------------------
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Title("Support", order=4),
                                dmc.Badge("Top Right", color="red"),
                            ],
                            justify="space-between",
                            mb="sm",
                        ),
                        dmc.Text('prefix="support"', size="sm", c="dimmed", mb="sm"),
                        dmc.Group(
                            [
                                dmc.Button("Open", id="multi-support-open", color="blue"),
                                dmc.Button("Close", id="multi-support-close", variant="outline"),
                            ],
                            mb="sm",
                        ),
                        dmc.TextInput(
                            id="multi-support-notify-text",
                            placeholder="Notification...",
                            value="Need help?",
                            mb="xs",
                        ),
                        dmc.Button("Notify", id="multi-support-notify", color="blue", variant="light"),
                    ],
                    p="lg",
                    withBorder=True,
                ),
            ],
            cols={"base": 1, "md": 2},
        ),
        # Store info
        dmc.Space(h="lg"),
        dmc.Paper(
            [
                dmc.Title("Store IDs", order=4, mb="xs"),
                dmc.Text(
                    "Each instance gets 6 independent stores. "
                    "Combined with the default instance, there are 18 stores in the DOM.",
                    size="sm",
                    c="dimmed",
                    mb="sm",
                ),
                html.Pre(
                    f"Support:   {list(SUPPORT_IDS.values())}\n"
                    f"Community: {list(COMMUNITY_IDS.values())}",
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


# Support callbacks --------------------------------------------------------

@callback(
    Output(SUPPORT_IDS["command"], "data", allow_duplicate=True),
    Input("multi-support-open", "n_clicks"),
    prevent_initial_call=True,
)
def open_support(_n):
    return crate_toggle(True, prefix="support")


@callback(
    Output(SUPPORT_IDS["command"], "data", allow_duplicate=True),
    Input("multi-support-close", "n_clicks"),
    prevent_initial_call=True,
)
def close_support(_n):
    return crate_toggle(False, prefix="support")


@callback(
    Output(SUPPORT_IDS["command"], "data", allow_duplicate=True),
    Input("multi-support-notify", "n_clicks"),
    State("multi-support-notify-text", "value"),
    prevent_initial_call=True,
)
def notify_support(_n, text):
    return crate_notify(text or "Need help?", prefix="support")


# Community callbacks ------------------------------------------------------

@callback(
    Output(COMMUNITY_IDS["command"], "data", allow_duplicate=True),
    Input("multi-community-open", "n_clicks"),
    prevent_initial_call=True,
)
def open_community(_n):
    return crate_toggle(True, prefix="community")


@callback(
    Output(COMMUNITY_IDS["command"], "data", allow_duplicate=True),
    Input("multi-community-close", "n_clicks"),
    prevent_initial_call=True,
)
def close_community(_n):
    return crate_toggle(False, prefix="community")


@callback(
    Output(COMMUNITY_IDS["command"], "data", allow_duplicate=True),
    Input("multi-community-notify", "n_clicks"),
    State("multi-community-notify-text", "value"),
    prevent_initial_call=True,
)
def notify_community(_n, text):
    return crate_notify(text or "Join the chat!", prefix="community")
