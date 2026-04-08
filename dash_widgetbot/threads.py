"""Per-user private thread manager for AI commands.

Creates and caches Discord private threads (type 12) so each user gets
an isolated 1-on-1 AI chat experience.  Opt-in via the
``AI_THREAD_PARENT_CHANNEL`` environment variable.

Thread naming: ``AI \u00b7 {username}``
Cache: ``user_id \u2192 thread_id`` (in-memory, thread-safe)
"""

import os
import threading

import requests


def _discord_api(method, path, *, json=None, max_retries=1, timeout=10):
    """Minimal Discord REST helper for thread operations."""
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token:
        return None
    url = f"https://discord.com/api/v10{path}"
    headers = {"Authorization": f"Bot {bot_token}"}
    if json is not None:
        headers["Content-Type"] = "application/json"
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = getattr(requests, method)(
                url, headers=headers, json=json, timeout=timeout,
            )
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < max_retries:
                import time
                time.sleep(1)
    print(f"[dash-widgetbot] Thread API {method.upper()} {path} failed: {last_exc}")
    return None


class ThreadManager:
    """Thread-safe manager that creates/caches per-user private threads."""

    def __init__(self):
        self._cache: dict[str, str] = {}  # user_id -> thread_id
        self._lock = threading.Lock()
        self._warmed = False

    def get_or_create(self, parent_channel_id: str, user_id: str, username: str) -> str | None:
        """Return cached thread_id or create a new private thread.

        Returns None on failure (no bot token, API error, etc.).
        """
        if not parent_channel_id or not user_id:
            return None

        with self._lock:
            # Warm cache on first call
            if not self._warmed:
                self._warm_cache(parent_channel_id)
                self._warmed = True

            # Cache hit
            cached = self._cache.get(user_id)
            if cached:
                return cached

        # Cache miss — create thread (outside lock to avoid blocking)
        thread_id = self._create_thread(parent_channel_id, user_id, username)
        if thread_id:
            with self._lock:
                self._cache[user_id] = thread_id
        return thread_id

    def _create_thread(self, parent_channel_id: str, user_id: str, username: str) -> str | None:
        """Create a private thread and add the user to it.

        POST /channels/{parent}/threads -> type 12 (PRIVATE_THREAD),
        invitable=false, auto_archive_duration=10080 (7 days).
        PUT /channels/{thread}/thread-members/{user_id} to add user.
        """
        thread_name = f"AI \u00b7 {username}"

        resp = _discord_api(
            "post",
            f"/channels/{parent_channel_id}/threads",
            json={
                "name": thread_name,
                "type": 12,  # PRIVATE_THREAD
                "invitable": False,
                "auto_archive_duration": 10080,  # 7 days
            },
        )
        if resp is None or not resp.ok:
            status = resp.status_code if resp is not None else "no response"
            text = resp.text[:200] if resp is not None else ""
            print(f"[dash-widgetbot] Thread creation failed ({status}): {text}")
            return None

        thread_id = resp.json().get("id")
        if not thread_id:
            print("[dash-widgetbot] Thread creation returned no ID")
            return None

        # Add the user to the thread
        add_resp = _discord_api(
            "put",
            f"/channels/{thread_id}/thread-members/{user_id}",
        )
        if add_resp is not None and not add_resp.ok and add_resp.status_code != 204:
            print(f"[dash-widgetbot] Failed to add user {user_id} to thread {thread_id}: {add_resp.status_code}")
            # Thread was created successfully, continue even if member add fails

        print(f"[dash-widgetbot] Created private thread for {username} -> {thread_id}")
        return thread_id

    def _warm_cache(self, parent_channel_id: str):
        """Recover threads from a previous session by scanning archived private threads.

        GET /channels/{parent}/threads/archived/private
        Match by name pattern 'AI \u00b7 {username}'.
        """
        resp = _discord_api("get", f"/channels/{parent_channel_id}/threads/archived/private")
        if resp is None or not resp.ok:
            return

        threads = resp.json().get("threads", [])
        for thread in threads:
            name = thread.get("name", "")
            thread_id = thread.get("id", "")
            if not name.startswith("AI \u00b7 ") or not thread_id:
                continue
            # We need to find the user_id from thread members
            # Fetch thread members to map back to user_id
            members_resp = _discord_api("get", f"/channels/{thread_id}/thread-members")
            if members_resp is None or not members_resp.ok:
                continue
            for member in members_resp.json():
                uid = member.get("user_id", "")
                # Skip the bot's own user_id
                if uid and uid not in self._cache:
                    self._cache[uid] = thread_id

        if self._cache:
            print(f"[dash-widgetbot] Warmed thread cache with {len(self._cache)} entries")

    def invalidate(self, user_id: str):
        """Remove a cached thread for a user (e.g. after 404)."""
        with self._lock:
            self._cache.pop(user_id, None)


# Module-level singleton
thread_manager = ThreadManager()
