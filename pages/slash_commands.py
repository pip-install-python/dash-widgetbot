"""Slash Commands page -- setup guide + interactive /ask testing."""

import json
import os
import time

import dash
from dash import html, callback, Input, Output, State, dcc, no_update
import dash_mantine_components as dmc

from dash_widgetbot.ai_builder import build_components_v2, DC_BG
from dash_widgetbot.ai_responder import generate_structured_response
from dash_widgetbot.interactions import sync_discord_endpoint, _detect_ngrok_url
from dash_widgetbot.preview import render_discord_preview

dash.register_page(
    __name__, path="/slash-commands", title="Slash Commands", name="Slash Commands"
)

APP_ID = os.getenv("DISCORD_APPLICATION_ID", "")
PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY", "")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")


def _masked(val, show=6):
    if not val:
        return "(not set)"
    if len(val) <= show:
        return val
    return val[:show] + "..." + val[-4:]


REGISTER_CURL = f"""\
curl -X PUT \\
  https://discord.com/api/v10/applications/{APP_ID or '<APP_ID>'}/commands \\
  -H "Authorization: Bot {BOT_TOKEN[:10] + '...' if BOT_TOKEN else '<BOT_TOKEN>'}" \\
  -H "Content-Type: application/json" \\
  -d '[
    {{
      "name": "ask",
      "description": "Ask the AI assistant a question",
      "type": 1,
      "options": [{{
        "name": "question",
        "description": "Your question",
        "type": 3,
        "required": true
      }}]
    }},
    {{
      "name": "navigate",
      "description": "Navigate to a page in the Dash app",
      "type": 1,
      "options": [{{
        "name": "path",
        "description": "Page path (e.g. /crate-commands)",
        "type": 3,
        "required": true
      }}]
    }},
    {{
      "name": "status",
      "description": "Show app status info",
      "type": 1
    }},
    {{
      "name": "gen",
      "description": "Generate a rich Dash UI component from a prompt",
      "type": 1,
      "options": [{{
        "name": "prompt",
        "description": "What to generate (article, code, table, image, or tip)",
        "type": 3,
        "required": true
      }}]
    }}
  ]'
"""

STEPS = [
    {
        "title": "Create Discord Application",
        "desc": (
            "Go to the Discord Developer Portal and create a new application. "
            "Copy the Application ID and Public Key."
        ),
    },
    {
        "title": "Set Environment Variables",
        "desc": (
            "Add DISCORD_APPLICATION_ID, DISCORD_PUBLIC_KEY, and DISCORD_BOT_TOKEN "
            "to your .env file."
        ),
    },
    {
        "title": "Configure Interactions Endpoint",
        "desc": (
            "In your Discord app settings, set the Interactions Endpoint URL to "
            "your app's public URL + /api/discord/interactions. "
            "Discord will send a PING to verify the endpoint."
        ),
    },
    {
        "title": "Register Slash Commands",
        "desc": (
            "Use the curl command below (or the Discord API) to register "
            "the /ask, /navigate, and /status slash commands."
        ),
    },
]

layout = dmc.Container(
    [
        dcc.Store(id="sc-test-payload", data=None),

        dmc.Space(h="xl"),
        dmc.Title("Slash Commands", order=2, mb="md"),
        dmc.Text(
            "Set up Discord slash commands that interact with your Dash app. "
            "Commands are processed via HTTP interactions (no WebSocket gateway needed).",
            c="dimmed",
            mb="xl",
        ),
        # Setup guide
        dmc.Paper(
            [
                dmc.Title("Setup Guide", order=4, mb="md"),
                dmc.Stepper(
                    [
                        dmc.StepperStep(
                            label=step["title"],
                            description=step["desc"],
                        )
                        for step in STEPS
                    ],
                    active=0
                    if not APP_ID
                    else 1
                    if not PUBLIC_KEY
                    else 2
                    if not BOT_TOKEN
                    else 4,
                    orientation="vertical",
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Endpoint info
        dmc.Paper(
            [
                dmc.Title("Endpoint Info", order=4, mb="xs"),
                dmc.Grid(
                    [
                        dmc.GridCol(
                            [
                                dmc.Text("Discord Endpoint URL", size="sm", fw=600),
                                html.Div(id="sc-endpoint-url"),
                            ],
                            span=12,
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text("Application ID", size="sm", fw=600),
                                dmc.Code(_masked(APP_ID)),
                            ],
                            span=4,
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text("Public Key", size="sm", fw=600),
                                dmc.Code(_masked(PUBLIC_KEY)),
                            ],
                            span=4,
                        ),
                        dmc.GridCol(
                            [
                                dmc.Text("Bot Token", size="sm", fw=600),
                                dmc.Code(_masked(BOT_TOKEN)),
                            ],
                            span=4,
                        ),
                    ],
                    mb="md",
                ),
                dmc.Group([
                    dmc.Badge(
                        "Ready" if (APP_ID and PUBLIC_KEY and BOT_TOKEN) else "Not Configured",
                        color="green" if (APP_ID and PUBLIC_KEY and BOT_TOKEN) else "yellow",
                    ),
                    dmc.Button(
                        "Sync Endpoint with ngrok",
                        id="sc-sync-endpoint-btn",
                        size="xs",
                        variant="light",
                        color="violet",
                        loading=False,
                    ),
                ], gap="sm"),
                html.Div(id="sc-sync-endpoint-result", style={"marginTop": "8px"}),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),
        # Registration command
        dmc.Paper(
            [
                dmc.Title("Register Commands", order=4, mb="xs"),
                dmc.Text(
                    "Run this curl command to register the demo slash commands with Discord.",
                    size="sm",
                    c="dimmed",
                    mb="sm",
                ),
                html.Pre(REGISTER_CURL, className="code-block"),
                dmc.Space(h="sm"),
                dmc.Text("Registered commands:", size="sm", fw=600, mb="xs"),
                dmc.List(
                    [
                        dmc.ListItem(
                            [
                                dmc.Code("/ask <question>"),
                                dmc.Text(
                                    " -- Sends the question to Gemini AI and returns the response",
                                    size="sm",
                                    span=True,
                                ),
                            ]
                        ),
                        dmc.ListItem(
                            [
                                dmc.Code("/navigate <path>"),
                                dmc.Text(
                                    " -- Returns an [ACTION:navigate:path] for the bridge",
                                    size="sm",
                                    span=True,
                                ),
                            ]
                        ),
                        dmc.ListItem(
                            [
                                dmc.Code("/status"),
                                dmc.Text(
                                    " -- Returns app info (version, registered pages)",
                                    size="sm",
                                    span=True,
                                ),
                            ]
                        ),
                        dmc.ListItem(
                            [
                                dmc.Code("/gen <prompt>"),
                                dmc.Text(
                                    " -- Generates a rich Dash component (article, code, table, image, or callout)",
                                    size="sm",
                                    span=True,
                                ),
                            ]
                        ),
                    ],
                    size="sm",
                ),
            ],
            p="lg",
            withBorder=True,
            mb="md",
        ),

        # ── Test /ask Locally ─────────────────────────────────────────
        dmc.Paper(
            [
                dmc.Title("Test /ask Locally", order=4, mb="xs"),
                dmc.Text(
                    "Run the full AI pipeline locally: generate a structured response, "
                    "preview the Components V2 output, and optionally send it to Discord.",
                    size="sm",
                    c="dimmed",
                    mb="md",
                ),
                # Input row
                dmc.Group(
                    [
                        dmc.TextInput(
                            id="sc-test-input",
                            placeholder="Type a question (e.g. What is Python?)",
                            style={"flex": 1},
                        ),
                        dmc.Button(
                            "Run /ask",
                            id="sc-test-btn",
                            color="indigo",
                            loading=False,
                        ),
                    ],
                    mb="md",
                ),
                # Timing badge
                html.Div(id="sc-test-timing", style={"marginBottom": "12px"}),

                dmc.Grid(
                    [
                        # Discord preview
                        dmc.GridCol(
                            [
                                dmc.Text("Discord Preview", fw=600, size="sm", mb="xs"),
                                dmc.Paper(
                                    dcc.Loading(
                                        html.Div(
                                            id="sc-discord-preview",
                                            children=dmc.Text(
                                                "Run /ask to see a preview",
                                                c="#72767D", size="sm", ta="center", py="xl",
                                            ),
                                        ),
                                        custom_spinner=dmc.Skeleton(visible=True, h="200px"),
                                        target_components={"sc-discord-preview": "children"},
                                    ),
                                    p="md",
                                    style={
                                        "background": DC_BG,
                                        "minHeight": "200px",
                                        "borderRadius": "8px",
                                    },
                                ),
                            ],
                            span=6,
                        ),
                        # JSON payload viewer
                        dmc.GridCol(
                            [
                                dmc.Group(
                                    [
                                        dmc.Text("JSON Payload", fw=600, size="sm"),
                                        dmc.Button(
                                            "Send to Discord",
                                            id="sc-send-discord-btn",
                                            size="xs",
                                            variant="light",
                                            color="indigo",
                                            loading=False,
                                        ),
                                    ],
                                    justify="space-between",
                                    mb="xs",
                                ),
                                html.Div(id="sc-send-discord-result"),
                                dmc.Paper(
                                    dmc.Code(
                                        id="sc-json-viewer",
                                        children="// Run /ask to see the payload",
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
                            ],
                            span=6,
                        ),
                    ],
                    gutter="xl",
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


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("sc-endpoint-url", "children"),
    Input("sc-sync-endpoint-result", "children"),  # refresh after sync
    prevent_initial_call=False,
)
def show_endpoint_url(_sync_result):
    """Fetch and display the current Discord Interactions Endpoint URL."""
    import requests as _req
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        return dmc.Code("(DISCORD_BOT_TOKEN not set)", block=True)
    try:
        resp = _req.get(
            "https://discord.com/api/v10/applications/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
        if resp.ok:
            url = resp.json().get("interactions_endpoint_url") or "(not set)"
            ngrok_url = _detect_ngrok_url()
            children = [dmc.Code(url, block=True)]
            if ngrok_url and ngrok_url not in url:
                children.append(
                    dmc.Text(
                        f"ngrok detected at {ngrok_url} but endpoint doesn't match!",
                        c="red", size="xs", mt="xs",
                    )
                )
            elif ngrok_url and ngrok_url in url:
                children.append(
                    dmc.Text("ngrok tunnel active and in sync", c="teal", size="xs", mt="xs")
                )
            return html.Div(children)
        return dmc.Code(f"API error: {resp.status_code}", block=True)
    except Exception as exc:
        return dmc.Code(f"Error: {exc}", block=True)


@callback(
    Output("sc-sync-endpoint-result", "children"),
    Input("sc-sync-endpoint-btn", "n_clicks"),
    running=[(Output("sc-sync-endpoint-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def sync_endpoint(_n):
    """Sync the Discord endpoint with the current ngrok tunnel."""
    result = sync_discord_endpoint()
    if result["success"]:
        return dmc.Badge(
            f"Synced: {result['endpoint_url']}",
            color="green", variant="light", size="sm",
        )
    return dmc.Badge(
        f"Failed: {result['error'][:80]}",
        color="red", variant="light", size="sm",
    )


@callback(
    Output("sc-discord-preview", "children"),
    Output("sc-json-viewer", "children"),
    Output("sc-test-payload", "data"),
    Output("sc-test-timing", "children"),
    Input("sc-test-btn", "n_clicks"),
    State("sc-test-input", "value"),
    running=[(Output("sc-test-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def run_ask_test(_n, question):
    if not question:
        return no_update, no_update, no_update, dmc.Badge(
            "Enter a question first", color="yellow", variant="light", size="sm",
        )

    t0 = time.time()
    result = generate_structured_response(question)
    elapsed = time.time() - t0

    ai_response = result.get("response")
    error = result.get("error")

    if error or ai_response is None:
        error_text = error or "Unknown error"
        return (
            dmc.Alert(error_text, color="red", variant="light"),
            f"// Error: {error_text}",
            None,
            dmc.Badge(
                f"Error ({elapsed:.1f}s)", color="red", variant="light", size="sm",
            ),
        )

    # Build Components V2 payload
    payload = build_components_v2(ai_response)
    json_str = json.dumps(payload, indent=2)

    # Discord preview
    preview = render_discord_preview(ai_response)

    timing = dmc.Badge(
        f"Generated in {elapsed:.1f}s", color="teal", variant="light", size="sm",
    )

    return preview, json_str, payload, timing


@callback(
    Output("sc-send-discord-result", "children"),
    Input("sc-send-discord-btn", "n_clicks"),
    State("sc-test-payload", "data"),
    running=[(Output("sc-send-discord-btn", "loading"), True, False)],
    prevent_initial_call=True,
)
def send_to_discord(_n, payload):
    if not payload or "components" not in payload:
        return dmc.Badge(
            "No payload to send", color="yellow", variant="light", size="sm",
        )

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
