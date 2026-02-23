"""AI Chat page -- two-panel layout with Discord-styled preview.

Left panel: chat interface with message history and settings.
Right panel: Discord-dark preview of the last Components V2 response + JSON viewer.
"""

import json
import time

import dash
from dash import html, callback, Input, Output, State, dcc, no_update, ctx
import dash_mantine_components as dmc

from dash_widgetbot import STORE_IDS, crate_toggle, crate_notify, crate_hide, crate_show
from dash_widgetbot.ai_responder import (
    generate_structured_response,
    STRUCTURED_SYSTEM_PROMPT,
)
from dash_widgetbot.ai_builder import build_components_v2, DC_BG
from dash_widgetbot.preview import render_discord_preview, render_action_badges

dash.register_page(__name__, path="/ai-chat", title="AI Chat", name="AI Chat")

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

layout = dmc.Container([
    dcc.Store(id="ai-chat-history", data=[]),
    dcc.Store(id="ai-chat-last-response", data=None),
    dcc.Store(id="ai-chat-last-payload", data=None),
    dcc.Location(id="ai-location", refresh=False),

    dmc.Space(h="xl"),
    dmc.Title("AI Chat", order=2, mb="xs"),
    dmc.Text(
        "Chat with Gemini AI. Responses are structured as Discord Components V2 messages. "
        "Requires GEMINI_API_KEY in .env.",
        c="dimmed", mb="lg", size="sm",
    ),

    dmc.Grid([
        # ── Left: Chat panel ──────────────────────────────────────────
        dmc.GridCol([
            # Messages
            dmc.Paper(
                html.Div(
                    id="ai-messages",
                    children=[
                        dmc.Text(
                            'Send a message to start chatting. Try: '
                            '"What is Python?" or "Draw me a sunset"',
                            c="dimmed", size="sm",
                        )
                    ],
                    style={"maxHeight": "400px", "overflowY": "auto"},
                ),
                p="lg", withBorder=True, mb="md",
                style={"minHeight": "200px"},
            ),

            # Input
            dmc.Group([
                dmc.TextInput(
                    id="ai-input",
                    placeholder="Type a message...",
                    style={"flex": 1},
                ),
                dmc.Button("Send", id="ai-send-btn", loading=False),
            ], mb="md"),

            # Action badges
            html.Div(id="ai-action-badges"),

            # Settings accordion
            dmc.Accordion([
                dmc.AccordionItem([
                    dmc.AccordionControl("Settings"),
                    dmc.AccordionPanel([
                        dmc.Text("System Prompt", fw=600, size="sm", mb="xs"),
                        dmc.Textarea(
                            id="ai-system-prompt",
                            value=STRUCTURED_SYSTEM_PROMPT,
                            minRows=6,
                            maxRows=12,
                            autosize=True,
                            mb="md",
                        ),
                    ]),
                ], value="settings"),
            ], mb="md"),
        ], span=6),

        # ── Right: Preview panel ──────────────────────────────────────
        dmc.GridCol([
            # Discord preview
            dmc.Text("Discord Preview", fw=600, size="sm", mb="xs"),
            dmc.Paper(
                dcc.Loading(
                    html.Div(id="ai-discord-preview"),
                    custom_spinner=dmc.Skeleton(visible=True, h="200px"),
                    target_components={"ai-discord-preview": "children"},
                ),
                p="md", mb="md",
                style={
                    "background": DC_BG,
                    "minHeight": "200px",
                    "borderRadius": "8px",
                },
            ),

            # JSON payload viewer + Send to Discord
            dmc.Group([
                dmc.Text("JSON Payload", fw=600, size="sm"),
                dmc.Button(
                    "Send to Discord",
                    id="ai-send-discord-btn",
                    size="xs",
                    variant="light",
                    color="indigo",
                    loading=False,
                ),
            ], justify="space-between", mb="xs"),
            html.Div(id="ai-send-discord-result"),
            dmc.Paper(
                dmc.Code(
                    id="ai-json-viewer",
                    children="// Send a message to see the payload",
                    block=True,
                ),
                p="md",
                style={
                    "background": "#1E1F22",
                    "maxHeight": "300px",
                    "overflowY": "auto",
                    "borderRadius": "8px",
                },
            ),
        ], span=6),
    ], gutter="xl"),

    dmc.Space(h="xl"),
], size="xl", py="xl")


# ---------------------------------------------------------------------------
# Message card builder
# ---------------------------------------------------------------------------

def _make_message_card(role, text, actions=None, is_error=False):
    """Build a chat message card."""
    is_user = role == "user"
    color = "blue" if is_user else ("red" if is_error else "violet")
    label_text = "You" if is_user else "Gemini"

    children = [
        dmc.Group([
            dmc.Badge(label_text, color=color, variant="light", size="sm"),
            dmc.Text(time.strftime("%H:%M:%S"), size="xs", c="dimmed"),
        ], justify="space-between", mb="xs"),
        dmc.Text(
            text[:500] + ("..." if len(text) > 500 else ""),
            size="sm",
            style={"whiteSpace": "pre-wrap"},
        ),
    ]

    if actions:
        children.append(
            dmc.Group([
                dmc.Badge(
                    f"{a.get('type', '?')}: {str(a.get('data', ''))[:25]}",
                    color="teal", variant="outline", size="sm",
                )
                for a in actions
            ], gap="xs", mt="xs")
        )

    return dmc.Paper(children, p="sm", withBorder=True, mb="xs")


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("ai-messages", "children"),
    Output("ai-chat-history", "data"),
    Output("ai-action-badges", "children"),
    Output("ai-discord-preview", "children"),
    Output("ai-json-viewer", "children"),
    Output("ai-chat-last-payload", "data"),
    Input("ai-send-btn", "n_clicks"),
    State("ai-input", "value"),
    State("ai-chat-history", "data"),
    State("ai-system-prompt", "value"),
    running=[(Output("ai-send-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def send_ai_message(_n, user_text, history, system_prompt):
    if not user_text:
        return no_update, no_update, no_update, no_update, no_update, no_update

    history = list(history or [])

    # Add user message
    history.append({"role": "user", "text": user_text})

    # Generate structured response
    result = generate_structured_response(
        user_text,
        system_override=system_prompt or None,
    )

    ai_response = result.get("response")
    error = result.get("error")

    if error or ai_response is None:
        error_text = error or "Unknown error"
        history.append({"role": "bot", "text": f"Error: {error_text}", "is_error": True})
        cards = [
            _make_message_card(
                msg["role"], msg["text"],
                actions=msg.get("actions"),
                is_error=msg.get("is_error", False),
            )
            for msg in history
        ]
        return cards, history, [], no_update, f"// Error: {error_text}", None

    # Store a summary for display
    summary = ai_response.title
    if ai_response.components:
        first = ai_response.components[0]
        if first.text:
            summary += f"\n{first.text.content[:200]}"

    actions = ai_response.actions or []
    history.append({
        "role": "bot",
        "text": summary,
        "actions": actions,
        "raw_json": result.get("raw_json"),
    })

    # Build message cards
    cards = [
        _make_message_card(
            msg["role"], msg["text"],
            actions=msg.get("actions"),
            is_error=msg.get("is_error", False),
        )
        for msg in history
    ]

    # Action badges
    action_badges = []
    if actions:
        action_badges = [
            dmc.Text("Actions:", size="sm", fw=600, mb="xs"),
            dmc.Group([
                dmc.Button(
                    f"{a.get('type', '?')}: {str(a.get('data', ''))[:25]}",
                    id={"type": "ai-action-btn", "index": i},
                    color="teal", variant="outline", size="xs",
                )
                for i, a in enumerate(actions)
            ], gap="xs"),
        ]

    # Discord preview
    preview = render_discord_preview(ai_response)

    # JSON payload
    payload = build_components_v2(ai_response)
    json_str = json.dumps(payload, indent=2)

    return cards, history, action_badges, preview, json_str, payload


@callback(
    Output(STORE_IDS["command"], "data", allow_duplicate=True),
    Output("ai-location", "pathname"),
    Input({"type": "ai-action-btn", "index": dash.ALL}, "n_clicks"),
    State("ai-chat-history", "data"),
    prevent_initial_call=True,
)
def execute_ai_action(n_clicks_list, history):
    if not any(n_clicks_list):
        return no_update, no_update

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update

    idx = triggered.get("index", 0)

    # Get actions from last bot message
    last_bot = None
    for msg in reversed(history or []):
        if msg["role"] == "bot" and msg.get("actions"):
            last_bot = msg
            break

    if not last_bot or idx >= len(last_bot["actions"]):
        return no_update, no_update

    action = last_bot["actions"][idx]
    a_type = action.get("type", "")
    a_data = action.get("data", "")

    crate_cmd = no_update
    nav_path = no_update

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

    return crate_cmd, nav_path


@callback(
    Output("ai-send-discord-result", "children"),
    Input("ai-send-discord-btn", "n_clicks"),
    State("ai-chat-last-payload", "data"),
    running=[(Output("ai-send-discord-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def send_to_discord(_n, payload):
    if not payload or "components" not in payload:
        return dmc.Badge("No payload to send", color="yellow", variant="light", size="sm")

    from dash_widgetbot.webhook import send_webhook_message

    result = send_webhook_message(components=payload["components"])

    if result["success"]:
        return dmc.Badge(
            f"Sent (ID: {result['message_id']})",
            color="green", variant="light", size="sm",
        )
    return dmc.Badge(
        f"Failed: {result['error'][:80]}",
        color="red", variant="light", size="sm",
    )
