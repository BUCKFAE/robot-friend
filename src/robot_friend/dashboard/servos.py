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
from dataclasses import dataclass, replace

from robot_friend.servo.servo import ServoState
from robot_friend.servo.servo_controller import ServoController

# Re-export ServoState so the panel/client import it from here.
__all__ = [
    "ServoBackend",
    "DashboardServos",
    "ServoState",
    "ServoSnapshot",
    "SERVOS_STATE_CHANNEL",
    "with_angle",
    "with_calibration",
]

#: Bus channel the ServoPanel syncs its shared state on (see :mod:`.panels.state_sync`).
SERVOS_STATE_CHANNEL = "servos.state"


@dataclass(frozen=True)
class ServoSnapshot:
    """Everything the ServoPanel renders, broadcast as one value across clients.

    Attributes:
        states: Every servo's current state (a tuple so the snapshot is immutable and
            compares by value, which the sync layer relies on to dedupe).
        driver: Active driver name (e.g. ``FakePwmDriver``), shown in the panel.
    """
    states: tuple[ServoState, ...]
    driver: str


def with_angle(snapshot: ServoSnapshot, channel: int, angle: float) -> ServoSnapshot:
    """Return ``snapshot`` with ``channel``'s angle replaced.

    The optimistic snapshot a panel broadcasts the instant a slider is released — peers
    update without anyone re-reading the backend (cheap locally, no extra HTTP live).
    """
    return replace(
        snapshot,
        states=tuple(
            replace(s, angle=angle) if s.channel == channel else s for s in snapshot.states
        ),
    )


def with_calibration(
    snapshot: ServoSnapshot, channel: int, calibration: float
) -> ServoSnapshot:
    """Return ``snapshot`` with ``channel``'s mid-point trim replaced (see :func:`with_angle`)."""
    return replace(
        snapshot,
        states=tuple(
            replace(s, calibration=calibration) if s.channel == channel else s
            for s in snapshot.states
        ),
    )


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

    def snapshot(self) -> ServoSnapshot:
        """States + driver name — the snapshot the panel syncs across clients.

        Concrete on the interface (mirrors :meth:`ControlsBackend.selection`): a single
        read covers both, so the live HTTP client fetches once rather than twice.
        """
        return ServoSnapshot(states=tuple(self.servos()), driver=self.driver_label())


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
