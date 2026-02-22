"""Discord Interactions endpoint for HTTP-only slash commands.

Registers a Dash hooks route at ``/api/discord/interactions`` that handles:
- PING (type 1) -- required for Discord endpoint verification
- APPLICATION_COMMAND (type 2) -- deferred response with follow-up via webhook
"""

import json
import os
import threading
import time

import requests
from dash import hooks

_command_handlers = {}


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


def register_command(name, handler):
    """Register a handler for a slash command.

    Parameters
    ----------
    name : str
        Command name (e.g. ``"ask"``).
    handler : callable
        ``handler(interaction_data) -> str`` that returns the response text.
        Called in a background thread; may be slow (AI calls, etc.).
    """
    _command_handlers[name] = handler


def _send_followup(application_id, interaction_token, content):
    """PATCH the deferred response with actual content."""
    url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{application_id}/{interaction_token}/messages/@original"
    )
    print(f"[dash-widgetbot] PATCHing follow-up to {url[:80]}...")
    try:
        resp = requests.patch(url, json={"content": content}, timeout=15)
        print(f"[dash-widgetbot] Follow-up response: {resp.status_code}")
        if not resp.ok:
            print(f"[dash-widgetbot] Follow-up failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as exc:
        print(f"[dash-widgetbot] Follow-up exception: {exc}")


def _handle_command(interaction, application_id):
    """Process a slash command in a daemon thread."""
    data = interaction.get("data", {})
    name = data.get("name", "")
    token = interaction.get("token", "")

    print(f"[dash-widgetbot] Handling command: /{name} (app_id={application_id})")

    handler = _command_handlers.get(name)
    if handler is None:
        print(f"[dash-widgetbot] No handler for /{name}, registered: {list(_command_handlers.keys())}")
        _send_followup(application_id, token, f"Unknown command: `/{name}`")
        return

    try:
        result = handler(interaction)
        print(f"[dash-widgetbot] Handler returned: {result[:100] if result else '(empty)'}...")
        _send_followup(application_id, token, result or "(no response)")
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

    @hooks.route("/api/discord/interactions", methods=("GET", "POST"))
    def interactions_route():
        """Handle incoming Discord interactions."""
        from flask import Response, request

        if request.method != "POST":
            return Response("Method Not Allowed", status=405)

        # Verify signature
        signature = request.headers.get("X-Signature-Ed25519", "")
        timestamp = request.headers.get("X-Signature-Timestamp", "")
        body = request.get_data()

        if not verify_signature(pk, signature, timestamp, body):
            return Response("Invalid signature", status=401)

        payload = json.loads(body)
        interaction_type = payload.get("type")

        # Type 1: PING -- required for endpoint verification
        if interaction_type == 1:
            return Response(
                json.dumps({"type": 1}),
                status=200,
                content_type="application/json",
            )

        # Type 2: APPLICATION_COMMAND -- defer + background follow-up
        if interaction_type == 2:
            t = threading.Thread(
                target=_handle_command,
                args=(payload, app_id),
                daemon=True,
            )
            t.start()

            return Response(
                json.dumps({"type": 5}),
                status=200,
                content_type="application/json",
            )

        return Response(
            json.dumps({"type": 1}),
            status=200,
            content_type="application/json",
        )
