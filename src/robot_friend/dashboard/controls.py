"""Shared dashboard controls state.

The NiceGUI control panel writes this object from the UI thread; background sources
read it from worker threads. Keep it intentionally small and typed so adding more
controls later is straightforward.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host


@dataclass(frozen=True)
class DeviceOption:
    value: Any
    label: str


class DashboardControls:
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
        finch_logger.info("selected camera device: %s", index)

    def set_sound_device(self, device: int | str | None) -> None:
        callbacks: list[Callable[[int | str | None], None]]
        with self._lock:
            if self._sound_device == device:
                return
            self._sound_device = device
            callbacks = list(self._sound_callbacks)
        finch_logger.info("selected sound device: %s", device)
        for callback in callbacks:
            callback(device)

    def on_sound_device_changed(
        self, callback: Callable[[int | str | None], None]
    ) -> None:
        with self._lock:
            self._sound_callbacks.append(callback)

    def camera_options(self) -> list[DeviceOption]:
        if is_pi_host():
            return [DeviceOption(0, "Pi camera")]

        video_devices = sorted(Path("/dev").glob("video[0-9]*"))
        indexes = [
            int(path.name.removeprefix("video"))
            for path in video_devices
            if path.name.removeprefix("video").isdigit()
        ]
        if not indexes:
            return [DeviceOption(self.camera_index, f"Camera {self.camera_index}")]

        try:
            import cv2
        except Exception as exc:
            finch_logger.warning("could not enumerate cameras: %s", exc)
            return [DeviceOption(self.camera_index, f"Camera {self.camera_index}")]

        options: list[DeviceOption] = []
        for index in indexes:
            cap = cv2.VideoCapture(index)
            try:
                if cap.isOpened():
                    label = f"Camera {index}"
                    options.append(DeviceOption(index, label))
            finally:
                cap.release()
        if not options:
            options.append(DeviceOption(self.camera_index, f"Camera {self.camera_index}"))
        return options

    def sound_options(self) -> list[DeviceOption]:
        try:
            import sounddevice
        except Exception as exc:
            finch_logger.warning("could not enumerate sound devices: %s", exc)
            return [DeviceOption(None, "Default input")]

        try:
            devices = sounddevice.query_devices()
        except Exception as exc:
            finch_logger.warning("could not query sound devices: %s", exc)
            return [DeviceOption(None, "Default input")]

        options = [
            DeviceOption(index, f"{index}: {info['name']}")
            for index, info in enumerate(devices)
            if info["max_input_channels"] > 0
        ]
        return options or [DeviceOption(None, "Default input")]
