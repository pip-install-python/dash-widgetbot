"""Send messages to Discord via Webhook Execute API."""

import os
import time

import requests

from ._constants import IS_COMPONENTS_V2


def send_webhook_message(
    content=None,
    *,
    webhook_url=None,
    username=None,
    avatar_url=None,
    thread_id=None,
    embed=None,
    components=None,
    flags=None,
):
    """POST a message to a Discord webhook.

    Parameters
    ----------
    content : str, optional
        Message text.  Can be ``None`` when sending a Components V2 message.
    webhook_url : str, optional
        Full webhook URL. Falls back to ``DISCORD_WEBHOOK_URL`` env var.
    username : str, optional
        Override the webhook's default username.
    avatar_url : str, optional
        Override the webhook's default avatar.
    thread_id : str, optional
        Send into a specific thread.
    embed : dict, optional
        A single Discord embed object.
    components : list[dict], optional
        Top-level message components (Components V2).  When provided the
        ``IS_COMPONENTS_V2`` flag is automatically set.
    flags : int, optional
        Message flags.  ``IS_COMPONENTS_V2`` (32768) is OR-ed in automatically
        when *components* is provided.

    Returns
    -------
    dict
        ``{success, status_code, message_id, error, _ts}``
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return {
            "success": False,
            "status_code": 0,
            "message_id": None,
            "error": "No webhook URL provided",
            "_ts": time.time(),
        }

    payload = {}
    if content is not None:
        payload["content"] = content
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if embed:
        payload["embeds"] = [embed]
    if components is not None:
        payload["components"] = components
        # Auto-set IS_COMPONENTS_V2 flag
        payload["flags"] = (flags or 0) | IS_COMPONENTS_V2
    elif flags is not None:
        payload["flags"] = flags

    params = {"wait": "true"}
    if components is not None:
        # Required query param for Components V2 via webhooks
        params["with_components"] = "true"
    if thread_id:
        params["thread_id"] = thread_id

    try:
        resp = requests.post(url, json=payload, params=params, timeout=10)
        if resp.ok:
            data = resp.json()
            return {
                "success": True,
                "status_code": resp.status_code,
                "message_id": data.get("id"),
                "error": None,
                "_ts": time.time(),
            }
        return {
            "success": False,
            "status_code": resp.status_code,
            "message_id": None,
            "error": resp.text[:500],
            "_ts": time.time(),
        }
    except requests.RequestException as exc:
        return {
            "success": False,
            "status_code": 0,
            "message_id": None,
            "error": str(exc),
            "_ts": time.time(),
        }
