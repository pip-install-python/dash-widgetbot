# Changelog

All notable changes to **dash-widgetbot** will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-02-21

Initial release.

### Added

#### DiscordCrate (`add_discord_crate`)
- Floating Discord chat button via `@widgetbot/crate@3` CDN (no npm/webpack required)
- Full Crate API control through `dcc.Store` command bridge:
  - `crate_toggle()` — open/close the popup
  - `crate_notify()` — show notification bubble with custom text, timeout, and avatar
  - `crate_navigate()` — navigate to a Discord channel
  - `crate_hide()` / `crate_show()` — show or hide the entire button
  - `crate_update_options()` — update Crate configuration at runtime
  - `crate_set_color()` — change embed CSS color variables
  - `crate_send_message()` — send a message on behalf of the signed-in user
  - `crate_login()` / `crate_logout()` — trigger auth flows
  - `crate_emit()` — send any raw embed-api command
- Event stores wired via `window.dash_clientside.set_props()`:
  - `event` store — signIn, signOut, sentMessage, toggle, ready, messageDelete, messageUpdate, unreadCountUpdate, directMessage, loginRequested
  - `message` store — new messages with content, author, channel
  - `user` store — signed-in user profile (username, id, avatar, provider)
  - `status` store — initialized flag, open/closed state
- Multi-instance support via `prefix` parameter (avoids store ID collisions)
- Page-scoped visibility via `pages` parameter (SPA route filtering)
- CDN load retry with exponential backoff (up to 5s) for slow connections
- Guard against double initialization (`window._dashWidgetBotCrate`)

#### DiscordWidget (`add_discord_widget` + `discord_widget_container`)
- Inline Discord channel embed rendered as a plain cross-origin `<iframe>`
- No CDN script required — eliminates `webcomponents-ce.js` polyfill conflict with Crate
- Events captured via `window.addEventListener('message', ...)` using WidgetBot's postMessage protocol (`{ widgetbot: true, event, data }`)
- Event stores: `event` (ready, sentMessage, signIn, signOut, messageUpdate, alreadySignedIn) and `message` (new messages)
- Per-container guard prevents duplicate listener registration

#### Action Tag Parser (`parse_actions`, `strip_actions`, `ACTION_PARSER_JS`)
- Regex-based `[ACTION:type:data]` tag system for embedding commands in plain text
- Supported actions: `navigate`, `notify`, `toggle`, `hide`, `show`, `open_url`
- Python parser (`parse_actions`, `strip_actions`) and matching JavaScript implementation (`ACTION_PARSER_JS`) for clientside use

#### Discord Interactions Endpoint (`add_discord_interactions`, `register_command`)
- Flask route registered at `/api/discord/interactions` via `hooks.route()`
- Ed25519 signature verification via `PyNaCl`
- PING/PONG handler for Discord endpoint verification
- Deferred response pattern: immediately returns HTTP 200 with type 5, then processes command in background thread and PATCHes the follow-up response
- `register_command(name)` decorator for slash command handlers

#### Outbound Webhook (`send_webhook_message`)
- POST to any Discord webhook URL with content, username override, avatar override, and thread targeting
- Returns structured result dict with `success`, `status_code`, `message_id`, and `error`

#### Gemini AI Responder (`generate_response`)
- Lazy-loaded `google-generativeai` integration
- System prompt instructs Gemini to embed `[ACTION:...]` tags in responses for autonomous Dash navigation/control
- Returns `text`, `actions` (parsed list), and `error`

#### Example Application (10 pages)
- `home.py` — feature overview and quick-start code
- `crate_commands.py` — toggle, notify, navigate, hide/show controls
- `crate_events.py` — live event log, last message, and user status cards
- `crate_styling.py` — runtime color, position, glyph, and embed color customization
- `widget_embed.py` — inline widget with live event display
- `multi_instance.py` — two additional named Crate instances with independent controls
- `bot_bridge.py` — action tag parsing and execution sandbox
- `slash_commands.py` — Discord interactions endpoint setup guide
- `ai_chat.py` — Gemini AI chat with action badge execution
- `webhook_send.py` — outbound webhook message composer

#### Packaging
- `pyproject.toml` with setuptools build backend
- `dash_widgetbot` as sole package (hooks registration, no compiled assets)
- `.env.example` with all required and optional environment variable names

---

[0.1.0]: https://github.com/pip-install-python/dash-widgetbot/releases/tag/v0.1.0
