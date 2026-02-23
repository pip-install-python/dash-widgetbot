"""Thread-safe in-memory store for /gen entries.

Entries are pushed by the Discord interaction handler (or local test)
and polled by the Dash page via ``dcc.Interval``.

## v1 (current): In-memory store + dcc.Interval polling (2s)
##   - Simple, no external deps, works with Flask dev server
##   - Latency: up to 2s between gen and display
##
## v2 (production): Flask SSE push
##   1. Add hooks.route("api/gen/stream") returning text/event-stream:
##        def event_generator():
##            cursor = gen_store.count()
##            while True:
##                new = gen_store.get_since(cursor)
##                for entry in new:
##                    cursor += 1
##                    yield f"data: {entry_to_json(entry)}\\n\\n"
##                time.sleep(0.5)
##
##   2. On the Dash page, replace dcc.Interval with a clientside_callback
##      that creates ``new EventSource("/api/gen/stream")`` and calls
##      ``window.dash_clientside.set_props("gen-feed", {children: ...})``
##      when data arrives.
##
##   3. Use Gunicorn with gevent/eventlet worker for concurrent SSE streams.
##      Flask dev server does NOT handle concurrent long-lived connections.
##
##   4. For multi-process deployments, replace in-memory gen_store with
##      Redis pub/sub (e.g. redis.pubsub() + subscribe to "gen" channel).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from .gen_schemas import GenResponse


@dataclass
class GenEntry:
    """A single /gen result stored in the feed."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    response: GenResponse | None = None
    image_bytes: bytes | None = None
    image_mime: str = ""
    discord_user: str = ""
    timestamp: float = field(default_factory=time.time)
    error: str | None = None


class GenStore:
    """Thread-safe ordered list of GenEntry objects."""

    def __init__(self, *, max_entries: int = 200):
        self._entries: list[GenEntry] = []
        self._max = max_entries
        self._lock = threading.Lock()

    def add(self, entry: GenEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max:
                self._entries = self._entries[-self._max:]

    def get_since(self, cursor: int) -> list[GenEntry]:
        """Return entries added after position *cursor*."""
        with self._lock:
            return list(self._entries[cursor:])

    def get_all(self) -> list[GenEntry]:
        with self._lock:
            return list(self._entries)

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


# Module-level singleton
gen_store = GenStore()
