"""Wire format + latest-value store for robot telemetry.

``robot_friend.main`` (the producer) owns a :class:`~robot_friend.telemetry.store.TelemetryStore`
and serves it as JSON on ``GET /telemetry.json``; the dashboard polls that endpoint,
reconstructs the dataclasses via :mod:`robot_friend.telemetry.codec`, and republishes
them onto its ``Bus``. Kept dependency-light so the realtime process needn't import the
dashboard or its web-stack deps.
"""
from robot_friend.telemetry.store import TelemetryStore

__all__ = ["TelemetryStore"]
