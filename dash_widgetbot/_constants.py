"""Store IDs, CDN URLs, and defaults for dash-widgetbot."""

CDN_CRATE = "https://cdn.jsdelivr.net/npm/@widgetbot/crate@3"

CRATE_STORE_KEYS = ("config", "command", "event", "message", "user", "status")

CRATE_DEFAULTS = {
    "color": "#5865f2",
    "location": ["bottom", "right"],
    "notifications": True,
    "dm_notifications": True,
    "indicator": True,
    "timeout": 10000,
    "all_channel_notifications": False,
    "embed_notification_timeout": 0,
    "defer": False,
}

WIDGET_STORE_KEYS = ("config", "command", "event", "message")


def get_crate_store_ids(prefix=""):
    """Return a dict mapping store keys to namespaced store IDs.

    With prefix="support": {"config": "support-_widgetbot-crate-config", ...}
    Without prefix:        {"config": "_widgetbot-crate-config", ...}
    """
    base = f"{prefix}-_widgetbot-crate" if prefix else "_widgetbot-crate"
    return {key: f"{base}-{key}" for key in CRATE_STORE_KEYS}


def get_widget_store_ids(container_id=""):
    """Return a dict mapping store keys to namespaced store IDs for a widget."""
    tag = container_id or "default"
    base = f"_widgetbot-widget-{tag}"
    return {key: f"{base}-{key}" for key in WIDGET_STORE_KEYS}
