"""Real-time progress tracking for AI generation commands.

Provides ``ProgressTracker`` which fans out ``ProgressEvent`` updates to
one or more sinks (Discord channel message, ephemeral reply, Socket.IO,
Crate notification).

Each sink implements ``send(event)`` and ``close()``.  Sinks are
responsible for their own throttling.
"""

from __future__ import annotations

import os
import time
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable

import requests as _req

# ---------------------------------------------------------------------------
# Phase constants and default percentages
# ---------------------------------------------------------------------------

PHASES = {
    "analyzing":      0,
    "generating":    10,
    "parsing":       85,
    "creating_image": 90,
    "posting":       95,
    "complete":     100,
    "error":          0,
}

_PHASE_LABELS = {
    "analyzing":      "Analyzing prompt...",
    "generating":     "Generating AI response...",
    "parsing":        "Parsing response...",
    "creating_image": "Creating image...",
    "posting":        "Posting to channel...",
    "complete":       "Complete",
    "error":          "Error",
}


# ---------------------------------------------------------------------------
# ProgressEvent
# ---------------------------------------------------------------------------

@dataclass
class ProgressEvent:
    """A single progress update."""
    task_id: str
    phase: str
    percent: int = 0
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def format_discord(self) -> str:
        """Render a text progress bar for Discord messages.

        Example: ``[########--] 80% Generating AI response... (1,200 bytes)``
        """
        filled = round(self.percent / 10)
        bar = "\u2588" * filled + "\u2591" * (10 - filled)
        label = _PHASE_LABELS.get(self.phase, self.phase)
        detail_suffix = f" ({self.detail})" if self.detail else ""
        return f"[{bar}] {self.percent}% {label}{detail_suffix}"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self.phase,
            "percent": self.percent,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Discord API helpers
# ---------------------------------------------------------------------------

def _edit_channel_message(channel_id: str, message_id: str, content: str) -> bool:
    """PATCH an existing channel message. Returns True on success."""
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token or not channel_id or not message_id:
        return False
    try:
        resp = _req.patch(
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json={"content": content},
            timeout=10,
        )
        return resp.ok
    except Exception as exc:
        print(f"[progress] edit channel message failed: {exc}")
        return False


def _patch_original(application_id: str, token: str, content: str) -> bool:
    """PATCH the @original ephemeral deferred response. Returns True on success."""
    if not application_id or not token:
        return False
    try:
        resp = _req.patch(
            f"https://discord.com/api/v10/webhooks/{application_id}/{token}/messages/@original",
            json={"content": content},
            timeout=10,
        )
        return resp.ok
    except Exception as exc:
        print(f"[progress] patch original failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Sinks
# ---------------------------------------------------------------------------

class ChannelMessageSink:
    """Edit a Discord channel loading message with progress bar text.

    Throttled to 1 edit per ``min_interval`` seconds (default 3s).
    Phase transitions bypass the throttle.
    """

    def __init__(self, channel_id: str, message_id: str, *, min_interval: float = 3.0):
        self.channel_id = channel_id
        self.message_id = message_id
        self.min_interval = min_interval
        self._last_send: float = 0.0
        self._last_phase: str = ""

    def send(self, event: ProgressEvent) -> None:
        now = time.time()
        phase_changed = event.phase != self._last_phase
        if not phase_changed and (now - self._last_send) < self.min_interval:
            return
        self._last_send = now
        self._last_phase = event.phase
        _edit_channel_message(self.channel_id, self.message_id, event.format_discord())

    def close(self) -> None:
        pass


class EphemeralSink:
    """PATCH the @original deferred ephemeral response with progress text.

    Throttled to 1 edit per ``min_interval`` seconds (default 3s).
    Phase transitions bypass the throttle.
    """

    def __init__(self, application_id: str, token: str, *, min_interval: float = 3.0):
        self.application_id = application_id
        self.token = token
        self.min_interval = min_interval
        self._last_send: float = 0.0
        self._last_phase: str = ""

    def send(self, event: ProgressEvent) -> None:
        now = time.time()
        phase_changed = event.phase != self._last_phase
        if not phase_changed and (now - self._last_send) < self.min_interval:
            return
        self._last_send = now
        self._last_phase = event.phase
        _patch_original(self.application_id, self.token, event.format_discord())

    def close(self) -> None:
        pass


class SocketIOSink:
    """Emit ``gen_progress`` events via Socket.IO.

    Throttled to 1 emit per ``min_interval`` seconds (default 0.5s).
    Phase transitions bypass the throttle.
    """

    def __init__(self, *, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._last_send: float = 0.0
        self._last_phase: str = ""

    def send(self, event: ProgressEvent) -> None:
        now = time.time()
        phase_changed = event.phase != self._last_phase
        if not phase_changed and (now - self._last_send) < self.min_interval:
            return
        self._last_send = now
        self._last_phase = event.phase
        from ._bridge import emit_progress
        emit_progress(event.to_dict())

    def close(self) -> None:
        pass


class CrateNotifySink:
    """Push crate.notify() on phase transitions only.

    Throttled to 1 notification per ``min_interval`` seconds (default 5s).
    Only fires on phase changes, never on byte-level updates.
    """

    def __init__(self, *, min_interval: float = 5.0):
        self.min_interval = min_interval
        self._last_send: float = 0.0
        self._last_phase: str = ""

    def send(self, event: ProgressEvent) -> None:
        if event.phase == self._last_phase:
            return  # Only fire on phase transitions
        now = time.time()
        if (now - self._last_send) < self.min_interval:
            return
        self._last_send = now
        self._last_phase = event.phase
        label = _PHASE_LABELS.get(event.phase, event.phase)
        from ._bridge import crate_notify, emit_command
        emit_command(crate_notify(f"{event.percent}% {label}", timeout=4000))

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# ProgressTracker
# ---------------------------------------------------------------------------

class ProgressTracker:
    """Fan-out progress updates to multiple sinks.

    Parameters
    ----------
    sinks : list
        Sink instances (each must have ``send(event)`` and ``close()``).
    task_id : str, optional
        Unique ID for this generation task.  Auto-generated if omitted.
    """

    def __init__(self, sinks: list | None = None, *, task_id: str | None = None):
        self.task_id = task_id or str(uuid.uuid4())
        self.sinks = list(sinks or [])
        self._lock = threading.Lock()
        self._closed = False

    def update(self, phase: str, percent: int | None = None, detail: str = "") -> None:
        """Push a progress update to all sinks.

        Parameters
        ----------
        phase : str
            One of the keys in ``PHASES``.
        percent : int, optional
            Override the default percentage for this phase.
        detail : str, optional
            Extra detail text (e.g. byte counts).
        """
        if self._closed:
            return
        pct = percent if percent is not None else PHASES.get(phase, 0)
        event = ProgressEvent(
            task_id=self.task_id,
            phase=phase,
            percent=pct,
            detail=detail,
        )
        with self._lock:
            for sink in self.sinks:
                try:
                    sink.send(event)
                except Exception as exc:
                    print(f"[progress] sink {type(sink).__name__} error: {exc}")

    def stream_callback(self) -> Callable[[int, int], None]:
        """Return a ``(chunk_bytes, total_bytes)`` callback for Gemini streaming.

        Maps byte-level progress to the 10-80% range of the ``generating`` phase.
        """
        def _on_chunk(chunk_bytes: int, total_bytes: int) -> None:
            # Map total_bytes into 10-80% range
            # Use a log-like curve: quick initial progress, slower as it grows
            # Assume typical responses are 500-5000 bytes
            if total_bytes <= 0:
                pct = 10
            elif total_bytes >= 5000:
                pct = 80
            else:
                pct = 10 + int(70 * (total_bytes / 5000))
            pct = min(pct, 80)
            detail = f"{total_bytes:,} bytes received"
            self.update("generating", percent=pct, detail=detail)
        return _on_chunk

    def close(self) -> None:
        """Mark tracker as closed and clean up sinks."""
        self._closed = True
        with self._lock:
            for sink in self.sinks:
                try:
                    sink.close()
                except Exception:
                    pass
