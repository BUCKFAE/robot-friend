"""Live ControlPanel backend: enumerate and command the robot over HTTP.

``GET /devices.json`` for the robot's device options + current selection; ``POST /control``
to change them. The last fetch is cached so the panel can read the current selection right
after listing options, and so a momentarily-unreachable robot still lets the page render
(falling back to the last cache / safe defaults).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from robot_friend.dashboard.controls import ControlsBackend
from robot_friend.devices import DeviceOption
from robot_friend.utils.finch_logger import finch_logger

_TIMEOUT = 1.5


class RobotControlsClient(ControlsBackend):
    """Reads the robot's devices and posts selections back to it."""

    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._cache: dict = {
            "camera": [],
            "sound": [],
            "selected": {"camera_index": 0, "sound_device": None},
        }

    def _fetch(self) -> None:
        try:
            with urllib.request.urlopen(self._base + "/devices.json", timeout=_TIMEOUT) as response:
                self._cache = json.loads(response.read())
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            finch_logger.info("robot devices unreachable at %s (%s)", self._base, exc)

    def _post(self, payload: dict) -> None:
        request = urllib.request.Request(
            self._base + "/control",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=_TIMEOUT).close()
        except (urllib.error.URLError, OSError) as exc:
            finch_logger.warning("could not send control to robot %s (%s)", self._base, exc)

    def camera_options(self) -> list[DeviceOption]:
        self._fetch()  # refresh the cache (and current selection) when options are listed
        return [DeviceOption(o["value"], o["label"]) for o in self._cache.get("camera", [])]

    def sound_options(self) -> list[DeviceOption]:
        return [DeviceOption(o["value"], o["label"]) for o in self._cache.get("sound", [])]

    @property
    def camera_index(self) -> int:
        return self._cache.get("selected", {}).get("camera_index", 0)

    @property
    def sound_device(self) -> int | str | None:
        return self._cache.get("selected", {}).get("sound_device")

    def set_camera_index(self, index: int) -> None:
        self._post({"camera_index": index})

    def set_sound_device(self, device: int | str | None) -> None:
        self._post({"sound_device": device})
