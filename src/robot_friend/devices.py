"""Hardware device enumeration for the robot host (cameras + microphones).

Lives outside the dashboard so the robot can enumerate and serve its own devices over
``GET /devices.json`` (the dashboard renders that list and commands a selection back).
Probing is lazy/guarded so importing this is cheap and safe where cv2/sounddevice or a
display aren't available.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host


@dataclass(frozen=True)
class DeviceOption:
    """A selectable hardware device.

    Attributes:
        value: The identifier passed back when this device is selected (index or name).
        label: Human-readable name for the dropdown.
    """
    value: Any
    label: str


def camera_options(current_index: int = 0) -> list[DeviceOption]:
    """Enumerate selectable cameras on this host (always returns at least one option)."""
    if is_pi_host():
        return [DeviceOption(0, "Pi camera")]

    video_devices = sorted(Path("/dev").glob("video[0-9]*"))
    indexes = [
        int(path.name.removeprefix("video"))
        for path in video_devices
        if path.name.removeprefix("video").isdigit()
    ]
    if not indexes:
        return [DeviceOption(current_index, f"Camera {current_index}")]

    try:
        import cv2
    except Exception as exc:
        finch_logger.warning("could not enumerate cameras: %s", exc)
        return [DeviceOption(current_index, f"Camera {current_index}")]

    options: list[DeviceOption] = []
    for index in indexes:
        cap = cv2.VideoCapture(index)
        try:
            if cap.isOpened():
                options.append(DeviceOption(index, f"Camera {index}"))
        finally:
            cap.release()
    return options or [DeviceOption(current_index, f"Camera {current_index}")]


def sound_options() -> list[DeviceOption]:
    """Enumerate capture-capable sound devices (always returns at least one option)."""
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
