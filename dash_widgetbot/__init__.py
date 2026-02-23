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
    from .interactions import (
        add_discord_interactions,
        register_command,
        register_component_handler,
        register_modal_handler,
        sync_discord_endpoint,
        verify_signature,
    )
    from .webhook import send_webhook_message
    from .components import (
        action_row,
        button,
        channel_select,
        components_v2_message,
        container,
        file,
        media_gallery,
        mentionable_select,
        modal_response,
        role_select,
        section,
        select_default_value,
        select_option,
        separator,
        string_select,
        text_display,
        text_input,
        thumbnail,
        unfurl_media,
        user_select,
        # Modal components
        checkbox,
        checkbox_group,
        checkbox_option,
        file_upload,
        label,
        radio_group,
        radio_option,
    )
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
    def register_component_handler(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def register_modal_handler(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def verify_signature(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def sync_discord_endpoint(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests' and 'PyNaCl'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    def send_webhook_message(*a, **kw):
        raise ImportError(
            "dash-widgetbot bot features require 'requests'. "
            "Install with: pip install dash-widgetbot[bot]"
        )
    # Component builders have no deps but are grouped with [bot] for API coherence
    def action_row(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def button(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def channel_select(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def components_v2_message(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def container(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def file(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def media_gallery(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def mentionable_select(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def modal_response(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def role_select(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def section(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def select_default_value(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def select_option(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def separator(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def string_select(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def text_display(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def text_input(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def thumbnail(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def unfurl_media(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def user_select(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def checkbox(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def checkbox_group(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def checkbox_option(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def file_upload(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def label(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def radio_group(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")
    def radio_option(*a, **kw): raise ImportError("Install with: pip install dash-widgetbot[bot]")

# Optional: AI responder (requires google-genai)
try:
    from .ai_responder import generate_response, generate_structured_response
except ImportError:
    def generate_response(*a, **kw):
        raise ImportError(
            "dash-widgetbot AI features require 'google-genai'. "
            "Install with: pip install dash-widgetbot[ai]"
        )
    def generate_structured_response(*a, **kw):
        raise ImportError(
            "dash-widgetbot AI features require 'google-genai'. "
            "Install with: pip install dash-widgetbot[ai]"
        )

# Optional: AI builder + image gen (no extra deps beyond requests)
try:
    from .ai_builder import build_components_v2
    from .ai_image import generate_image
    from .ai_schemas import AIResponse
except ImportError:
    def build_components_v2(*a, **kw):
        raise ImportError("Install with: pip install dash-widgetbot[ai]")
    def generate_image(*a, **kw):
        raise ImportError("Install with: pip install dash-widgetbot[ai]")
    AIResponse = None

# Optional: Gen command (requires google-genai + dash-mantine-components)
try:
    from .gen_responder import generate_gen_response
    from .gen_schemas import GenResponse, GenFormat
    from .gen_store import gen_store, GenEntry
    from .gen_renderer import render_gen_card
except ImportError:
    def generate_gen_response(*a, **kw):
        raise ImportError("Install with: pip install dash-widgetbot[ai]")
    GenResponse = None
    GenFormat = None
    gen_store = None
    GenEntry = None
    def render_gen_card(*a, **kw):
        raise ImportError("Install with: pip install dash-widgetbot[ai]")

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
    "register_component_handler",
    "register_modal_handler",
    "verify_signature",
    "sync_discord_endpoint",
    "send_webhook_message",
    # Components V2 builders (requires [bot] extra)
    "action_row",
    "button",
    "channel_select",
    "components_v2_message",
    "container",
    "file",
    "media_gallery",
    "mentionable_select",
    "modal_response",
    "role_select",
    "section",
    "select_default_value",
    "select_option",
    "separator",
    "string_select",
    "text_display",
    "text_input",
    "thumbnail",
    "unfurl_media",
    "user_select",
    # Modal components (requires [bot] extra)
    "checkbox",
    "checkbox_group",
    "checkbox_option",
    "file_upload",
    "label",
    "radio_group",
    "radio_option",
    # AI integration (requires [ai] extra)
    "generate_response",
    "generate_structured_response",
    "build_components_v2",
    "generate_image",
    "AIResponse",
    # Gen command (requires [ai] extra)
    "generate_gen_response",
    "GenResponse",
    "GenFormat",
    "gen_store",
    "GenEntry",
    "render_gen_card",
]
