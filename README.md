# dash-widgetbot

A [Dash 3.x hooks](https://dash.plotly.com/hooks) plugin that embeds [WidgetBot](https://widgetbot.io) Discord chat into Plotly Dash applications — no webpack, no React build step, no npm.

Two components are provided:

- **DiscordCrate** — floating Discord chat button with full API control (toggle, notify, navigate, style)
- **DiscordWidget** — inline embedded Discord channel rendered as a plain `<iframe>`

---

## Installation

```bash
pip install dash-widgetbot
```

**Optional extras** (install only what you need):

```bash
pip install dash-widgetbot[bot]      # requests + PyNaCl — slash commands + webhooks
pip install dash-widgetbot[ai]       # google-genai — Gemini AI responder
pip install dash-widgetbot[realtime] # flask-socketio + dash-socketio — real-time transport
pip install dash-widgetbot[all]      # everything
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

Requires `[bot]` extra, a public HTTPS URL (e.g. ngrok), and a registered Discord application.

```python
import dash_widgetbot as dwb

dwb.add_discord_interactions(
    public_key="your_discord_public_key_hex",
    application_id="your_app_id",
)

@dwb.register_command("ask")
def handle_ask(interaction):
    question = interaction["data"]["options"][0]["value"]
    return f"You asked: {question}"
```

Register the endpoint in the Discord Developer Portal:
```
Interactions Endpoint URL → https://yourdomain.com/api/discord/interactions
```

Automatically sync at startup using the ngrok auto-detect:

```python
dwb.sync_discord_endpoint()  # detects ngrok or reads INTERACTIONS_URL env var
```

### Discord Components V2

Build rich Discord messages with the full Components V2 builder library:

```python
from dash_widgetbot.components import container, text_display, button, action_row

payload = container(
    text_display("## Hello from Dash!"),
    action_row(
        button("Visit App", url="https://your-app.com"),
    ),
    color=0x5865f2,
)
```

### Structured AI Responses (Gemini)

Requires `[ai]` extra and `GEMINI_API_KEY` env var.

```python
result = dwb.generate_structured_response("What is this app?")
ai_response = result["response"]  # AIResponse Pydantic model

# Convert to Discord Components V2 payload
discord_payload = dwb.build_components_v2(ai_response)

# Or render as Dash components (Discord dark preview)
dash_preview = dwb.render_discord_preview(ai_response)
```

`AIResponse` supports: `title`, `color`, `components` (text, section, gallery, button_row, separator blocks), `footer`, `image_prompt`, `actions`, and `sources` (from Google Search grounding).

### Multi-Format AI Generation (`/gen`)

```python
result = dwb.generate_gen_response("Explain Python async/await")
gen_response = result["response"]  # GenResponse Pydantic model

# Render as a styled DMC card
from dash_widgetbot.gen_renderer import render_gen_card
card = render_gen_card(gen_entry)
```

Supported formats: `article`, `code`, `data_table`, `image`, `callout`.

### Per-User Private AI Threads

When `AI_THREAD_PARENT_CHANNEL` is set, Discord AI commands (`/ai`, `/ask`, `/gen`) automatically route responses to a private thread per user:

```dotenv
AI_THREAD_PARENT_CHANNEL=your_text_channel_id
```

Each Discord user gets their own private thread (type 12, 7-day auto-archive). Bot permissions required: `CREATE_PRIVATE_THREADS`, `SEND_MESSAGES_IN_THREADS`, `MANAGE_THREADS`.

### Real-Time Transport (`[realtime]`)

Requires `[realtime]` extra. Adds Socket.IO alongside the always-active store bridge for zero-latency server → client pushes.

```python
from flask_socketio import SocketIO
from dash_widgetbot import configure_socketio

_socketio = SocketIO(app.server, async_mode='threading', cors_allowed_origins="*")
configure_socketio(_socketio)

# Push a command to all connected clients from a background thread
from dash_widgetbot import emit_command
emit_command(dwb.crate_notify("Job finished!"))
```

### Progress Tracking

`ProgressTracker` fans out real-time progress updates to multiple sinks during long-running AI generation:

```python
from dash_widgetbot.progress import ProgressTracker, SocketIOSink, EphemeralSink

tracker = ProgressTracker(sinks=[SocketIOSink(), EphemeralSink(app_id, token)])
result = dwb.generate_gen_response(prompt, on_progress=tracker.stream_callback())
tracker.close()
```

Progress phases: `analyzing` → `generating` (10–80%) → `parsing` → `creating_image` → `posting` → `complete`.

### Outbound Webhooks

```python
dwb.send_webhook_message(
    content="Deployed successfully!",
    webhook_url="https://discord.com/api/webhooks/...",
    username="Dash Bot",
)
```

### Action Tag Parser

Embed action tags in any text (e.g. AI responses, slash command replies):

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
# WidgetBot embed
WIDGETBOT_SERVER=your_server_id
WIDGETBOT_CHANNEL=your_channel_id
WIDGETBOT_SHARD=                   # empty = free tier; https://e-business.widgetbot.co for paid

# Discord Bot (required for slash commands)
DISCORD_APPLICATION_ID=
DISCORD_PUBLIC_KEY=
DISCORD_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
DISCORD_GUILD_ID=                  # guild for slash command registration (empty = global)

# Interactions endpoint URL (empty = ngrok auto-detect)
INTERACTIONS_URL=

# Gemini AI
GEMINI_API_KEY=
GEMINI_MODEL=                      # default: gemini-2.0-flash
GEMINI_IMAGE_API_KEY=              # falls back to GEMINI_API_KEY
GEMINI_IMAGE_MODEL=                # default: gemini-2.0-flash-exp-image-generation
GEMINI_SEARCH_GROUNDING=           # default: true; set to "false" to disable

# Private AI Threads (optional)
AI_THREAD_PARENT_CHANNEL=          # channel ID; enables per-user private threads
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

[realtime] additive path:
server side      →  emit_command()       →  Socket.IO            →  Crate API (direct)
gen_store.add()  →  socketio.emit()      →  DashSocketIO prop    →  Dash callback
```

Key design decisions:

- **No build toolchain** — pure Python + inline JS via Dash hooks
- **Store bridge always active** — `dcc.Store` carries all commands and events; Socket.IO is purely additive
- **`set_props()`** — async event push from JS to Dash stores without callback returns
- **CDN-only** — WidgetBot JS loaded from jsDelivr; widget uses a plain cross-origin `<iframe>`
- **Namespaced IDs** — all store IDs prefixed with `_widgetbot-` to avoid collisions
- **Non-blocking sinks** — Discord API calls for progress edits fire in daemon threads; generation is never blocked by cosmetic channel edits

---

## Example App

Clone the repo and run the included 13-page example application:

```bash
git clone https://github.com/pip-install-python/dash-widgetbot
cd dash-widgetbot
pip install -e ".[all]"
cp .env.example .env          # fill in your server/channel IDs and API keys
python app.py
```

Open `http://127.0.0.1:8150`. Pages cover every feature:

| Page | What it shows |
|------|---------------|
| Home | Overview and quick-start |
| Crate Commands | toggle, notify, navigate, hide/show |
| Crate Events | live event log, last message, user status |
| Crate Styling | runtime color, position, glyph, embed colors |
| Widget Embed | inline iframe with event display |
| Multi-Instance | two additional named Crate instances |
| Bot Bridge | action tag parsing and execution sandbox |
| Slash Commands | interactions setup guide + local /ask test |
| AI Chat | Gemini structured responses with Discord preview |
| Webhook Send | outbound webhook composer |
| Rich Messages | Components V2 message builder |
| Rich Message Preview | live Components V2 visual builder |
| Gen Gallery | real-time feed of Discord `/gen` and `/ai` results |

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