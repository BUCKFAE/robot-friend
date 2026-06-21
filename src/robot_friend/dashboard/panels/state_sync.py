"""Cross-client live state for dashboard control panels, carried on the :class:`Bus`.

The dashboard builds a fresh element tree per browser connection (see
:mod:`robot_friend.dashboard.app`), so a control one user moves — a servo slider, a
device select — is invisible to everyone else unless its new value is broadcast. The
:class:`~robot_friend.dashboard.bus.Bus` already fans a channel's latest value out to
every client's poll timer; :class:`StateSync` is the small piece that makes a panel use
it as *shared* state: publish a snapshot when this client commits a change, and apply
peers' snapshots back onto the widgets without echoing our own change or looping.

A panel *composes* one ``StateSync`` (rather than subclassing it), keyed to a bus
channel, and supplies its own snapshot type plus a widget-update callback — so servos (a
:class:`~robot_friend.dashboard.servos.ServoSnapshot`) and controls (a
:class:`~robot_friend.dashboard.controls.ControlSelection`) share the same plumbing.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot_friend.dashboard.bus import Bus


class StateSync:
    """Mirrors one panel's state across every client over a single :class:`Bus` channel.

    Attributes:
        state: The last snapshot published or applied — this client's view of the
            shared value, used to dedupe and to build the next optimistic snapshot.
        applying: True while a peer's snapshot is being written to the widgets.
    """

    def __init__(self, bus: Bus, channel: str) -> None:
        self._bus = bus
        self._channel = channel
        self._state: Any = None
        self._applying = False

    @property
    def state(self) -> Any:
        return self._state

    @property
    def applying(self) -> bool:
        """Commit handlers check this and bail: programmatic widget updates made while
        applying a peer's snapshot must not be mistaken for user input and re-broadcast.
        """
        return self._applying

    def seed(self, snapshot: Any) -> None:
        """Adopt ``snapshot`` as the starting state, publishing it only if the channel is
        still empty — so the first client to render seeds the shared value and later
        clients inherit whatever peers have since changed it to."""
        self._state = snapshot
        if self._bus.latest(self._channel) is None:
            self._bus.publish(self._channel, snapshot)

    def publish(self, snapshot: Any) -> None:
        """Broadcast a user-made change to every client — a no-op while applying a peer's
        update, or when nothing actually changed (which also breaks feedback loops)."""
        if self._applying or snapshot == self._state:
            return
        self._state = snapshot
        self._bus.publish(self._channel, snapshot)

    def receive(self, snapshot: Any, apply_to_widgets: Callable[[Any], None]) -> None:
        """Apply a snapshot delivered by the poll timer, skipping our own echo and
        guarding ``apply_to_widgets`` so the writes it makes can't re-publish."""
        if snapshot == self._state:
            return
        self._state = snapshot
        self._applying = True
        try:
            apply_to_widgets(snapshot)
        finally:
            self._applying = False
