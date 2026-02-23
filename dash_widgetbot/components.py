"""Discord Components V2 builder functions.

Pure dict builders — no network calls, no dependencies beyond stdlib.
Each function returns a dict matching Discord's component schema.

Reference: https://discord.com/developers/docs/components/reference
"""

from ._constants import (
    BUTTON_STYLES,
    COMPONENT_TYPES,
    IS_COMPONENTS_V2,
    TEXT_INPUT_STYLES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def select_option(label, value, *, description=None, emoji=None, default=False):
    """Build an option dict for ``string_select``.

    Parameters
    ----------
    label : str
        Display text (max 100 chars).
    value : str
        Value sent in the interaction (max 100 chars).
    description : str, optional
        Additional description (max 100 chars).
    emoji : dict, optional
        ``{"id": ..., "name": ..., "animated": ...}`` partial emoji object.
    default : bool
        Whether this option is selected by default.
    """
    opt = {"label": label, "value": value}
    if description is not None:
        opt["description"] = description
    if emoji is not None:
        opt["emoji"] = emoji
    if default:
        opt["default"] = True
    return opt


def select_default_value(id, type):
    """Build a default-value entry for auto-populated selects.

    Parameters
    ----------
    id : str
        Snowflake ID of the entity.
    type : str
        ``"user"``, ``"role"``, or ``"channel"``.
    """
    return {"id": id, "type": type}


def unfurl_media(url):
    """Build an unfurled media object: ``{"url": url}``."""
    return {"url": url}


# ---------------------------------------------------------------------------
# Layout Components
# ---------------------------------------------------------------------------

def action_row(*children, **kw):
    """Action Row (type 1) — horizontal row of buttons or a single select.

    Parameters
    ----------
    *children : dict
        Up to 5 buttons, or exactly 1 select menu component.
    **kw
        Extra fields merged into the component dict (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["action_row"], "components": list(children)}
    comp.update(kw)
    return comp


def container(*children, color=None, spoiler=False, **kw):
    """Container (type 17) — top-level wrapper with optional accent color.

    Parameters
    ----------
    *children : dict
        Child components (action_row, text_display, section, etc.).
    color : int, optional
        Accent color as integer (e.g. ``0x5865F2``).
    spoiler : bool
        Whether the container is initially collapsed behind a spoiler.
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["container"], "components": list(children)}
    if color is not None:
        comp["accent_color"] = color
    if spoiler:
        comp["spoiler"] = True
    comp.update(kw)
    return comp


def section(accessory, *fields, **kw):
    """Section (type 9) — text fields with a thumbnail or button accessory.

    Parameters
    ----------
    accessory : dict
        A ``thumbnail`` or ``button`` component displayed beside the fields.
    *fields : dict
        One or more ``text_display`` components.
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {
        "type": COMPONENT_TYPES["section"],
        "components": list(fields),
        "accessory": accessory,
    }
    comp.update(kw)
    return comp


def separator(*, divider=True, spacing=None, **kw):
    """Separator (type 14) — visual divider with optional spacing.

    Parameters
    ----------
    divider : bool
        Whether to render a visible line (default ``True``).
    spacing : str, optional
        ``"small"`` or ``"large"`` (maps to spacing enum 1/2).
    **kw
        Extra fields (e.g. ``id``).
    """
    _spacing_map = {"small": 1, "large": 2}
    comp = {"type": COMPONENT_TYPES["separator"], "divider": divider}
    if spacing is not None:
        comp["spacing"] = _spacing_map.get(spacing, spacing)
    comp.update(kw)
    return comp


# ---------------------------------------------------------------------------
# Content Components
# ---------------------------------------------------------------------------

def text_display(content, **kw):
    """Text Display (type 10) — markdown or plain text block.

    Parameters
    ----------
    content : str
        Text content (supports markdown).
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["text_display"], "content": content}
    comp.update(kw)
    return comp


def media_gallery(*items, **kw):
    """Media Gallery (type 12) — grid of images/videos.

    Parameters
    ----------
    *items : dict
        Media items, each with at least ``{"media": unfurl_media(url)}``.
        Optional keys: ``description``, ``spoiler``.
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["media_gallery"], "items": list(items)}
    comp.update(kw)
    return comp


def file(url, *, spoiler=False, **kw):
    """File (type 13) — attached file display.

    Parameters
    ----------
    url : str
        URL of the file.
    spoiler : bool
        Whether the file is hidden behind a spoiler.
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["file"], "file": unfurl_media(url)}
    if spoiler:
        comp["spoiler"] = True
    comp.update(kw)
    return comp


def thumbnail(media, *, description=None, spoiler=False, **kw):
    """Thumbnail (type 11) — used inside ``section`` as an accessory.

    Parameters
    ----------
    media : dict
        ``unfurl_media(url)`` object.
    description : str, optional
        Alt-text / description.
    spoiler : bool
        Whether the thumbnail is hidden behind a spoiler.
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["thumbnail"], "media": media}
    if description is not None:
        comp["description"] = description
    if spoiler:
        comp["spoiler"] = True
    comp.update(kw)
    return comp


# ---------------------------------------------------------------------------
# Interactive Components
# ---------------------------------------------------------------------------

def button(label, *, custom_id=None, style="primary", url=None, emoji=None,
           disabled=False, sku_id=None, **kw):
    """Button (type 2) — clickable button.

    Parameters
    ----------
    label : str
        Button text (max 80 chars).
    custom_id : str, optional
        Unique identifier for interaction handling (required for non-link/premium).
    style : str or int
        One of ``"primary"``, ``"secondary"``, ``"success"``, ``"danger"``,
        ``"link"``, ``"premium"`` or the integer value directly.
    url : str, optional
        URL for link-style buttons (style must be ``"link"``).
    emoji : dict, optional
        Partial emoji object ``{"name": "...", "id": "...", "animated": ...}``.
    disabled : bool
        Whether the button is disabled.
    sku_id : str, optional
        SKU ID for premium-style buttons.
    **kw
        Extra fields.
    """
    style_val = BUTTON_STYLES.get(style, style) if isinstance(style, str) else style
    comp = {"type": COMPONENT_TYPES["button"], "style": style_val}
    if label:
        comp["label"] = label
    if custom_id is not None:
        comp["custom_id"] = custom_id
    if url is not None:
        comp["url"] = url
    if emoji is not None:
        comp["emoji"] = emoji
    if disabled:
        comp["disabled"] = True
    if sku_id is not None:
        comp["sku_id"] = sku_id
    comp.update(kw)
    return comp


def string_select(custom_id, options, *, placeholder=None, min_values=None,
                  max_values=None, disabled=False, **kw):
    """String Select (type 3) — dropdown from predefined options.

    Parameters
    ----------
    custom_id : str
        Unique identifier for interaction handling.
    options : list[dict]
        List of ``select_option(...)`` dicts (max 25).
    placeholder : str, optional
        Placeholder text when nothing is selected.
    min_values : int, optional
        Minimum number of selections (default 1).
    max_values : int, optional
        Maximum number of selections (default 1).
    disabled : bool
        Whether the select is disabled.
    **kw
        Extra fields.
    """
    comp = {
        "type": COMPONENT_TYPES["string_select"],
        "custom_id": custom_id,
        "options": options,
    }
    if placeholder is not None:
        comp["placeholder"] = placeholder
    if min_values is not None:
        comp["min_values"] = min_values
    if max_values is not None:
        comp["max_values"] = max_values
    if disabled:
        comp["disabled"] = True
    comp.update(kw)
    return comp


def _auto_select(type_key, custom_id, *, placeholder=None, min_values=None,
                 max_values=None, default_values=None, disabled=False, **kw):
    """Internal: build an auto-populated select (user/role/mentionable/channel)."""
    comp = {
        "type": COMPONENT_TYPES[type_key],
        "custom_id": custom_id,
    }
    if placeholder is not None:
        comp["placeholder"] = placeholder
    if min_values is not None:
        comp["min_values"] = min_values
    if max_values is not None:
        comp["max_values"] = max_values
    if default_values is not None:
        comp["default_values"] = default_values
    if disabled:
        comp["disabled"] = True
    comp.update(kw)
    return comp


def user_select(custom_id, **kw):
    """User Select (type 5) — user picker."""
    return _auto_select("user_select", custom_id, **kw)


def role_select(custom_id, **kw):
    """Role Select (type 6) — role picker."""
    return _auto_select("role_select", custom_id, **kw)


def mentionable_select(custom_id, **kw):
    """Mentionable Select (type 7) — user + role picker."""
    return _auto_select("mentionable_select", custom_id, **kw)


def channel_select(custom_id, *, channel_types=None, **kw):
    """Channel Select (type 8) — channel picker.

    Parameters
    ----------
    custom_id : str
        Unique identifier.
    channel_types : list[int], optional
        Filter to specific channel types (e.g. ``[0]`` for text channels).
    **kw
        Passed to ``_auto_select``.
    """
    comp = _auto_select("channel_select", custom_id, **kw)
    if channel_types is not None:
        comp["channel_types"] = channel_types
    return comp


def text_input(custom_id, label, *, style="short", placeholder=None,
               min_length=None, max_length=None, required=True, value=None, **kw):
    """Text Input (type 4) — modal text input field.

    Parameters
    ----------
    custom_id : str
        Unique identifier.
    label : str
        Label displayed above the input.
    style : str or int
        ``"short"`` (single-line) or ``"paragraph"`` (multi-line).
    placeholder : str, optional
        Placeholder text.
    min_length : int, optional
        Minimum input length (0-4000).
    max_length : int, optional
        Maximum input length (1-4000).
    required : bool
        Whether the field is required (default ``True``).
    value : str, optional
        Pre-filled value.
    **kw
        Extra fields.
    """
    style_val = TEXT_INPUT_STYLES.get(style, style) if isinstance(style, str) else style
    comp = {
        "type": COMPONENT_TYPES["text_input"],
        "custom_id": custom_id,
        "label": label,
        "style": style_val,
    }
    if placeholder is not None:
        comp["placeholder"] = placeholder
    if min_length is not None:
        comp["min_length"] = min_length
    if max_length is not None:
        comp["max_length"] = max_length
    if not required:
        comp["required"] = False
    if value is not None:
        comp["value"] = value
    comp.update(kw)
    return comp


# ---------------------------------------------------------------------------
# Modal Components
# ---------------------------------------------------------------------------

def label(label_text, component, *, description=None, **kw):
    """Label (type 18) — wraps a modal component with label text.

    Parameters
    ----------
    label_text : str
        Label displayed above the component (max 45 chars).
    component : dict
        The child component (text_input, select, file_upload, etc.).
    description : str, optional
        Additional description (max 100 chars).
    **kw
        Extra fields (e.g. ``id``).
    """
    comp = {"type": COMPONENT_TYPES["label"], "label": label_text, "component": component}
    if description is not None:
        comp["description"] = description
    comp.update(kw)
    return comp


def file_upload(custom_id, *, min_values=None, max_values=None, required=True, **kw):
    """File Upload (type 19) — file upload field in modals.

    Parameters
    ----------
    custom_id : str
        Unique identifier (1-100 chars).
    min_values : int, optional
        Minimum files (0-10, default 1).
    max_values : int, optional
        Maximum files (1-10, default 1).
    required : bool
        Whether upload is required (default ``True``).
    **kw
        Extra fields.
    """
    comp = {"type": COMPONENT_TYPES["file_upload"], "custom_id": custom_id}
    if min_values is not None:
        comp["min_values"] = min_values
    if max_values is not None:
        comp["max_values"] = max_values
    if not required:
        comp["required"] = False
    comp.update(kw)
    return comp


def radio_option(label, value, *, description=None, default=False):
    """Build an option for ``radio_group``.

    Parameters
    ----------
    label : str
        User-facing text (max 100 chars).
    value : str
        Dev-defined value (max 100 chars).
    description : str, optional
        Additional description (max 100 chars).
    default : bool
        Whether selected by default.
    """
    opt = {"label": label, "value": value}
    if description is not None:
        opt["description"] = description
    if default:
        opt["default"] = True
    return opt


def radio_group(custom_id, options, *, required=True, **kw):
    """Radio Group (type 21) — single-choice options in modals.

    Parameters
    ----------
    custom_id : str
        Unique identifier (1-100 chars).
    options : list[dict]
        ``radio_option(...)`` dicts (2-10).
    required : bool
        Whether a selection is required (default ``True``).
    **kw
        Extra fields.
    """
    comp = {
        "type": COMPONENT_TYPES["radio_group"],
        "custom_id": custom_id,
        "options": options,
    }
    if not required:
        comp["required"] = False
    comp.update(kw)
    return comp


def checkbox_option(label, value, *, description=None, default=False):
    """Build an option for ``checkbox_group``.

    Parameters
    ----------
    label : str
        User-facing text (max 100 chars).
    value : str
        Dev-defined value (max 100 chars).
    description : str, optional
        Additional description (max 100 chars).
    default : bool
        Whether selected by default.
    """
    opt = {"label": label, "value": value}
    if description is not None:
        opt["description"] = description
    if default:
        opt["default"] = True
    return opt


def checkbox_group(custom_id, options, *, min_values=None, max_values=None,
                   required=True, **kw):
    """Checkbox Group (type 22) — multi-select checkboxes in modals.

    Parameters
    ----------
    custom_id : str
        Unique identifier (1-100 chars).
    options : list[dict]
        ``checkbox_option(...)`` dicts (1-10).
    min_values : int, optional
        Minimum selections (0-10, default 1).
    max_values : int, optional
        Maximum selections (1-10).
    required : bool
        Whether selecting is required (default ``True``).
    **kw
        Extra fields.
    """
    comp = {
        "type": COMPONENT_TYPES["checkbox_group"],
        "custom_id": custom_id,
        "options": options,
    }
    if min_values is not None:
        comp["min_values"] = min_values
    if max_values is not None:
        comp["max_values"] = max_values
    if not required:
        comp["required"] = False
    comp.update(kw)
    return comp


def checkbox(custom_id, *, default=False, **kw):
    """Checkbox (type 23) — single yes/no checkbox in modals.

    Parameters
    ----------
    custom_id : str
        Unique identifier (1-100 chars).
    default : bool
        Whether checked by default.
    **kw
        Extra fields.
    """
    comp = {"type": COMPONENT_TYPES["checkbox"], "custom_id": custom_id}
    if default:
        comp["default"] = True
    comp.update(kw)
    return comp


# ---------------------------------------------------------------------------
# Message-Level Builders
# ---------------------------------------------------------------------------

def components_v2_message(*components, **kw):
    """Build a full message payload with the ``IS_COMPONENTS_V2`` flag.

    Parameters
    ----------
    *components : dict
        Top-level components (typically ``container(...)`` or ``action_row(...)``).
    **kw
        Extra message-level fields (e.g. ``content``, ``embeds``, ``allowed_mentions``).

    Returns
    -------
    dict
        Message payload ready for ``send_webhook_message(components=...)``
        or direct API use.
    """
    payload = {"components": list(components), "flags": IS_COMPONENTS_V2}
    payload.update(kw)
    # Merge caller-supplied flags with IS_COMPONENTS_V2
    if "flags" in kw:
        payload["flags"] = kw["flags"] | IS_COMPONENTS_V2
    return payload


def modal_response(custom_id, title, *components):
    """Build a Type 9 (MODAL) interaction response.

    Return this from a command or component handler to pop up a modal dialog.

    Parameters
    ----------
    custom_id : str
        Unique identifier for the modal (used to match ``register_modal_handler``).
    title : str
        Modal title (max 45 chars).
    *components : dict
        ``action_row(text_input(...))`` components (max 5 rows).

    Returns
    -------
    dict
        Dict with ``_modal: True`` sentinel, consumed by the interaction handler.
    """
    return {
        "_modal": True,
        "custom_id": custom_id,
        "title": title,
        "components": list(components),
    }
