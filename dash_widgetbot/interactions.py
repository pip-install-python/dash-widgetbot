"""Discord Interactions endpoint for HTTP-only slash commands.

Registers a Dash hooks route at ``/api/discord/interactions`` that handles:
- PING (type 1) -- required for Discord endpoint verification
- APPLICATION_COMMAND (type 2) -- deferred response with follow-up via webhook
- MESSAGE_COMPONENT (type 3) -- button clicks, select changes
- MODAL_SUBMIT (type 5) -- modal form submissions
"""

import json
import os
import threading
import time

import requests
from dash import hooks

from ._constants import IS_COMPONENTS_V2

_command_handlers = {}
_component_handlers = {}
_modal_handlers = {}
_ephemeral_commands: set = set()

_INTERACTIONS_PATH = "/api/discord/interactions"


def _discord_request(method, url, *, max_retries=2, backoff=1.0, **kwargs):
    """Discord API request with retry on transient SSL/connection errors."""
    kwargs.setdefault("timeout", 15)
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return getattr(requests, method)(url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
                print(f"[dash-widgetbot] Discord API retry {attempt+1}/{max_retries}: {exc}")
            else:
                raise


def _detect_ngrok_url():
    """Query the local ngrok agent API for the current public HTTPS URL.

    Returns
    -------
    str or None
        The public HTTPS URL, e.g. ``https://xxxx.ngrok-free.app``, or
        ``None`` if ngrok is not running.
    """
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
        if resp.ok:
            for tunnel in resp.json().get("tunnels", []):
                url = tunnel.get("public_url", "")
                if url.startswith("https://"):
                    return url.rstrip("/")
    except Exception:
        pass
    return None


def _post_loading_channel_message(channel_id: str, content: str) -> str | None:
    """Post a temporary public loading message to a channel.

    Called from the background handler thread *before* running the command
    so that WidgetBot (which reads channel history, not ephemeral messages)
    shows the user immediate feedback.

    Returns
    -------
    str or None
        Discord message ID, or ``None`` on failure.
    """
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token or not channel_id:
        return None
    try:
        resp = _discord_request(
            "post",
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json={"content": content},
        )
        if resp.ok:
            msg_id = resp.json().get("id")
            print(f"[dash-widgetbot] Loading message posted (id={msg_id})")
            return msg_id
        print(f"[dash-widgetbot] Loading message failed ({resp.status_code}): {resp.text[:100]}")
    except Exception as exc:
        print(f"[dash-widgetbot] Loading message exception: {exc}")
    return None


def _delete_channel_message(channel_id: str, message_id: str) -> None:
    """Delete a channel message by ID (fire-and-forget in a daemon thread).

    Used to remove the temporary loading message once the real response
    has been posted to the channel.  Runs non-blocking with no retries
    so it never delays the main handler thread.
    """
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token or not channel_id or not message_id:
        return

    def _do_delete():
        try:
            resp = _discord_request(
                "delete",
                f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
                max_retries=0,
                headers={"Authorization": f"Bot {bot_token}"},
                timeout=5,
            )
            if resp.ok or resp.status_code == 204:
                print(f"[dash-widgetbot] Loading message deleted (id={message_id})")
            else:
                print(f"[dash-widgetbot] Loading message delete failed ({resp.status_code})")
        except Exception as exc:
            print(f"[dash-widgetbot] Loading message delete exception: {exc}")

    threading.Thread(target=_do_delete, daemon=True).start()


def _edit_channel_message(channel_id: str, message_id: str, content: str) -> bool:
    """Edit an existing channel message. Returns True on success."""
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token or not channel_id or not message_id:
        return False
    try:
        resp = _discord_request(
            "patch",
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json={"content": content},
        )
        return resp.ok
    except Exception as exc:
        print(f"[dash-widgetbot] Edit channel message failed: {exc}")
        return False


_AI_COMMANDS = frozenset({"ai", "gen", "ask"})


def sync_discord_endpoint(*, base_url=None, bot_token=None, application_id=None):
    """Detect the current public URL and update Discord's Interactions Endpoint.

    Call this at app startup (after ``add_discord_interactions()``) to
    automatically keep the Discord endpoint in sync with an ngrok tunnel
    or custom domain.

    Resolution order for *base_url*:

    1. Explicit ``base_url`` parameter
    2. ``INTERACTIONS_URL`` env var (full URL **or** just the base domain)
    3. Auto-detected ngrok tunnel URL

    Parameters
    ----------
    base_url : str, optional
        Public base URL (e.g. ``https://example.com``).
    bot_token : str, optional
        Discord bot token.  Falls back to ``DISCORD_BOT_TOKEN``.
    application_id : str, optional
        Discord application ID.  Falls back to ``DISCORD_APPLICATION_ID``.

    Returns
    -------
    dict
        ``{"success": bool, "endpoint_url": str | None, "error": str | None}``
    """
    token = bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
    app_id = application_id or os.getenv("DISCORD_APPLICATION_ID", "")

    if not token or not app_id:
        return {
            "success": False,
            "endpoint_url": None,
            "error": "DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID are required",
        }

    # Resolve the base URL
    url = base_url or os.getenv("INTERACTIONS_URL", "")
    source = "parameter" if base_url else "INTERACTIONS_URL env"

    if not url:
        url = _detect_ngrok_url()
        source = "ngrok auto-detect"

    if not url:
        print("[dash-widgetbot] No public URL found (no ngrok, no INTERACTIONS_URL)")
        return {
            "success": False,
            "endpoint_url": None,
            "error": "No public URL found. Start ngrok or set INTERACTIONS_URL.",
        }

    # Build the full endpoint URL
    if _INTERACTIONS_PATH in url:
        endpoint_url = url
    else:
        endpoint_url = url.rstrip("/") + _INTERACTIONS_PATH

    # Check what Discord currently has
    try:
        get_resp = _discord_request(
            "get",
            f"https://discord.com/api/v10/applications/@me",
            headers={"Authorization": f"Bot {token}"},
        )
        if get_resp.ok:
            current = get_resp.json().get("interactions_endpoint_url", "")
            if current == endpoint_url:
                print(f"[dash-widgetbot] Endpoint already up to date: {endpoint_url}")
                return {"success": True, "endpoint_url": endpoint_url, "error": None}
    except Exception:
        pass  # Proceed to PATCH anyway

    # Update Discord
    print(f"[dash-widgetbot] Updating interactions endpoint ({source}): {endpoint_url}")
    try:
        resp = _discord_request(
            "patch",
            f"https://discord.com/api/v10/applications/@me",
            headers={"Authorization": f"Bot {token}"},
            json={"interactions_endpoint_url": endpoint_url},
        )
        if resp.ok:
            print(f"[dash-widgetbot] Endpoint updated successfully!")
            return {"success": True, "endpoint_url": endpoint_url, "error": None}
        else:
            error = resp.text[:200]
            print(f"[dash-widgetbot] Endpoint update failed ({resp.status_code}): {error}")
            return {"success": False, "endpoint_url": endpoint_url, "error": error}
    except Exception as exc:
        print(f"[dash-widgetbot] Endpoint update exception: {exc}")
        return {"success": False, "endpoint_url": endpoint_url, "error": str(exc)}


def verify_signature(public_key_hex, signature, timestamp, body):
    """Verify a Discord interaction request signature (Ed25519).

    Parameters
    ----------
    public_key_hex : str
        Hex-encoded Ed25519 public key from the Discord Developer Portal.
    signature : str
        ``X-Signature-Ed25519`` header value.
    timestamp : str
        ``X-Signature-Timestamp`` header value.
    body : bytes
        Raw request body.

    Returns
    -------
    bool
    """
    try:
        from nacl.signing import VerifyKey
    except ImportError:
        raise ImportError(
            "PyNaCl is required for signature verification. "
            "Install it with: pip install PyNaCl>=1.5.0"
        )
    try:
        vk = VerifyKey(bytes.fromhex(public_key_hex))
        vk.verify(timestamp.encode() + body, bytes.fromhex(signature))
        return True
    except Exception:
        return False


def register_command(name, handler, *, ephemeral=False):
    """Register a handler for a slash command.

    Parameters
    ----------
    name : str
        Command name (e.g. ``"ask"``).
    handler : callable
        ``handler(interaction_data) -> str | dict | None``
        - ``str`` — sent as ``{"content": str}``
        - ``dict`` — sent as-is (may include ``components``, ``embeds``, ``flags``)
        - ``dict`` with ``_modal: True`` — sends a Type 9 MODAL response
        - ``None`` — acknowledgement only
        Called in a background thread; may be slow (AI calls, etc.).
    ephemeral : bool, optional
        If ``True``, the initial deferred response is ephemeral (flags=64),
        meaning only the invoker sees "thinking...". The follow-up PATCH
        is also private. Useful for commands that post to the channel
        themselves so WidgetBot doesn't show a duplicate.
    """
    _command_handlers[name] = handler
    if ephemeral:
        _ephemeral_commands.add(name)


def register_component_handler(custom_id, handler):
    """Register a handler for a message component interaction (button click, select change).

    Parameters
    ----------
    custom_id : str
        The ``custom_id`` of the button or select component.
    handler : callable
        ``handler(interaction) -> str | dict | None``
        - ``str`` — sent as ``{"content": str}``
        - ``dict`` — sent as-is (may include ``components``, ``embeds``, ``flags``)
        - ``dict`` with ``_modal: True`` — sends a Type 9 MODAL response
        - ``None`` — acknowledgement only (no follow-up message)
    """
    _component_handlers[custom_id] = handler


def register_modal_handler(custom_id, handler):
    """Register a handler for a modal form submission.

    Parameters
    ----------
    custom_id : str
        The ``custom_id`` of the modal.
    handler : callable
        ``handler(interaction) -> str | dict | None``
        - ``str`` — sent as ``{"content": str}``
        - ``dict`` — sent as-is
        - ``None`` — acknowledgement only
    """
    _modal_handlers[custom_id] = handler


def _build_followup_payload(result):
    """Convert a handler result to a JSON-serializable follow-up payload.

    Parameters
    ----------
    result : str | dict | None
        Handler return value.

    Returns
    -------
    dict or None
        Payload for PATCH, or ``None`` if no follow-up needed.
    """
    if result is None:
        return None
    if isinstance(result, str):
        return {"content": result}
    if isinstance(result, dict):
        # Strip internal sentinel — _modal should have been handled before this
        payload = {k: v for k, v in result.items() if not k.startswith("_")}
        # Auto-set IS_COMPONENTS_V2 flag when components are present
        if "components" in payload and "flags" not in payload:
            payload["flags"] = IS_COMPONENTS_V2
        return payload
    return {"content": str(result)}


def _send_followup(application_id, interaction_token, result):
    """PATCH the deferred response with actual content.

    Parameters
    ----------
    application_id : str
    interaction_token : str
    result : str | dict | None
        Handler return value.
    """
    payload = _build_followup_payload(result)
    if payload is None:
        return

    url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{application_id}/{interaction_token}/messages/@original"
    )
    params = {}
    if "components" in payload:
        params["with_components"] = "true"

    print(f"[dash-widgetbot] PATCHing follow-up to {url[:80]}...")
    try:
        resp = requests.patch(url, json=payload, params=params, timeout=15)
        print(f"[dash-widgetbot] Follow-up response: {resp.status_code}")
        if not resp.ok:
            print(f"[dash-widgetbot] Follow-up failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as exc:
        print(f"[dash-widgetbot] Follow-up exception: {exc}")


def _send_followup_with_files(application_id, interaction_token, payload, *, files):
    """PATCH a deferred response with both JSON payload and file attachments.

    Uses ``multipart/form-data`` with ``payload_json`` + file parts so that
    Discord can process Components V2 messages that reference
    ``attachment://filename`` URLs.

    Parameters
    ----------
    application_id : str
    interaction_token : str
    payload : dict
        Message payload (components, flags, etc.).  An ``attachments``
        metadata array is added automatically.
    files : list[tuple[str, bytes, str]]
        Each entry is ``(filename, data_bytes, content_type)``.
    """
    url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{application_id}/{interaction_token}/messages/@original"
    )
    params = {}
    if "components" in payload:
        params["with_components"] = "true"

    # Build attachments metadata
    attachments = []
    multipart_files = {}
    for idx, (filename, data, content_type) in enumerate(files):
        attachments.append({"id": idx, "filename": filename})
        multipart_files[f"files[{idx}]"] = (filename, data, content_type)

    payload["attachments"] = attachments

    print(f"[dash-widgetbot] PATCHing multipart follow-up ({len(files)} file(s))...")
    try:
        resp = requests.patch(
            url,
            data={"payload_json": json.dumps(payload)},
            files=multipart_files,
            params=params,
            timeout=30,
        )
        print(f"[dash-widgetbot] Multipart follow-up response: {resp.status_code}")
        if not resp.ok:
            print(f"[dash-widgetbot] Multipart failed ({resp.status_code}): {resp.text[:300]}")
            # Retry without files as fallback
            print("[dash-widgetbot] Retrying as JSON-only (no files)...")
            payload.pop("attachments", None)
            fallback = requests.patch(url, json=payload, params=params, timeout=15)
            print(f"[dash-widgetbot] Fallback response: {fallback.status_code}")
    except Exception as exc:
        print(f"[dash-widgetbot] Multipart follow-up exception: {exc}")


def _send_modal_response(application_id, interaction_id, interaction_token, modal_dict):
    """Send a Type 9 (MODAL) interaction response via the callback URL.

    Parameters
    ----------
    application_id : str
    interaction_id : str
    interaction_token : str
    modal_dict : dict
        Must contain ``custom_id``, ``title``, ``components``.
    """
    url = f"https://discord.com/api/v10/interactions/{interaction_id}/{interaction_token}/callback"
    payload = {
        "type": 9,
        "data": {
            "custom_id": modal_dict["custom_id"],
            "title": modal_dict["title"],
            "components": modal_dict["components"],
        },
    }
    print(f"[dash-widgetbot] Sending modal response for {modal_dict['custom_id']}...")
    try:
        resp = requests.post(url, json=payload, timeout=15)
        print(f"[dash-widgetbot] Modal response: {resp.status_code}")
        if not resp.ok:
            print(f"[dash-widgetbot] Modal failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as exc:
        print(f"[dash-widgetbot] Modal exception: {exc}")


def _handle_command(interaction, application_id):
    """Process a slash command in a daemon thread."""
    data = interaction.get("data", {})
    name = data.get("name", "")
    token = interaction.get("token", "")
    channel_id = interaction.get("channel_id", "")

    print(f"[dash-widgetbot] Handling command: /{name} (app_id={application_id})")

    handler = _command_handlers.get(name)
    if handler is None:
        print(f"[dash-widgetbot] No handler for /{name}, registered: {list(_command_handlers.keys())}")
        _send_followup(application_id, token, f"Unknown command: `/{name}`")
        return

    # Inject progress tracker for AI commands
    tracker = None
    if name in _AI_COMMANDS:
        from .progress import ProgressTracker, EphemeralSink, SocketIOSink
        sinks = [SocketIOSink()]
        if name in _ephemeral_commands:
            sinks.append(EphemeralSink(application_id, token))
        tracker = ProgressTracker(sinks=sinks)
        interaction["_progress_tracker"] = tracker

    try:
        result = handler(interaction)
        # Check for modal response
        if isinstance(result, dict) and result.get("_modal"):
            _send_modal_response(
                application_id,
                interaction.get("id", ""),
                token,
                result,
            )
            return
        # Check for file attachments (_files sentinel)
        if isinstance(result, dict) and result.get("_files"):
            files = result.pop("_files")
            payload = _build_followup_payload(result)
            if payload is not None:
                _send_followup_with_files(application_id, token, payload, files=files)
            return
        _send_followup(application_id, token, result)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        _send_followup(application_id, token, f"Error: {exc}")
    finally:
        if tracker:
            tracker.close()


def _handle_component(interaction, application_id):
    """Process a component interaction (button click, select change) in a daemon thread."""
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    token = interaction.get("token", "")

    print(f"[dash-widgetbot] Handling component: {custom_id} (app_id={application_id})")

    handler = _component_handlers.get(custom_id)
    if handler is None:
        print(f"[dash-widgetbot] No handler for component {custom_id}")
        return

    try:
        result = handler(interaction)
        if isinstance(result, dict) and result.get("_modal"):
            _send_modal_response(
                application_id,
                interaction.get("id", ""),
                token,
                result,
            )
            return
        _send_followup(application_id, token, result)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        _send_followup(application_id, token, f"Error: {exc}")


def _handle_modal(interaction, application_id):
    """Process a modal submission in a daemon thread."""
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    token = interaction.get("token", "")

    print(f"[dash-widgetbot] Handling modal: {custom_id} (app_id={application_id})")

    handler = _modal_handlers.get(custom_id)
    if handler is None:
        print(f"[dash-widgetbot] No handler for modal {custom_id}")
        return

    try:
        result = handler(interaction)
        _send_followup(application_id, token, result)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        _send_followup(application_id, token, f"Error: {exc}")


def add_discord_interactions(*, public_key=None, application_id=None):
    """Register the ``/api/discord/interactions`` route via Dash hooks.

    Parameters
    ----------
    public_key : str, optional
        Hex-encoded Ed25519 public key. Falls back to ``DISCORD_PUBLIC_KEY``.
    application_id : str, optional
        Discord application ID. Falls back to ``DISCORD_APPLICATION_ID``.
    """
    pk = public_key or os.getenv("DISCORD_PUBLIC_KEY", "")
    app_id = application_id or os.getenv("DISCORD_APPLICATION_ID", "")

    if not pk:
        print("[dash-widgetbot] DISCORD_PUBLIC_KEY not set -- interactions disabled")
        return
    if not app_id:
        print("[dash-widgetbot] DISCORD_APPLICATION_ID not set -- interactions disabled")
        return

    @hooks.route("api/discord/interactions", methods=("GET", "POST"))
    def interactions_route():
        """Handle incoming Discord interactions."""
        from flask import Response, request

        if request.method != "POST":
            return Response("Method Not Allowed", status=405)

        try:
            # Verify signature
            signature = request.headers.get("X-Signature-Ed25519", "")
            timestamp = request.headers.get("X-Signature-Timestamp", "")
            body = request.get_data()

            print(f"[dash-widgetbot] Interaction received ({len(body)} bytes)")

            verified = verify_signature(pk, signature, timestamp, body)
            if not verified:
                print("[dash-widgetbot] Signature verification: FAILED")
                return Response("Invalid signature", status=401)
            print("[dash-widgetbot] Signature verification: OK")

            payload = json.loads(body)
            interaction_type = payload.get("type")
            print(f"[dash-widgetbot] Interaction type: {interaction_type}")

            # Type 1: PING -- required for endpoint verification
            if interaction_type == 1:
                print("[dash-widgetbot] Responding to PING")
                return Response(
                    json.dumps({"type": 1}),
                    status=200,
                    content_type="application/json",
                )

            # Type 2: APPLICATION_COMMAND -- defer + background follow-up
            if interaction_type == 2:
                data = payload.get("data", {})
                name = data.get("name", "")
                print(f"[dash-widgetbot] Command: /{name}")

                t = threading.Thread(
                    target=_handle_command,
                    args=(payload, app_id),
                    daemon=True,
                )
                t.start()

                is_ephemeral = name in _ephemeral_commands
                deferred = {"type": 5, "data": {"flags": 64}} if is_ephemeral else {"type": 5}
                print(f"[dash-widgetbot] Returning deferred response (type 5, ephemeral={is_ephemeral}) for /{name}")
                return Response(
                    json.dumps(deferred),
                    status=200,
                    content_type="application/json",
                )

            # Type 3: MESSAGE_COMPONENT -- button clicks, select changes
            if interaction_type == 3:
                custom_id = payload.get("data", {}).get("custom_id", "")
                print(f"[dash-widgetbot] Component interaction: {custom_id}")
                handler = _component_handlers.get(custom_id)
                if handler:
                    t = threading.Thread(
                        target=_handle_component,
                        args=(payload, app_id),
                        daemon=True,
                    )
                    t.start()
                # Type 6: DEFERRED_UPDATE_MESSAGE -- ack without "thinking"
                return Response(
                    json.dumps({"type": 6}),
                    status=200,
                    content_type="application/json",
                )

            # Type 5: MODAL_SUBMIT
            if interaction_type == 5:
                custom_id = payload.get("data", {}).get("custom_id", "")
                print(f"[dash-widgetbot] Modal submission: {custom_id}")
                handler = _modal_handlers.get(custom_id)
                if handler:
                    t = threading.Thread(
                        target=_handle_modal,
                        args=(payload, app_id),
                        daemon=True,
                    )
                    t.start()
                # Type 6: DEFERRED_UPDATE_MESSAGE
                return Response(
                    json.dumps({"type": 6}),
                    status=200,
                    content_type="application/json",
                )

            print(f"[dash-widgetbot] Unknown interaction type: {interaction_type}")
            return Response(
                json.dumps({"type": 1}),
                status=200,
                content_type="application/json",
            )

        except Exception as exc:
            print(f"[dash-widgetbot] FATAL: Interaction route crashed: {exc}")
            import traceback
            traceback.print_exc()
            # Return deferred response as fallback so Discord doesn't timeout
            return Response(
                json.dumps({"type": 5}),
                status=200,
                content_type="application/json",
            )
