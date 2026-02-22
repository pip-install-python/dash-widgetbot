"""dash-widgetbot -- Dash hooks plugin for WidgetBot Discord embeds."""

__version__ = "0.1.0"

from .crate import add_discord_crate
from .widget import add_discord_widget, discord_widget_container
from ._bridge import (
    crate_toggle,
    crate_notify,
    crate_navigate,
    crate_hide,
    crate_show,
    crate_update_options,
    crate_send_message,
    crate_login,
    crate_logout,
    crate_set_color,
    crate_emit,
)
from ._constants import get_crate_store_ids, get_widget_store_ids
from .action_parser import parse_actions, strip_actions, ACTION_PARSER_JS

# Optional: bot integration (requires requests + PyNaCl)
try:
    from .interactions import add_discord_interactions, register_command, verify_signature
    from .webhook import send_webhook_message
except ImportError:
    def add_discord_interactions(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def register_command(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def verify_signature(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def send_webhook_message(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests'. "
            "Install with: pip install dash-widgetbot[bot]"
        )

# Optional: AI responder (requires google-generativeai)
try:
    from .ai_responder import generate_response
except ImportError:
    def generate_response(*a, **kw):
        raise ImportError(
            "dash-widgetbot AI features require 'google-generativeai'. "
            "Install with: pip install dash-widgetbot[ai]"
        )

# Convenience: default (no-prefix) store IDs
STORE_IDS = get_crate_store_ids()

__all__ = [
    "__version__",
    "add_discord_crate",
    "add_discord_widget",
    "discord_widget_container",
    "crate_toggle",
    "crate_notify",
    "crate_navigate",
    "crate_hide",
    "crate_show",
    "crate_update_options",
    "crate_send_message",
    "crate_login",
    "crate_logout",
    "crate_set_color",
    "crate_emit",
    "get_crate_store_ids",
    "get_widget_store_ids",
    "STORE_IDS",
    "parse_actions",
    "strip_actions",
    "ACTION_PARSER_JS",
    # Bot integration (requires [bot] extra)
    "add_discord_interactions",
    "register_command",
    "verify_signature",
    "send_webhook_message",
    # AI integration (requires [ai] extra)
    "generate_response",
]
