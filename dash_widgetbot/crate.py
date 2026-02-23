"""DiscordCrate -- floating chat button powered by WidgetBot Crate v3.

Registers Dash hooks to inject stores, load CDN script, initialise
the Crate instance, wire events back to stores, and dispatch commands.
"""

from dash import hooks, html, dcc, Input, Output

from ._constants import CDN_CRATE, get_crate_store_ids

_cdn_loaded = False

# ---------------------------------------------------------------------------
# Clientside JS: initialise Crate and wire events
# ---------------------------------------------------------------------------
_INIT_JS = """
function(config) {
    if (!config || !config.server) return window.dash_clientside.no_update;

    var prefix = config._prefix || '';
    var crateKey = '_dashWidgetBotCrate' + (prefix ? '_' + prefix : '');

    // Guard double-init
    if (window[crateKey]) return window.dash_clientside.no_update;

    // CDN may not be loaded yet -- retry with exponential backoff
    if (typeof window.Crate === 'undefined') {
        var retryKey = '_widgetbot_retry' + (prefix ? '_' + prefix : '');
        var retryCount = window[retryKey] || 0;
        if (retryCount >= 10) {
            console.error('[dash-widgetbot] Crate CDN failed to load after 10 retries');
            return window.dash_clientside.no_update;
        }
        window[retryKey] = retryCount + 1;
        var delay = Math.min(200 * Math.pow(2, retryCount), 5000);
        var configStoreId = config._stores.config;
        setTimeout(function() {
            var retrigger = Object.assign({}, config, {_retry: retryCount + 1});
            window.dash_clientside.set_props(configStoreId, {data: retrigger});
        }, delay);
        return window.dash_clientside.no_update;
    }

    // Build options -------------------------------------------------------
    var opts = {server: config.server};
    var simple = ['channel','thread','color','css','username','avatar','token','shard'];
    for (var i = 0; i < simple.length; i++) {
        if (config[simple[i]]) opts[simple[i]] = config[simple[i]];
    }
    if (config.location)       opts.location = config.location;
    if (config.glyph)          opts.glyph = config.glyph;
    if (config.accessibility)  opts.accessibility = config.accessibility;
    // booleans
    if (config.notifications !== undefined)              opts.notifications = config.notifications;
    if (config.dm_notifications !== undefined)            opts.dmNotifications = config.dm_notifications;
    if (config.indicator !== undefined)                   opts.indicator = config.indicator;
    if (config.all_channel_notifications !== undefined)   opts.allChannelNotifications = config.all_channel_notifications;
    if (config.defer !== undefined)                       opts.defer = config.defer;
    // numbers
    if (config.timeout !== undefined)                     opts.timeout = config.timeout;
    if (config.embed_notification_timeout !== undefined)  opts.embedNotificationTimeout = config.embed_notification_timeout;
    if (config.settings_group)                            opts.settingsGroup = config.settings_group;

    // Create Crate --------------------------------------------------------
    var crate = new Crate(opts);
    window[crateKey] = crate;

    // Route-aware visibility (optional: config.pages)
    if (config.pages && Array.isArray(config.pages) && config.pages.length > 0) {
        var allowedPages = config.pages;

        function updateCrateVisibility() {
            var path = window.location.pathname;
            var isAllowed = allowedPages.indexOf(path) !== -1;
            isAllowed ? crate.show() : crate.hide();
        }

        // Apply immediately (handles direct page loads)
        updateCrateVisibility();

        // Set up one-time global route watcher for SPA navigation
        if (!window._dashWidgetBotRouteWatcher) {
            window._dashWidgetBotRouteWatcher = true;
            var origPushState = history.pushState;
            history.pushState = function() {
                origPushState.apply(this, arguments);
                window.dispatchEvent(new Event('_dashWidgetBotRouteChange'));
            };
            window.addEventListener('popstate', function() {
                window.dispatchEvent(new Event('_dashWidgetBotRouteChange'));
            });
        }

        // Each restricted Crate gets its own listener
        var routeListenerKey = crateKey + '_routeListener';
        if (!window[routeListenerKey]) {
            window[routeListenerKey] = function() { updateCrateVisibility(); };
            window.addEventListener('_dashWidgetBotRouteChange', window[routeListenerKey]);
        }
    }

    // Store IDs for event wiring
    var sid = config._stores;

    // Wire events ---------------------------------------------------------
    crate.on('ready', function() {
        window.dash_clientside.set_props(sid.status, {
            data: {initialized: true, open: false, _ts: Date.now()}
        });
    });

    crate.on('message', function(data) {
        var msg = data && data.message ? data.message : (data || {});
        window.dash_clientside.set_props(sid.message, {data: {
            content: msg.content || '',
            author: msg.author ? {
                username: msg.author.username || '',
                id: msg.author.id || '',
                avatar: msg.author.avatar || ''
            } : {},
            channel: data && data.channel ? (data.channel.name || '') : '',
            channel_id: data && data.channel ? (data.channel.id || '') : '',
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('signIn', function(user) {
        window.dash_clientside.set_props(sid.user, {data: {
            username: user.username || '', id: user.id || '',
            avatar: user.avatarUrl || '', provider: user.provider || '',
            signed_in: true, _ts: Date.now()
        }});
    });

    crate.on('alreadySignedIn', function(user) {
        window.dash_clientside.set_props(sid.user, {data: {
            username: user.username || '', id: user.id || '',
            avatar: user.avatarUrl || '', provider: user.provider || '',
            signed_in: true, _ts: Date.now()
        }});
    });

    crate.on('signOut', function() {
        window.dash_clientside.set_props(sid.user, {
            data: {signed_in: false, _ts: Date.now()}
        });
    });

    crate.on('sentMessage', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'sentMessage', content: data.content || '',
            channel_id: data.channel ? (data.channel.id || '') : '',
            channel_name: data.channel ? (data.channel.name || '') : '',
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('messageDelete', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'messageDelete', message_id: data.id || '',
            channel: data.channel ? (data.channel.id || '') : '',
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('messageDeleteBulk', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'messageDeleteBulk', ids: data.ids || [],
            channel: data.channel ? (data.channel.id || '') : '',
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('messageUpdate', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'messageUpdate', message: data.message || {},
            channel: data.channel ? (data.channel.id || '') : '',
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('unreadCountUpdate', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'unreadCountUpdate', count: data.count || 0,
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('directMessage', function(data) {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'directMessage', message: data.message || {},
            timestamp: Date.now(), _ts: Date.now()
        }});
    });

    crate.on('loginRequested', function() {
        window.dash_clientside.set_props(sid.event, {data: {
            type: 'loginRequested', timestamp: Date.now(), _ts: Date.now()
        }});
    });

    return window.dash_clientside.no_update;
}
"""

# ---------------------------------------------------------------------------
# Clientside JS: dispatch commands from the command store
# ---------------------------------------------------------------------------
_DISPATCH_JS = """
function(cmd) {
    if (!cmd || !cmd.action) return window.dash_clientside.no_update;

    var prefix = cmd._prefix || '';
    var crateKey = '_dashWidgetBotCrate' + (prefix ? '_' + prefix : '');
    var crate = window[crateKey];

    if (!crate) {
        console.warn('[dash-widgetbot] Crate not initialised for prefix "' + prefix + '"');
        return window.dash_clientside.no_update;
    }

    switch (cmd.action) {
        case 'toggle':
            crate.toggle(cmd.value);
            break;
        case 'notify':
            crate.notify(cmd.data || '');
            break;
        case 'navigate':
            if (typeof cmd.data === 'string') { crate.navigate(cmd.data); }
            else if (cmd.data) { crate.emit('navigate', cmd.data); }
            break;
        case 'hide':
            crate.hide();
            break;
        case 'show':
            crate.show();
            break;
        case 'update_options':
            crate.setOptions(cmd.data || {});
            break;
        case 'send_message':
            crate.emit('sendMessage', cmd.data);
            break;
        case 'login':
            crate.emit('login');
            break;
        case 'logout':
            crate.emit('logout');
            break;
        case 'color':
            if (cmd.data && Array.isArray(cmd.data)) {
                crate.emit('color', cmd.data);
            }
            break;
        case 'emit':
            crate.emit(cmd.event, cmd.data);
            break;
    }

    return window.dash_clientside.no_update;
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_discord_crate(
    server,
    channel="",
    *,
    color="#5865f2",
    location=None,
    glyph=None,
    css="",
    notifications=True,
    dm_notifications=True,
    indicator=True,
    timeout=10000,
    all_channel_notifications=False,
    embed_notification_timeout=0,
    defer=False,
    username="",
    avatar="",
    token="",
    thread="",
    shard="",
    accessibility=None,
    settings_group="",
    prefix="",
    pages=None,
):
    """Register a WidgetBot Crate instance via Dash hooks.

    Returns the store IDs dict so callers can wire callbacks::

        ids = add_discord_crate(server="123", channel="456")
        # ids['command']  -> write commands here
        # ids['message']  -> read incoming messages
    """
    global _cdn_loaded

    store_ids = get_crate_store_ids(prefix)

    # 1. CDN script (once across all instances) ----------------------------
    if not _cdn_loaded:
        hooks.script(
            [{"external_url": CDN_CRATE, "external_only": True}]
        )
        _cdn_loaded = True

    # 2. Config data -------------------------------------------------------
    config_data = {
        "server": server,
        "channel": channel,
        "color": color,
        "location": location or ["bottom", "right"],
        "css": css,
        "notifications": notifications,
        "dm_notifications": dm_notifications,
        "indicator": indicator,
        "timeout": timeout,
        "all_channel_notifications": all_channel_notifications,
        "embed_notification_timeout": embed_notification_timeout,
        "defer": defer,
        "username": username,
        "avatar": avatar,
        "token": token,
        "thread": thread,
        "shard": shard,
        "settings_group": settings_group,
        "_prefix": prefix,
        "_stores": store_ids,
        "pages": pages or [],
    }
    if glyph:
        config_data["glyph"] = glyph
    if accessibility:
        config_data["accessibility"] = accessibility

    # 3. Layout: inject dcc.Store components -------------------------------
    @hooks.layout()
    def _inject_stores(layout):
        stores = html.Div(
            [
                dcc.Store(id=store_ids["config"], data=config_data),
                dcc.Store(id=store_ids["command"]),
                dcc.Store(id=store_ids["event"]),
                dcc.Store(id=store_ids["message"]),
                dcc.Store(id=store_ids["user"]),
                dcc.Store(id=store_ids["status"]),
            ],
            style={"display": "none"},
        )
        if isinstance(layout, list):
            return [stores] + layout
        return [stores, layout]

    # 4. Init callback: create Crate, wire events -------------------------
    hooks.clientside_callback(
        _INIT_JS,
        Output(store_ids["status"], "data", allow_duplicate=True),
        Input(store_ids["config"], "data"),
        prevent_initial_call="initial_duplicate",
    )

    # 5. Command dispatch callback -----------------------------------------
    hooks.clientside_callback(
        _DISPATCH_JS,
        Output(store_ids["status"], "data", allow_duplicate=True),
        Input(store_ids["command"], "data"),
        prevent_initial_call=True,
    )

    return store_ids
