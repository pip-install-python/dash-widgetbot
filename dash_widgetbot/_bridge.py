"""Command helper functions for the store bridge.

Every function returns a dict intended for the command dcc.Store.
Each dict includes ``_ts`` (time.time()) to prevent Dash store
deduplication -- clicking "Toggle" twice must fire twice.
"""

import time


def crate_toggle(is_open=None, prefix=""):
    """Toggle the Crate open/closed. None = toggle, True = open, False = close."""
    cmd = {"action": "toggle", "_ts": time.time(), "_prefix": prefix}
    if is_open is not None:
        cmd["value"] = is_open
    return cmd


def crate_notify(content, timeout=None, avatar=None, prefix=""):
    """Show a notification bubble on the Crate button."""
    if isinstance(content, str) and timeout is None and avatar is None:
        data = content
    else:
        data = {"content": content} if isinstance(content, str) else dict(content)
        if timeout is not None:
            data["timeout"] = timeout
        if avatar is not None:
            data["avatar"] = avatar
    return {"action": "notify", "data": data, "_ts": time.time(), "_prefix": prefix}


def crate_navigate(channel, guild=None, prefix=""):
    """Navigate to a Discord channel (and optionally guild)."""
    if guild:
        data = {"guild": guild, "channel": channel}
    else:
        data = channel
    return {"action": "navigate", "data": data, "_ts": time.time(), "_prefix": prefix}


def crate_hide(prefix=""):
    """Hide the entire Crate (button + widget + notifications)."""
    return {"action": "hide", "_ts": time.time(), "_prefix": prefix}


def crate_show(prefix=""):
    """Restore a previously hidden Crate."""
    return {"action": "show", "_ts": time.time(), "_prefix": prefix}


def crate_update_options(prefix="", **opts):
    """Merge new options into the Crate config at runtime."""
    return {"action": "update_options", "data": opts, "_ts": time.time(), "_prefix": prefix}


def crate_send_message(message, channel=None, prefix=""):
    """Send a message to Discord via the embed API."""
    if channel:
        data = {"channel": channel, "message": message}
    else:
        data = message
    return {"action": "send_message", "data": data, "_ts": time.time(), "_prefix": prefix}


def crate_login(prefix=""):
    """Request user login via the embed API."""
    return {"action": "login", "_ts": time.time(), "_prefix": prefix}


def crate_logout(prefix=""):
    """Log the user out via the embed API."""
    return {"action": "logout", "_ts": time.time(), "_prefix": prefix}


def crate_set_color(variable, value, prefix=""):
    """Set an embed color variable (background, accent, or primary)."""
    return {"action": "color", "data": [variable, value], "_ts": time.time(), "_prefix": prefix}


def crate_emit(event, data=None, prefix=""):
    """Send a raw embed-api command."""
    return {"action": "emit", "event": event, "data": data, "_ts": time.time(), "_prefix": prefix}


def emit_command(command_dict, namespace=None):
    """Emit a crate command via Socket.IO if available. Returns True if emitted.

    Server-side use only (background threads, webhook handlers).
    Client-side commands still flow through dcc.Store.
    """
    from ._transport import is_socketio_available, get_socketio
    from ._constants import SIO_NAMESPACE_CRATE, SIO_EVENT_CRATE_COMMAND
    if not is_socketio_available():
        return False
    get_socketio().emit(
        SIO_EVENT_CRATE_COMMAND,
        command_dict,
        namespace=namespace or SIO_NAMESPACE_CRATE,
    )
    return True


def emit_progress(event_dict, namespace=None):
    """Emit a gen_progress event via Socket.IO. Returns True if emitted."""
    from ._transport import is_socketio_available, get_socketio
    from ._constants import SIO_NAMESPACE_GEN, SIO_EVENT_GEN_PROGRESS
    if not is_socketio_available():
        return False
    get_socketio().emit(
        SIO_EVENT_GEN_PROGRESS,
        event_dict,
        namespace=namespace or SIO_NAMESPACE_GEN,
    )
    return True
