# WidgetBot.io Skill Reference - dash-widgetbot

## Overview

dash-widgetbot is a Dash hooks plugin that integrates WidgetBot Discord embeds into Plotly Dash applications. It provides two primary components: **DiscordCrate** (floating chat button) and **DiscordWidget** (inline embedded chat).

## Architecture: Hooks-Based Plugin (No Build Toolchain)

The plugin uses Dash 3.x hooks (`hooks.layout`, `hooks.clientside_callback`, `hooks.script`) to inject WidgetBot functionality into any Dash app. Communication flows through `dcc.Store` components acting as a bridge between Python callbacks and the imperative WidgetBot JavaScript API.

```
Dash Callbacks --> dcc.Store (command) --> clientside_callback --> Crate API
Crate events   --> clientside_callback --> dcc.Store (events)  --> Dash Callbacks
```

## Why Hooks Over React Components

1. **No build toolchain** - No webpack, npm, or React compilation needed
2. **Imperative API fit** - Crate's `.toggle()`, `.notify()`, `.navigate()` map naturally to command dicts dispatched through stores
3. **set_props** - Crate events fire asynchronously from outside React; `set_props()` pushes data into stores directly
4. **Multi-instance** - `prefix` parameter enables multiple Crate instances without ID collisions
5. **Zero bundle impact** - Crate loads from jsdelivr CDN; no webpack bundle growth
6. **Pure Python** - Entire plugin is Python + inline JS strings

## DiscordCrate Features

### Constructor Options (Full)
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| server | str | (required) | Discord server ID |
| channel | str | "" | Default channel ID |
| thread | str | "" | Thread ID |
| color | str | "#5865f2" | Button color |
| location | list | ["bottom","right"] | [vertical, horizontal] position |
| glyph | list | None | [icon_url, css_size] custom button icon |
| css | str | "" | CSS injected into Shadow DOM |
| notifications | bool | True | Message notifications |
| dm_notifications | bool | True | DM notifications |
| indicator | bool | True | Unread indicator dot |
| timeout | int | 10000 | Notification timeout (ms) |
| all_channel_notifications | bool | False | Notify for ALL channels |
| embed_notification_timeout | int | 0 | Embed notification timeout |
| defer | bool | False | Only load when user opens |
| username | str | "" | Pre-fill guest username |
| avatar | str | "" | Pre-fill guest avatar URL |
| token | str | "" | JWT auth token |
| shard | str | "" | Custom WidgetBot server URL |
| accessibility | list | None | Accessibility settings |
| settings_group | str | "" | Settings group |
| prefix | str | "" | Multi-instance namespace |

### Command Functions (Python Helpers)
| Function | Description |
|----------|-------------|
| `crate_toggle(is_open, prefix)` | Open/close the widget |
| `crate_notify(content, timeout, avatar, prefix)` | Show notification bubble |
| `crate_navigate(channel, guild, prefix)` | Navigate to channel |
| `crate_hide(prefix)` | Hide entire Crate |
| `crate_show(prefix)` | Show hidden Crate |
| `crate_update_options(prefix, **opts)` | Update options at runtime |
| `crate_send_message(message, channel, prefix)` | Send message to Discord |
| `crate_login(prefix)` | Request user login |
| `crate_logout(prefix)` | Log user out |
| `crate_set_color(variable, value, prefix)` | Set embed color (background/accent/primary) |
| `crate_emit(event, data, prefix)` | Raw embed-api command |

### Events (JS to Python via Stores)
| Event | Store | Data Shape |
|-------|-------|-----------|
| message | message store | `{content, author: {username, id, avatar}, channel, channel_id, timestamp}` |
| signIn | user store | `{username, id, avatar, provider, signed_in: true}` |
| alreadySignedIn | user store | `{username, id, avatar, provider, signed_in: true}` |
| signOut | user store | `{signed_in: false}` |
| sentMessage | event store | `{type: 'sentMessage', content, channel, timestamp}` |
| messageDelete | event store | `{type: 'messageDelete', message_id, channel, timestamp}` |
| messageDeleteBulk | event store | `{type: 'messageDeleteBulk', ids[], channel, timestamp}` |
| messageUpdate | event store | `{type: 'messageUpdate', message, channel, timestamp}` |
| ready | status store | `{initialized: true, open: false}` |
| unreadCountUpdate | event store | `{type: 'unreadCountUpdate', count, timestamp}` |
| directMessage | event store | `{type: 'directMessage', message, timestamp}` |
| loginRequested | event store | `{type: 'loginRequested', timestamp}` |

### Store IDs
| Key | ID | Purpose |
|-----|-----|---------|
| config | `_widgetbot-crate-config` | Crate constructor options |
| command | `_widgetbot-crate-command` | Command dispatch (Python to JS) |
| event | `_widgetbot-crate-event` | Generic event stream (JS to Python) |
| message | `_widgetbot-crate-message` | Message data (JS to Python) |
| user | `_widgetbot-crate-user` | User sign-in/out state (JS to Python) |
| status | `_widgetbot-crate-status` | Init/open state (bidirectional) |

## DiscordWidget Features

### Attributes
| Attribute | Type | Description |
|-----------|------|-------------|
| server | str | Discord server ID (required) |
| channel | str | Channel ID |
| thread | str | Thread ID |
| width | str | Width (CSS, e.g. "100%") |
| height | str | Height (CSS, e.g. "600px") |
| username | str | Dynamic username |
| avatar | str | Dynamic avatar URL |
| notifications | bool | Enable notifications |

### API Access
Same embed-api events and commands as Crate, accessed through the DOM element's `.on()` and `.emit()` methods.

## Usage Examples

### Basic Setup
```python
from dash_widgetbot import add_discord_crate
add_discord_crate(server="YOUR_SERVER_ID", channel="YOUR_CHANNEL_ID")
```

### Callback Integration
```python
from dash import callback, Input, Output
from dash_widgetbot import crate_toggle, crate_notify, STORE_IDS

# Open chat on button click
@callback(Output(STORE_IDS['command'], 'data'), Input('btn', 'n_clicks'), prevent_initial_call=True)
def open_chat(n):
    return crate_toggle(True)

# React to Discord messages
@callback(Output('feed', 'children'), Input(STORE_IDS['message'], 'data'), prevent_initial_call=True)
def on_message(msg):
    return f"{msg['author']['username']}: {msg['content']}" if msg else ""
```

### Multi-Instance
```python
add_discord_crate(server=SRV, channel=CH1, prefix="support", location=["bottom","right"], color="#5865f2")
add_discord_crate(server=SRV, channel=CH2, prefix="community", location=["bottom","left"], color="#2ecc71")

# Target specific instance
@callback(Output(f"support-_widgetbot-crate-command", 'data'), ...)
def open_support(n):
    return crate_toggle(True, prefix="support")
```

## Project Structure
```
dash-widgetbot/
├── dash_widgetbot/          # Plugin package
│   ├── __init__.py          # Public API
│   ├── crate.py             # Crate hooks
│   ├── widget.py            # Widget hooks
│   ├── _bridge.py           # Command helpers
│   └── _constants.py        # IDs, URLs, defaults
├── pages/                   # Example pages
│   ├── home.py              # Overview
│   ├── crate_commands.py    # Command demos
│   ├── crate_events.py      # Event demos
│   ├── crate_styling.py     # Styling demos
│   ├── widget_embed.py      # Inline widget
│   └── multi_instance.py    # Multi-crate
├── app.py                   # Example app
├── .env.example             # Config template
└── pyproject.toml           # Package metadata
```
