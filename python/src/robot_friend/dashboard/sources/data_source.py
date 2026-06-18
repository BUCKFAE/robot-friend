"""The ``DataSource`` extension point.

A sibling abstraction to ``Camera`` and ``ImageDetector``: a source starts
producing in the background and publishes onto a :class:`Bus` channel; a matching
``Panel`` consumes that channel. Adding a panel to the dashboard is therefore
"add a source + add a panel that share a channel name".
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from robot_friend.dashboard.bus import Bus


class DashboardDataSource(ABC):
    """Base class for everything that feeds the dashboard."""

    #: Bus channel this source publishes onto (panels subscribe by the same name).
    channel: str

    @abstractmethod
    def start(self, bus: Bus) -> None:
        """Begin publishing to ``self.channel`` (typically on a daemon thread)."""
