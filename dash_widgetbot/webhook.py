"""Send messages to Discord via Webhook Execute API."""

import os
import time

import requests


def send_webhook_message(
    content,
    *,
    webhook_url=None,
    username=None,
    avatar_url=None,
    thread_id=None,
    embed=None,
):
    """POST a message to a Discord webhook.

    Parameters
    ----------
    content : str
        Message text.
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

    payload = {"content": content}
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if embed:
        payload["embeds"] = [embed]

    params = {"wait": "true"}
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
