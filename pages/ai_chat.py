"""AI Chat page -- Gemini AI demo with action detection.

Testable immediately with GEMINI_API_KEY.
"""

import json
import time

import dash
from dash import html, callback, Input, Output, State, dcc, no_update, ctx
import dash_mantine_components as dmc

from dash_widgetbot import STORE_IDS, crate_toggle, crate_notify, crate_hide, crate_show
from dash_widgetbot.action_parser import parse_actions, strip_actions
from dash_widgetbot.ai_responder import generate_response, SYSTEM_PROMPT

dash.register_page(__name__, path="/ai-chat", title="AI Chat", name="AI Chat")

AVAILABLE_PAGES = [
    "/", "/crate-commands", "/crate-events", "/crate-styling",
    "/widget-embed", "/multi-instance", "/bot-bridge",
    "/slash-commands", "/ai-chat", "/webhook-send",
]

PAGE_CONTEXT = "Available pages in this Dash app:\n" + "\n".join(
    f"- {p}" for p in AVAILABLE_PAGES
)

layout = dmc.Container(
    [
        dcc.Store(id="ai-chat-history", data=[]),
        dcc.Location(id="ai-location", refresh=False),
        dmc.Space(h="xl"),
        dmc.Title("AI Chat", order=2, mb="md"),
        dmc.Text(
            "Chat with Gemini AI. The bot can embed [ACTION:...] tags in responses "
            "to trigger Dash actions. Requires GEMINI_API_KEY in .env.",
            c="dimmed",
            mb="xl",
        ),
        # Chat messages
        dmc.Paper(
            html.Div(
                id="ai-messages",
                children=[
                    dmc.Text(
                        "Send a message to start chatting. Try: "
                        '"Show me the events page" or "Navigate to commands"',
                        c="dimmed",
                        size="sm",
                    )
                ],
                style={"maxHeight": "400px", "overflowY": "auto"},
            ),
            p="lg",
            withBorder=True,
            mb="md",
            style={"minHeight": "200px"},
        ),
        # Input
        dmc.Group(
            [
                dmc.TextInput(
                    id="ai-input",
                    placeholder="Type a message...",
                    style={"flex": 1},
                ),
                dmc.Button("Send", id="ai-send-btn"),
            ],
            mb="md",
        ),
        # Action badges (from last response)
        html.Div(id="ai-action-badges", children=[]),
        dmc.Space(h="md"),
        # System prompt editor
        dmc.Accordion(
            [
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl("System Prompt"),
                        dmc.AccordionPanel(
                            dmc.Textarea(
                                id="ai-system-prompt",
                                value=SYSTEM_PROMPT,
                                minRows=8,
                                autosize=True,
                            )
                        ),
                    ],
                    value="system-prompt",
                ),
            ],
            mb="md",
        ),
        dmc.Space(h="xl"),
    ],
    size="lg",
    py="xl",
)


def _make_message_card(role, text, actions=None):
    """Build a message card component."""
    is_user = role == "user"
    color = "blue" if is_user else "violet"
    label = "You" if is_user else "Gemini"
    clean = strip_actions(text) if not is_user else text

    children = [
        dmc.Group(
            [
                dmc.Badge(label, color=color, variant="light", size="sm"),
                dmc.Text(time.strftime("%H:%M:%S"), size="xs", c="dimmed"),
            ],
            justify="space-between",
            mb="xs",
        ),
        dmc.Text(clean, size="sm", style={"whiteSpace": "pre-wrap"}),
    ]

    if actions:
        children.append(
            dmc.Group(
                [
                    dmc.Badge(
                        f"{a['type']}: {a['data'][:30]}",
                        color="teal",
                        variant="outline",
                        size="sm",
                    )
                    for a in actions
                ],
                gap="xs",
                mt="xs",
            )
        )

    return dmc.Paper(children, p="sm", withBorder=True, mb="xs")


@callback(
    Output("ai-messages", "children"),
    Output("ai-chat-history", "data"),
    Output("ai-action-badges", "children"),
    Input("ai-send-btn", "n_clicks"),
    State("ai-input", "value"),
    State("ai-chat-history", "data"),
    State("ai-system-prompt", "value"),
    prevent_initial_call=True,
)
def send_ai_message(_n, user_text, history, system_prompt):
    if not user_text:
        return no_update, no_update, no_update

    history = list(history or [])

    # Add user message
    history.append({"role": "user", "text": user_text, "actions": []})

    # Generate AI response
    result = generate_response(
        user_text,
        context=PAGE_CONTEXT,
        system_override=system_prompt or None,
    )

    if result["error"]:
        bot_text = f"Error: {result['error']}"
        actions = []
    else:
        bot_text = result["text"]
        actions = result["actions"]

    history.append({"role": "bot", "text": bot_text, "actions": actions})

    # Build message cards
    cards = [
        _make_message_card(msg["role"], msg["text"], msg.get("actions"))
        for msg in history
    ]

    # Build clickable action badges
    action_badges = []
    if actions:
        action_badges = [
            dmc.Text("Actions from last response:", size="sm", fw=600, mb="xs"),
            dmc.Group(
                [
                    dmc.Button(
                        f"{a['type']}: {a['data'][:30]}",
                        id={"type": "ai-action-btn", "index": i},
                        color="teal",
                        variant="outline",
                        size="xs",
                    )
                    for i, a in enumerate(actions)
                ],
                gap="xs",
            ),
        ]

    return cards, history, action_badges


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

    # Find which button was clicked
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
    a_type = action["type"]
    a_data = action["data"]

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
