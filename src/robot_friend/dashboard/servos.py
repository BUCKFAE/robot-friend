"""Dashboard servo controls — what the ServoPanel reads and writes.

:class:`ServoBackend` is the interface the panel talks to. Two implementations let the same
panel drive either a local demo or a live robot:

* :class:`DashboardServos` — demo/local: a :class:`ServoController` over the factory-selected
  driver (the in-memory fake on a laptop), so servos can be moved and debugged with no hardware.
* :class:`~robot_friend.dashboard.servos_client.RobotServosClient` — live: read and command the
  robot's servos over HTTP.

Mirrors the camera/mic :class:`ControlsBackend` split in :mod:`robot_friend.dashboard.controls`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from robot_friend.servo.servo import ServoState
from robot_friend.servo.servo_controller import ServoController

# Re-export ServoState so the panel/client import it from here.
__all__ = ["ServoBackend", "DashboardServos", "ServoState"]


class ServoBackend(ABC):
    """Servo states + commands, readable and settable by the ServoPanel."""

    @abstractmethod
    def servos(self) -> list[ServoState]: ...

    @abstractmethod
    def set_angle(self, channel: int, angle: float) -> None: ...

    @abstractmethod
    def set_calibration(self, channel: int, deviation: float) -> None: ...

    @abstractmethod
    def driver_label(self) -> str:
        """Name of the active backend driver (e.g. ``FakePwmDriver``), shown in the UI."""


class DashboardServos(ServoBackend):
    """Demo/local backend: a real ServoController over the factory-selected driver.

    The controller is built lazily on first use so that, in live mode (where this is swapped
    for :class:`RobotServosClient` before any panel renders), no driver is opened and no servo
    is moved — mirroring how cheap :class:`DashboardControls` is at construction.
    """

    def __init__(self) -> None:
        self._controller: ServoController | None = None

    @property
    def _ctrl(self) -> ServoController:
        if self._controller is None:
            self._controller = ServoController.from_factory()
        return self._controller

    def servos(self) -> list[ServoState]:
        return self._ctrl.states()

    def set_angle(self, channel: int, angle: float) -> None:
        self._ctrl.set_angle(channel, angle)

    def set_calibration(self, channel: int, deviation: float) -> None:
        self._ctrl.set_calibration(channel, deviation)

    def driver_label(self) -> str:
        return self._ctrl.driver_name
