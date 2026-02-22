"""Slash Commands page -- interactions endpoint setup guide."""

import os

import dash
from dash import html
import dash_mantine_components as dmc

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
                                dmc.Text("Interactions URL", size="sm", fw=600),
                                dmc.Code(
                                    "https://<your-domain>/api/discord/interactions",
                                    block=True,
                                ),
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
                dmc.Badge(
                    "Ready" if (APP_ID and PUBLIC_KEY and BOT_TOKEN) else "Not Configured",
                    color="green" if (APP_ID and PUBLIC_KEY and BOT_TOKEN) else "yellow",
                ),
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
                    ],
                    size="sm",
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
