"""Dashboard controls — what the ControlPanel reads and writes.

:class:`ControlsBackend` is the interface the panel talks to. Two implementations let the
same panel drive either a local demo or a live robot:

* :class:`DashboardControls` — demo/local: enumerate *this* host's devices, keep the
  selection in memory (nothing consumes it; the demo sources are synthetic).
* :class:`~robot_friend.dashboard.controls_client.RobotControlsClient` — live: enumerate
  and command the *robot* over HTTP.

Device enumeration itself lives in :mod:`robot_friend.devices` (shared with the robot).
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass

from robot_friend.devices import DeviceOption, camera_options, sound_options
from robot_friend.utils.finch_logger import finch_logger

# Re-export DeviceOption so panels keep importing it from here.
__all__ = [
    "ControlsBackend",
    "DashboardControls",
    "DeviceOption",
    "ControlSelection",
    "CONTROLS_STATE_CHANNEL",
]

#: Bus channel the ControlPanel syncs its shared state on (see :mod:`.panels.state_sync`).
CONTROLS_STATE_CHANNEL = "controls.state"


@dataclass(frozen=True)
class ControlSelection:
    """The device selection shared across dashboard clients.

    Only the *selection* is synced — device enumeration (which probes cameras/mics) stays
    behind the panel's "Refresh devices" button, off the live-update path.

    Attributes:
        camera_index: Selected webcam index.
        sound_device: Selected sound-input device (index, name, or None for the default).
    """
    camera_index: int
    sound_device: int | str | None


class ControlsBackend(ABC):
    """Device options + current selection, readable and settable by the ControlPanel."""

    @abstractmethod
    def camera_options(self) -> list[DeviceOption]: ...

    @abstractmethod
    def sound_options(self) -> list[DeviceOption]: ...

    @property
    @abstractmethod
    def camera_index(self) -> int: ...

    @property
    @abstractmethod
    def sound_device(self) -> int | str | None: ...

    @abstractmethod
    def set_camera_index(self, index: int) -> None: ...

    @abstractmethod
    def set_sound_device(self, device: int | str | None) -> None: ...

    def selection(self) -> ControlSelection:
        """Current selection — the snapshot the panel syncs across clients."""
        return ControlSelection(
            camera_index=self.camera_index,
            sound_device=self.sound_device,
        )


class DashboardControls(ControlsBackend):
    """Demo/local backend: this host's devices, selection held in memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._camera_index = 0
        self._sound_device: int | str | None = None

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
        with self._lock:
            if self._sound_device == device:
                return
            self._sound_device = device
        finch_logger.info("selected sound device: %s", device)

    def camera_options(self) -> list[DeviceOption]:
        return camera_options(self.camera_index)

    def sound_options(self) -> list[DeviceOption]:
        return sound_options()
