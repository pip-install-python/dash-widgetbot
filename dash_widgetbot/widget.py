"""DiscordWidget -- inline embedded Discord chat via plain iframe + postMessage.

Renders the WidgetBot embed as a standard ``html.Iframe`` pointing directly to
the configured shard (default ``https://e.widgetbot.io``).  No CDN script is
required, so there is no polyfill conflict with the Crate CDN.

Events are received by registering a single ``window.addEventListener('message',
...)`` listener scoped to the specific iframe via ``event.source``.
"""

from dash import hooks, html, dcc, Input, Output

from ._constants import get_widget_store_ids, DEFAULT_SHARD

# ---------------------------------------------------------------------------
# Clientside JS: register postMessage listener and wire events
# ---------------------------------------------------------------------------
_INIT_JS = """
function(config) {
    if (!config || !config.server) return window.dash_clientside.no_update;

    var containerId = config._container_id;
    var listenerKey = '_dashWidgetBotMsgListener_' + containerId;

    // Guard: register the postMessage listener only once per container
    if (window[listenerKey]) return window.dash_clientside.no_update;

    var sid = config._stores;

    function handleMessage(event) {
        // 1. Parse -- WidgetBot sends a JSON string
        var raw = event.data;
        var data;
        try { data = (typeof raw === 'string') ? JSON.parse(raw) : raw; }
        catch (e) { return; }

        // 2. Verify this is a WidgetBot embed-api message
        if (!data || data.widgetbot !== true) return;

        // 3. Verify origin (use configured shard, fall back to default)
        var expectedOrigin = (config.shard || '').replace(/\/$/, '') || 'https://e.widgetbot.io';
        if (event.origin !== expectedOrigin) return;

        // NOTE: Do NOT check event.source vs iframe.contentWindow --
        // cross-origin iframes return null for contentWindow, so that
        // guard would silently drop every message.

        // 4. Read the correct fields: embed-api uses { widgetbot, event, data }
        var evType = data.event;   // field is 'event', NOT 'type'
        var evData = data.data || {};

        switch (evType) {
            case 'ready':
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'ready', timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'message':
                var msg = evData.message || {};
                window.dash_clientside.set_props(sid.message, {data: {
                    content: msg.content || '',
                    author: msg.author ? {
                        username: msg.author.username || msg.author.name || '',
                        id: msg.author.id || '',
                        avatar: msg.author.avatarUrl || ''
                    } : {},
                    channel: evData.channel ? (evData.channel.name || '') : '',
                    channel_id: evData.channel ? (evData.channel.id || '') : '',
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'sentMessage':
                var ch = evData.channel;
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'sentMessage',
                    content: evData.content || '',
                    channel: ch ? (ch.name || ch.id || '') : '',
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'signIn':
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'signIn',
                    username: evData.username || evData.name || '',
                    id: evData.id || evData._id || '',
                    signed_in: true,
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'alreadySignedIn':
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'signIn',
                    username: evData.username || evData.name || '',
                    id: evData.id || evData._id || '',
                    signed_in: true,
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'signOut':
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'signOut', signed_in: false,
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
            case 'messageUpdate':
                window.dash_clientside.set_props(sid.event, {data: {
                    type: 'messageUpdate',
                    message: evData.message || {},
                    channel: evData.channel ? (evData.channel.id || '') : '',
                    timestamp: Date.now(), _ts: Date.now()
                }});
                break;
        }
    }

    window.addEventListener('message', handleMessage);
    window[listenerKey] = handleMessage;

    return window.dash_clientside.no_update;
}
"""


def discord_widget_container(server, channel="", *, width="100%", height="600px",
                             shard="", container_id="widgetbot-container"):
    """Return an ``html.Iframe`` that embeds the Discord channel directly.

    Place this in your page layout where the inline widget should appear.
    """
    shard_url = shard.rstrip("/") if shard else DEFAULT_SHARD
    return html.Iframe(
        src=f"{shard_url}/channels/{server}/{channel}",
        id=container_id,
        style={"width": width, "height": height, "border": "none"},
        allow="clipboard-write",
    )


def add_discord_widget(
    server,
    channel="",
    *,
    width="100%",
    height="600px",
    username="",
    avatar="",
    shard="",
    container_id="widgetbot-container",
):
    """Register a WidgetBot inline widget via Dash hooks.

    Call this *before* creating the Dash app.  Then place
    ``discord_widget_container(...)`` in your page layout.

    Returns the widget store IDs dict.
    """
    store_ids = get_widget_store_ids(container_id)

    # Config data ----------------------------------------------------------
    config_data = {
        "server": server,
        "channel": channel,
        "width": width,
        "height": height,
        "username": username,
        "avatar": avatar,
        "shard": shard,
        "_container_id": container_id,
        "_stores": store_ids,
    }

    # Layout: inject stores ------------------------------------------------
    @hooks.layout()
    def _inject_stores(layout):
        stores = html.Div(
            [
                dcc.Store(id=store_ids["config"], data=config_data),
                dcc.Store(id=store_ids["command"]),
                dcc.Store(id=store_ids["event"]),
                dcc.Store(id=store_ids["message"]),
            ],
            style={"display": "none"},
        )
        if isinstance(layout, list):
            return [stores] + layout
        return [stores, layout]

    # Init callback: register postMessage listener -------------------------
    hooks.clientside_callback(
        _INIT_JS,
        Output(store_ids["event"], "data", allow_duplicate=True),
        Input(store_ids["config"], "data"),
        prevent_initial_call="initial_duplicate",
    )

    return store_ids
