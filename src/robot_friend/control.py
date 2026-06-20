"""Robot-side control state: which camera / microphone the robot is using.

Written by ``POST /control`` (from the dashboard, or any client) and read by main's
vision and audio loops, which switch hardware when the selection changes. The robot does
not depend on anyone setting these — defaults are used until a command arrives, so the
control endpoint is purely additive and never required.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from robot_friend.devices import camera_options, sound_options
from robot_friend.utils.finch_logger import finch_logger


class RobotControls:
    """Thread-safe selected-device state, plus the device list for ``/devices.json``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._camera_index = 0
        self._sound_device: int | str | None = None
        self._sound_callbacks: list[Callable[[int | str | None], None]] = []

    @property
    def camera_index(self) -> int:
        with self._lock:
            return self._camera_index

    @property
    def sound_device(self) -> int | str | None:
        with self._lock:
            return self._sound_device

    def set_camera_index(self, index: int) -> None:
        with self._lock:
            if self._camera_index == index:
                return
            self._camera_index = index
        finch_logger.info("camera device selected: %s", index)

    def set_sound_device(self, device: int | str | None) -> None:
        with self._lock:
            if self._sound_device == device:
                return
            self._sound_device = device
            callbacks = list(self._sound_callbacks)
        finch_logger.info("sound device selected: %s", device)
        for callback in callbacks:
            callback(device)

    def on_sound_device_changed(
        self, callback: Callable[[int | str | None], None]
    ) -> None:
        """Register a callback fired when the sound device changes (the audio loop uses
        this to restart capture on the new device)."""
        with self._lock:
            self._sound_callbacks.append(callback)

    def apply(self, payload: dict[str, Any]) -> None:
        """Apply a control command — the parsed ``POST /control`` body. Absent keys are
        left unchanged, so partial updates work."""
        if payload.get("camera_index") is not None:
            self.set_camera_index(int(payload["camera_index"]))
        if "sound_device" in payload:
            self.set_sound_device(payload["sound_device"])

    def devices_payload(self) -> dict[str, Any]:
        """Available devices + current selection, for ``GET /devices.json``."""
        return {
            "camera": [
                {"value": o.value, "label": o.label}
                for o in camera_options(self.camera_index)
            ],
            "sound": [{"value": o.value, "label": o.label} for o in sound_options()],
            "selected": {
                "camera_index": self.camera_index,
                "sound_device": self.sound_device,
            },
        }
