# Changelog

All notable changes to **dash-widgetbot** will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project follows [Semantic Versioning](https://semver.org/).

---

## [0.4.0] — 2026-02-23

### Added

#### AI Task Progress Streaming

- **`progress.py`** (new module) — `ProgressTracker` fans out `ProgressEvent` updates to
  multiple sinks with per-sink throttling and phase-based progress percentages
- **`ProgressEvent`** dataclass with `format_discord()` rendering text progress bars:
  `[████████░░] 80% Generating AI response... (1,200 bytes received)`
- **4 sink implementations:**
  - `ChannelMessageSink` — edits the Crate-bridge loading message with progress bar text (3s throttle)
  - `EphemeralSink` — PATCHes the `@original` ephemeral deferred response (3s throttle)
  - `SocketIOSink` — emits `gen_progress` events on `/widgetbot-gen` namespace (0.5s throttle)
  - `CrateNotifySink` — pushes `crate.notify()` on phase transitions only (5s throttle)
- **Progress phases:** `analyzing` (0%) → `generating` (10-80%) → `parsing` (85%) →
  `creating_image` (90%) → `posting` (95%) → `complete` (100%)
- **Gemini streaming** — `generate_gen_response()` and `generate_structured_response()`
  accept `on_progress` kwarg; uses `generate_content_stream()` for chunk-level byte
  progress during text generation. Falls back to non-streaming on failure.
  **Zero additional Gemini API cost** — streaming delivers the same tokens incrementally.
- **`emit_progress()`** helper in `_bridge.py` for Socket.IO `gen_progress` events
- **`_edit_channel_message()`** helper in `interactions.py` for PATCHing channel messages
- **Tracker injection** — `_handle_command()` in `interactions.py` automatically creates
  a `ProgressTracker` with `EphemeralSink` + `SocketIOSink` for `/ai`, `/gen`, `/ask`
- **Crate-bridge tracker** — `_run()` in `app.py` creates tracker with
  `ChannelMessageSink` + `SocketIOSink` + `CrateNotifySink` for Crate-bridge AI commands
- **Gen Gallery progress cards** — `pages/discord_to_dash.py` listens for `gen_progress`
  Socket.IO events and renders animated `dmc.Progress` + `dmc.Loader` cards that
  appear during generation and auto-remove on completion
- **Exported:** `ProgressTracker`, `ProgressEvent`, `emit_progress` from `__init__.py`

#### Socket.IO Real-Time Transport (`[realtime]` extras)

- **`[realtime]` optional extras group** — `pip install dash-widgetbot[realtime]` adds
  `flask-socketio>=5.3.0`, `dash-socketio>=1.1.1`, and `simple-websocket>=1.0.0`
- **`configure_socketio(socketio)`** — public API to register the app's `SocketIO` instance
  with the hook; call once after `app = dash.Dash(...)` in your app entry point
- **`is_socketio_available()`** — introspection helper; returns `True` when `configure_socketio`
  has been called with a non-`None` instance
- **`emit_command(command_dict, namespace=None)`** — server-side push helper in `_bridge.py`;
  emits any crate command dict on the Socket.IO `/widgetbot-crate` namespace.
  Returns `True` if emitted, `False` when Socket.IO is not configured.
  Use from background threads or webhook handlers.
- **`_transport.py`** (new module) — singleton transport registry; no flask-socketio
  import at module level, fully safe to import without `[realtime]` installed
- **`SIO_NAMESPACE_CRATE`** / **`SIO_NAMESPACE_GEN`** — namespace constants exported
  from `_constants.py` and `__init__.py`

#### Dual-Path Design (store bridge always active, Socket.IO additive)

```
Store bridge (ALWAYS active)           Socket.IO path (opt-in, [realtime])
────────────────────────────           ──────────────────────────────────────
Crate event → set_props()              Crate event → socket.emit()
  → dcc.Store → Dash callback            → /widgetbot-crate NS

server cmd → dcc.Store                 server cmd → emit_command()
  → clientside_callback → Crate           → crate_command event → Crate

gen_store.add() → dcc.Interval         gen_store.add() → socketio.emit()
  → poll_gen_store → render cards        → /widgetbot-gen NS → render card
```

- **`crate.py`** — injects `DashSocketIO` component into the hidden stores `Div`
  when `[realtime]` packages are installed; JS init block connects to
  `/widgetbot-crate` namespace and mirrors every `set_props()` event call
  with a matching `socket.emit()` (zero latency for real-time listeners).
  Server-pushed `crate_command` events dispatch directly to the Crate API
  (same action handlers as `_DISPATCH_JS`).
- **`widget.py`** — same DashSocketIO injection and JS event mirroring as crate,
  using the `/widgetbot-crate` namespace; events only (no server→client commands).
- **`gen_store.GenStore.add()`** — emits `gen_result` on `/widgetbot-gen` after
  appending to the list (outside the lock); image bytes are **not** included in the
  payload — use `GET /api/gen/<entry_id>/image` instead.
- **`pages/discord_to_dash.py`** — adds `DashSocketIO` to layout and
  `_on_gen_result_sio` callback when packages are available; `dcc.Interval`
  stays active as the zero-dependency fallback.

#### New Routes (example app)

- **`GET /api/gen/<entry_id>/image`** — serves `image_bytes` for a `GenEntry` by ID;
  required since gen socket payloads omit bytes to stay JSON-serializable.

### Example App Integration Pattern

```python
from dash_widgetbot._transport import has_socketio_packages
_socketio = None
if has_socketio_packages():
    from flask_socketio import SocketIO
    from dash_widgetbot import configure_socketio
    _socketio = SocketIO(app.server, async_mode='threading', cors_allowed_origins="*")
    configure_socketio(_socketio)

if __name__ == "__main__":
    if _socketio:
        _socketio.run(app.server, debug=True, port=8150)
    else:
        app.run(debug=True, port=8150)
```

### Invariants

- All `dcc.Store` components remain — permanent fallback transport, unchanged
- All `set_props()` calls in JS fire alongside any Socket.IO emission
- `register_command()` signature unchanged
- `pip install dash-widgetbot` (no extras) runs cleanly with zero Socket.IO imports

---

## [0.3.0] — 2026-02-23

### Added

#### `/gen` and `/ai` Slash Commands
- `/gen` command — multi-format AI content generation with `GenResponse` schema: `article`, `code`, `data_table`, `image`, `callout`
- `/ai` command — single clean channel message with optional image attachment; ephemeral private ack to invoker only
- `gen_schemas.py` — `GenResponse`, `ArticleContent`, `CodeContent`, `DataTableContent`, `ImageContent`, `CalloutContent` Pydantic models
- `gen_responder.py` — `generate_gen_response()` using shared Gemini client from `ai_responder`; format-discriminated structured output
- `gen_store.py` — thread-safe in-memory `GenStore` + `GenEntry` for pushing AI-generated content to Dash pages without external deps (v2 SSE upgrade path documented inline)
- `gen_renderer.py` — renders `GenEntry` as styled DMC cards for each format variant

#### Crate-Bridge Slash Commands (`_handle_crate_slash`)
- Users can type `/ai prompt`, `/ask question`, `/gen prompt`, `/navigate path`, `/status` directly in the WidgetBot Crate as plain messages
- `sentMessage` event intercepted by `_handle_crate_slash` Dash callback; command parsed, fake interaction built, handler dispatched in background thread
- `crate.notify()` toast fires immediately (same callback return) for instant feedback
- `_CMD_OPTION_MAP` and `_CMD_NOTIFY` dicts drive per-command parsing and toast text

#### Loading Message Scoping (Crate-bridge only)
- `_post_loading_channel_message(channel_id, content)` and `_delete_channel_message(channel_id, message_id)` are now **Crate-bridge only**
- `_CRATE_LOADING_MSGS` dict in `app.py` maps `ask`/`ai`/`gen` to their loading texts
- Loading message posted before handler, deleted in `finally` — appears and disappears in the Crate feed
- Discord native slash commands (`/api/discord/interactions` type 2) keep only their type-5 "2plot.ai is thinking…" indicator — no duplicate public channel message

#### Gen Gallery Page (`/discord-to-dash`)
- `pages/discord_to_dash.py` — polls `gen_store` via `dcc.Interval` (2s), renders entries as DMC cards in an infinite-scroll feed
- Local test panel for development without Discord

### Changed
- `register_command()` signature simplified — `loading_message` parameter removed (loading messages now wired exclusively to the Crate-bridge `_run()` path)
- `_handle_command()` in `interactions.py` reverted to clean deferred-response-only pattern (no loading message logic)

### Console Log Notes (known, not actionable)
- `webcomponents-ce.js: A custom element 'mce-autosize-textarea' already defined` — originates inside the Crate iframe (WidgetBot internal); cannot be suppressed from outside
- Duplicate `[embed-api] on '...'` registrations — expected with 3 Crate instances (default + support + community prefixes)
- Cloudflare 401 PAT challenges from `challenges.cloudflare.com` — Cloudflare bot-challenge flow inside the WidgetBot iframe; benign
- WebSocket reconnects to `wss://stonks.widgetbot.io/api/graphql` — WidgetBot GraphQL subscription auto-reconnect; benign

---

## [0.2.0] — 2026-02-22

### Added

#### AI Structured Responses (`generate_structured_response`)
- JSON-mode structured output via Gemini API returning validated `AIResponse` Pydantic models
- `AIResponse` schema with semantic blocks: `TextBlock`, `SectionBlock`, `GalleryBlock`, `ButtonRow`, `ComponentBlock`
- `build_components_v2()` converts `AIResponse` into Discord Components V2 message payloads with container, text displays, sections, media galleries, action rows, and separators
- `render_discord_preview()` renders `AIResponse` as Discord-dark-themed DMC components for Dash preview pages
- `render_action_badges()` renders Dash app action badges from `AIResponse.actions`

#### Google Search Grounding
- `generate_structured_response()` enables Google Search grounding by default via `types.Tool(google_search=types.GoogleSearch())`
- Grounding source URLs extracted from `result.candidates[0].grounding_metadata.grounding_chunks`
- `SourceLink` model (`title`, `url`) for type-safe source representation
- `AIResponse.sources` field populated server-side from grounding metadata (not part of AI JSON output)
- Sources rendered as link buttons in Discord Components V2 messages (max 5 per action row)
- Sources rendered as styled anchor links in Dash Discord preview
- `GEMINI_SEARCH_GROUNDING` env var toggle (default `true`) to disable search grounding
- System prompt updated to inform model of web search capability

#### AI Image Generation (`generate_image`)
- `generate_image(prompt)` for Gemini-powered image generation
- `AIResponse.image_prompt` field triggers image generation when user explicitly requests it
- Generated images rendered as `media_gallery()` in Discord Components V2 messages

#### Discord Components V2 Builders (`components.py`)
- Full builder function library: `action_row`, `button`, `container`, `section`, `separator`, `text_display`, `media_gallery`, `file`, `thumbnail`, `unfurl_media`
- Interactive builders: `string_select`, `user_select`, `role_select`, `mentionable_select`, `channel_select`, `text_input`
- Modal builders: `checkbox`, `checkbox_group`, `checkbox_option`, `file_upload`, `label`, `radio_group`, `radio_option`
- Message-level: `components_v2_message()`, `modal_response()`
- Helper functions: `select_option()`, `select_default_value()`

#### Component & Modal Interaction Handlers
- `register_component_handler(custom_id, handler)` for button clicks and select changes
- `register_modal_handler(custom_id, handler)` for modal form submissions
- `sync_discord_endpoint(endpoint_url)` for Discord interactions URL registration
- Handler return types: `str` (content), `dict` (components/embeds), `dict` with `_modal: True` (modal response)

#### Webhook Components V2 Support
- `send_webhook_message()` now accepts `components` and `flags` parameters
- `content` parameter made optional (can send components-only messages)

#### Example Pages (new)
- `rich_messages.py` — Components V2 message builder showcase
- `rich_message_preview.py` — Live Discord Components V2 preview page

#### Example Pages (updated)
- `ai_chat.py` — Structured response mode with Discord preview, image generation, and source display
- `slash_commands.py` — Components V2 responses for `/ask` command with image support

### Changed
- `GEMINI_MODEL` env var now configurable (default `gemini-2.0-flash`)
- AI responder uses `google.genai.Client` (new SDK) instead of `google.generativeai` (legacy)

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

[0.4.0]: https://github.com/pip-install-python/dash-widgetbot/releases/tag/v0.4.0
[0.3.0]: https://github.com/pip-install-python/dash-widgetbot/releases/tag/v0.3.0
[0.2.0]: https://github.com/pip-install-python/dash-widgetbot/releases/tag/v0.2.0
[0.1.0]: https://github.com/pip-install-python/dash-widgetbot/releases/tag/v0.1.0
