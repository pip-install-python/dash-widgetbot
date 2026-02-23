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
            "An inline Discord embed rendered as a cross-origin iframe pointing directly to "
            "e.widgetbot.io. No floating button — the chat is always visible in the page.",
            c="dimmed",
            mb="md",
        ),

        # ── Limitations callout ──────────────────────────────────────────
        dmc.Alert(
            title="Widget limitations vs. DiscordCrate",
            color="yellow",
            variant="light",
            radius="md",
            mb="xl",
            children=dmc.Stack(
                [
                    dmc.Text(
                        "The inline widget is a passive, read-mostly embed. "
                        "Most features built around DiscordCrate do not apply here.",
                        size="sm",
                    ),
                    dmc.Table(
                        [
                            dmc.TableThead(
                                dmc.TableTr([
                                    dmc.TableTh("Feature"),
                                    dmc.TableTh("DiscordCrate"),
                                    dmc.TableTh("DiscordWidget"),
                                ])
                            ),
                            dmc.TableTbody([
                                dmc.TableTr([
                                    dmc.TableTd("Slash command bridge (/ai, /ask, /gen…)"),
                                    dmc.TableTd("✅ sentMessage → _handle_crate_slash"),
                                    dmc.TableTd("❌ not wired — widget event store is separate"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Server → client commands"),
                                    dmc.TableTd("✅ toggle, notify, navigate, hide, show…"),
                                    dmc.TableTd("❌ no command dispatch JS — command store ignored"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("emit_command() server push"),
                                    dmc.TableTd("✅ pushes via Socket.IO /widgetbot-crate"),
                                    dmc.TableTd("❌ Socket.IO path is Crate-only"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Login / logout control"),
                                    dmc.TableTd("✅ crate_login() / crate_logout()"),
                                    dmc.TableTd("❌ no programmatic auth trigger"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Notification toast (crate_notify)"),
                                    dmc.TableTd("✅"),
                                    dmc.TableTd("❌"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Channel navigation"),
                                    dmc.TableTd("✅ crate_navigate()"),
                                    dmc.TableTd("❌"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Receive message events"),
                                    dmc.TableTd("✅ via Crate JS API"),
                                    dmc.TableTd("✅ via postMessage from iframe"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("unreadCountUpdate / directMessage"),
                                    dmc.TableTd("✅"),
                                    dmc.TableTd("❌ not sent over postMessage"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("messageDelete / messageDeleteBulk"),
                                    dmc.TableTd("✅"),
                                    dmc.TableTd("❌ not sent over postMessage"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Multi-instance (prefix param)"),
                                    dmc.TableTd("✅ unlimited, ID-isolated"),
                                    dmc.TableTd("⚠️ one per page (single container_id)"),
                                ]),
                                dmc.TableTr([
                                    dmc.TableTd("Page-scoped visibility (pages param)"),
                                    dmc.TableTd("✅ SPA route filtering"),
                                    dmc.TableTd("❌ always visible when in layout"),
                                ]),
                            ]),
                        ],
                        withTableBorder=True,
                        withColumnBorders=True,
                        highlightOnHover=True,
                        fz="sm",
                        mb="xs",
                    ),
                    dmc.Text(
                        "When to use the widget: you want Discord chat permanently visible "
                        "in the page body and don't need Dash-to-Discord command control or "
                        "slash command integration. For everything else, use DiscordCrate.",
                        size="sm",
                        c="dimmed",
                        fs="italic",
                    ),
                ],
                gap="sm",
            ),
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
                dmc.Text(
                    "Events received via postMessage from the iframe: "
                    "ready, message, sentMessage, signIn, signOut, messageUpdate.",
                    size="sm",
                    c="dimmed",
                    mb="xs",
                ),
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
