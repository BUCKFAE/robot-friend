"""Thread-safe channel fan-out at the heart of the dashboard.

Sync producers (the camera loop, the sound-device callback, metric pollers) call
:meth:`Bus.publish` from their own threads. The per-client NiceGUI page reads the
most recent value with :meth:`Bus.latest` from a ``ui.timer`` poll, and optional
callbacks fire synchronously on publish. This generalises the single-slot
``threading.Condition`` fan-out the original single-stream video server used.

Only lightweight metadata travels on the bus (numbers, short strings, dataclasses).
High-rate media bypasses it: video goes over a dedicated MJPEG route, audio over a
binary WebSocket.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class Bus:
    """A latest-value store with per-channel subscribers, safe across threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, Any] = {}
        self._subscribers: dict[str, list[Callable[[Any], None]]] = {}

    def publish(self, channel: str, value: Any) -> None:
        """Record ``value`` as the latest on ``channel`` and notify subscribers."""
        with self._lock:
            self._latest[channel] = value
            subscribers = list(self._subscribers.get(channel, ()))
        # Fire outside the lock so a slow subscriber can't block other producers.
        for callback in subscribers:
            callback(value)

    def latest(self, channel: str, default: Any = None) -> Any:
        """Return the most recently published value on ``channel`` (or ``default``)."""
        with self._lock:
            return self._latest.get(channel, default)

    def subscribe(self, channel: str, callback: Callable[[Any], None]) -> None:
        """Register ``callback`` to run (on the publisher's thread) for each publish."""
        with self._lock:
            self._subscribers.setdefault(channel, []).append(callback)

    def channels(self) -> list[str]:
        """Every channel that has received at least one value."""
        with self._lock:
            return list(self._latest)
