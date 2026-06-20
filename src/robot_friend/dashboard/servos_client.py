"""Live ServoPanel backend: read and command the robot's servos over HTTP.

``GET /servos.json`` for the robot's servo states + active driver; ``POST /servo`` to move one.
The last fetch is cached so the panel still renders (from the cache / safe defaults) when the
robot is momentarily unreachable. Mirrors :class:`RobotControlsClient`.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from robot_friend.dashboard.servos import ServoBackend
from robot_friend.servo.servo import ServoState
from robot_friend.utils.finch_logger import finch_logger

_TIMEOUT = 1.5


class RobotServosClient(ServoBackend):
    """Reads the robot's servos and posts angle commands back to it."""

    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._cache: dict[str, Any] = {"servos": [], "driver": "unknown"}

    def _fetch(self) -> None:
        try:
            with urllib.request.urlopen(
                self._base + "/servos.json", timeout=_TIMEOUT
            ) as response:
                self._cache = json.loads(response.read())
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            finch_logger.info("robot servos unreachable at %s (%s)", self._base, exc)

    def _post(self, payload: dict[str, Any]) -> None:
        request = urllib.request.Request(
            self._base + "/servo",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=_TIMEOUT).close()
        except (urllib.error.URLError, OSError) as exc:
            finch_logger.warning("could not send servo command to %s (%s)", self._base, exc)

    def servos(self) -> list[ServoState]:
        self._fetch()  # refresh the cache (states + driver) whenever the panel reads
        return [ServoState(**s) for s in self._cache.get("servos", [])]

    def set_angle(self, channel: int, angle: float) -> None:
        self._post({"channel": channel, "angle": angle})

    def set_calibration(self, channel: int, deviation: float) -> None:
        self._post({"channel": channel, "calibration": deviation})

    def driver_label(self) -> str:
        return self._cache.get("driver", "unknown")
