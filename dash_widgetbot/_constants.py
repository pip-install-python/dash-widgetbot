"""Store IDs, CDN URLs, and defaults for dash-widgetbot."""

CDN_CRATE = "https://cdn.jsdelivr.net/npm/@widgetbot/crate@3"
DEFAULT_SHARD = "https://e.widgetbot.io"

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


# ---------------------------------------------------------------------------
# Discord Components V2
# ---------------------------------------------------------------------------

COMPONENT_TYPES = {
    "action_row": 1,
    "button": 2,
    "string_select": 3,
    "text_input": 4,
    "user_select": 5,
    "role_select": 6,
    "mentionable_select": 7,
    "channel_select": 8,
    "section": 9,
    "text_display": 10,
    "thumbnail": 11,
    "media_gallery": 12,
    "file": 13,
    "separator": 14,
    "container": 17,
    "label": 18,
    "file_upload": 19,
    "radio_group": 21,
    "checkbox_group": 22,
    "checkbox": 23,
}

BUTTON_STYLES = {
    "primary": 1,
    "secondary": 2,
    "success": 3,
    "danger": 4,
    "link": 5,
    "premium": 6,
}

TEXT_INPUT_STYLES = {
    "short": 1,
    "paragraph": 2,
}

# Message flag for Components V2 payloads
IS_COMPONENTS_V2 = 1 << 15  # 32768

# ---------------------------------------------------------------------------
# Socket.IO namespaces and event names
# ---------------------------------------------------------------------------

SIO_NAMESPACE_CRATE = "/widgetbot-crate"
SIO_NAMESPACE_GEN   = "/widgetbot-gen"

SIO_EVENT_CRATE_COMMAND = "crate_command"   # server → client
SIO_EVENT_CRATE_EVENT   = "crate_event"     # client → server
SIO_EVENT_CRATE_MESSAGE = "crate_message"   # client → server
SIO_EVENT_CRATE_USER    = "crate_user"      # client → server
SIO_EVENT_CRATE_STATUS  = "crate_status"    # bidirectional

SIO_EVENT_GEN_RESULT    = "gen_result"      # server → client
SIO_EVENT_GEN_PROGRESS  = "gen_progress"    # server → client
