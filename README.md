# dash-widgetbot

> **Under Development** — This plugin is actively being built. APIs may change between releases. Not recommended for production use yet.

A [Dash 3.x hooks](https://dash.plotly.com/hooks) plugin that embeds [WidgetBot](https://widgetbot.io) Discord chat into Plotly Dash applications — no webpack, no React build step, no npm.

Two components are provided:

- **DiscordCrate** — floating Discord chat button with full API control (toggle, notify, navigate, style)
- **DiscordWidget** — inline embedded Discord channel rendered as a plain `<iframe>`

---

## Installation

```bash
pip install dash-widgetbot
```

**Optional extras** (only needed for bot/AI features):

```bash
pip install dash-widgetbot[bot]   # requests + PyNaCl (slash commands + webhooks)
pip install dash-widgetbot[ai]    # google-generativeai (Gemini AI responder)
pip install dash-widgetbot[all]   # everything
```

---

## Quick Start

### DiscordCrate (floating button)

```python
import dash
from dash import html
import dash_widgetbot as dwb

# 1. Register BEFORE creating the Dash app
store_ids = dwb.add_discord_crate(
    server="299881420891881473",
    channel="355719584830980096",
)

app = dash.Dash(__name__)
app.layout = html.Div([...])

if __name__ == "__main__":
    app.run(debug=True)
```

```python
# In any callback — send commands to the Crate
from dash import Input, Output, callback
import dash_widgetbot as dwb

@callback(
    Output(dwb.STORE_IDS["command"], "data"),
    Input("open-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_crate(n):
    return dwb.crate_toggle(True)
```

### DiscordWidget (inline embed)

```python
import dash
from dash import html
import dash_widgetbot as dwb

# 1. Register BEFORE creating the Dash app
widget_ids = dwb.add_discord_widget(
    server="299881420891881473",
    channel="355719584830980096",
)

app = dash.Dash(__name__)

# 2. Place the container in your layout
app.layout = html.Div([
    dwb.discord_widget_container(
        server="299881420891881473",
        channel="355719584830980096",
        width="100%",
        height="600px",
    )
])
```

---

## DiscordCrate

### `add_discord_crate()`

Call once **before** `dash.Dash()`. Registers CDN script, layout stores, and clientside callbacks via Dash hooks.

```python
store_ids = dwb.add_discord_crate(
    server,                        # Required — Discord server ID
    channel="",                    # Default channel ID
    color="#5865f2",               # Button background color
    location=["bottom", "right"],  # ["top"|"bottom", "left"|"right"]
    glyph=("", ""),                # Custom icon (open_url, closed_url)
    css="",                        # Extra CSS injected into embed
    notifications=True,            # Enable message notifications
    dm_notifications=True,         # Enable DM notifications
    indicator=True,                # Show unread indicator dot
    timeout=10000,                 # Notification display duration (ms)
    defer=False,                   # Delay Crate init until first interaction
    prefix="",                     # Namespace for multiple Crate instances
    pages=None,                    # List of paths where Crate is visible
)
```

**Returns** a `dict` of store IDs: `config`, `command`, `event`, `message`, `user`, `status`.

### Command helpers

All helpers return a dict intended to be stored in the `command` store:

```python
# Open / close the popup
dwb.crate_toggle(True)          # open
dwb.crate_toggle(False)         # close
dwb.crate_toggle()              # toggle current state

# Show a notification bubble
dwb.crate_notify("Hello!", timeout=5000, avatar="https://...")

# Navigate to a different channel
dwb.crate_navigate("355719584830980096")

# Hide / show the entire Crate button
dwb.crate_hide()
dwb.crate_show()

# Update appearance at runtime
dwb.crate_update_options(color="#ed4245", location=["top", "left"])
dwb.crate_set_color("--color-accent", "#ed4245")

# Send a message on behalf of the signed-in user
dwb.crate_send_message("Hello from Dash!")

# Raw embed-api command
dwb.crate_emit("navigate", {"guild": "...", "channel": "..."})
```

### Reading events

```python
from dash import Input, callback

@callback(
    Output("last-message", "children"),
    Input(dwb.STORE_IDS["message"], "data"),
)
def on_message(data):
    if not data:
        return "No messages yet"
    return f"{data['author']['username']}: {data['content']}"
```

Available stores:

| Store key | Fires when | Payload keys |
|-----------|-----------|--------------|
| `event`   | signIn, signOut, sentMessage, toggle, ready, … | `type`, `_ts`, event-specific fields |
| `message` | A message is received in the channel | `content`, `author`, `channel`, `channel_id` |
| `user`    | User signs in or out | `username`, `id`, `avatar`, `signed_in` |
| `status`  | Crate opens/closes | `initialized`, `open` |

### Multiple Crate instances

```python
# Register with a unique prefix
support_ids = dwb.add_discord_crate(
    server="...", channel="...",
    color="#ed4245", location=["top", "right"],
    prefix="support",
)

# Use prefix-specific store IDs
support_store_ids = dwb.get_crate_store_ids("support")

# Command helpers accept prefix too
dwb.crate_toggle(True, prefix="support")
```

---

## DiscordWidget

### `add_discord_widget()`

Call once **before** `dash.Dash()`. Registers layout stores and a `window.postMessage` listener via Dash hooks. No CDN script is loaded.

```python
widget_ids = dwb.add_discord_widget(
    server,                            # Required — Discord server ID
    channel="",                        # Default channel ID
    width="100%",
    height="600px",
    container_id="widgetbot-container",  # Must match discord_widget_container()
)
```

### `discord_widget_container()`

Place in your layout wherever the inline widget should appear:

```python
dwb.discord_widget_container(
    server="299881420891881473",
    channel="355719584830980096",
    width="100%",
    height="600px",
    container_id="widgetbot-container",  # Must match add_discord_widget()
)
```

### Widget events

```python
widget_ids = dwb.get_widget_store_ids("widgetbot-container")

@callback(
    Output("widget-events", "children"),
    Input(widget_ids["event"], "data"),
)
def on_widget_event(data):
    if not data:
        return "No events yet"
    return f"Event: {data['type']}"
```

---

## Optional Features

### Slash Commands (Discord Interactions Endpoint)

Requires: `requests`, `PyNaCl`, a public HTTPS URL, and a registered Discord application.

```python
import dash_widgetbot as dwb

dwb.add_discord_interactions(
    public_key="your_discord_public_key_hex",
    application_id="your_app_id",
)

@dwb.register_command("ask")
def handle_ask(interaction):
    question = interaction["data"]["options"][0]["value"]
    response = dwb.generate_response(question)
    return response["text"]
```

Configure in Discord Developer Portal: `Interactions Endpoint URL → https://yourdomain.com/api/discord/interactions`

### Outbound Webhooks

```python
dwb.send_webhook_message(
    content="Deployed successfully!",
    webhook_url="https://discord.com/api/webhooks/...",
    username="Dash Bot",
)
```

### Gemini AI Responder

Requires: `google-generativeai` and `GEMINI_API_KEY` env var.

```python
result = dwb.generate_response(
    user_message="What pages does this app have?",
    context="This is a Dash analytics dashboard.",
)
# result["text"] may contain [ACTION:navigate:/some-page] tags
actions = result["actions"]   # parsed list of {type, data} dicts
```

### Action Tag Parser

Embed action tags in any text (e.g., AI responses, slash command replies):

```python
text = "Go here [ACTION:navigate:/reports] or [ACTION:notify:Done!]"

actions = dwb.parse_actions(text)
# [{"type": "navigate", "data": "/reports"}, {"type": "notify", "data": "Done!"}]

clean = dwb.strip_actions(text)
# "Go here  or "
```

Valid actions: `navigate`, `notify`, `toggle`, `hide`, `show`, `open_url`

---

## Environment Variables

```dotenv
WIDGETBOT_SERVER=your_server_id
WIDGETBOT_CHANNEL=your_channel_id

# Optional — bot/AI features
DISCORD_APPLICATION_ID=
DISCORD_PUBLIC_KEY=
DISCORD_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
GEMINI_API_KEY=
```

Use `python-dotenv` to load them:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Architecture

```
Python callback  →  dcc.Store (command)  →  clientside_callback  →  Crate API
Crate events     →  set_props()          →  dcc.Store (events)   →  Python callback
Widget iframe    →  window.postMessage   →  set_props()          →  dcc.Store (events)
```

Key design decisions:

- **No build toolchain** — pure Python + inline JS via Dash hooks
- **Store bridge** — `dcc.Store` components carry commands and events between Python and JS
- **`set_props()`** — async event push from JS to Dash stores without callback returns
- **CDN-only** — WidgetBot JS loaded from jsDelivr; widget uses a plain cross-origin `<iframe>`
- **Namespaced IDs** — all store IDs prefixed with `_widgetbot-` to avoid collisions

---

## Example App

Clone the repo and run the included example to see all features live:

```bash
git clone https://github.com/pip-install-python/dash-widgetbot
cd dash-widgetbot
pip install -e ".[all]"
cp .env.example .env          # add your server/channel IDs
python app.py
```

Open `http://127.0.0.1:8150` — ten demo pages cover every feature.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.11 |
| Dash | ≥ 3.0.3 |
| WidgetBot account | Free tier available at [widgetbot.io](https://widgetbot.io) |

---

## License

MIT — see [LICENSE](LICENSE) for details.

**Pip Install Python LLC** — [pip-install-python.com](https://pip-install-python.com)
