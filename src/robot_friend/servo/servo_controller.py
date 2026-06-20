"""Robot-side servo state: owns the PWM driver + servos and bridges HTTP payloads.

Analogous to :class:`robot_friend.control.RobotControls` — thread-safe, owns the JSON shape
served at ``GET /servos.json`` and applies ``POST /servo`` commands. The same controller backs
the dashboard's demo mode (driving a :class:`FakePwmDriver`), so the UI exercises the real
servo path with no hardware.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from typing import Any

from robot_friend.servo.pwm_driver import PwmDriver
from robot_friend.servo.pwm_driver_factory import PwmDriverFactory
from robot_friend.servo.servo import Servo, ServoConfig, ServoState
from robot_friend.utils.finch_logger import finch_logger


@dataclass(frozen=True)
class ServoSpec:
    """Declares one servo wired to the robot.

    Attributes:
        channel: PCA9685 channel the servo is connected to.
        label: Human-readable name shown in the dashboard.
        config: Pulse/range tuning for the servo model.
    """
    channel: int
    label: str
    config: ServoConfig = field(default_factory=ServoConfig)


#: The robot's servos. Minimal starter layout — edit to match your build (channel/label/model).
DEFAULT_SERVOS: list[ServoSpec] = [
    ServoSpec(channel=0, label="pan"),
    ServoSpec(channel=1, label="tilt"),
]


class ServoController:
    """Owns the PWM driver + servos; thread-safe state for the HTTP endpoints and dashboard."""

    def __init__(
        self,
        driver: PwmDriver,
        specs: list[ServoSpec],
        *,
        center_on_start: bool = True,
    ) -> None:
        self._lock = threading.Lock()
        self._driver = driver
        self._servos: dict[int, Servo] = {
            spec.channel: Servo(driver, spec.channel, spec.config, label=spec.label)
            for spec in specs
        }
        if center_on_start:
            for servo in self._servos.values():
                servo.move_neutral()

    @classmethod
    def from_factory(cls, specs: list[ServoSpec] | None = None) -> ServoController:
        """Build a controller whose driver is chosen by :class:`PwmDriverFactory` (fake off-Pi)."""
        driver = PwmDriverFactory.get_pwm_driver()
        controller = cls(driver, specs if specs is not None else DEFAULT_SERVOS)
        finch_logger.info(
            "servo controller ready: %d servo(s) on %s",
            len(controller._servos),
            controller.driver_name,
        )
        return controller

    @property
    def driver_name(self) -> str:
        return type(self._driver).__name__

    def set_angle(self, channel: int, angle: float) -> None:
        """Command the servo on ``channel`` to ``angle`` degrees (a no-op if there is none)."""
        with self._lock:
            servo = self._servos.get(channel)
            if servo is None:
                finch_logger.warning("no servo on channel %s", channel)
                return
            servo.angle(angle)

    def move_neutral(self, channel: int) -> None:
        """Center the servo on ``channel`` (a no-op if there is none)."""
        with self._lock:
            servo = self._servos.get(channel)
            if servo is not None:
                servo.move_neutral()

    def set_calibration(self, channel: int, deviation: float) -> None:
        """Set a servo's mid-point trim (degrees) and re-apply its angle so it takes effect now."""
        with self._lock:
            servo = self._servos.get(channel)
            if servo is None:
                finch_logger.warning("no servo on channel %s", channel)
                return
            servo.calibrate(deviation)
            servo.angle(servo.current_angle)  # re-apply the request with the new trim

    def states(self) -> list[ServoState]:
        with self._lock:
            return [servo.state() for servo in self._servos.values()]

    def snapshot(self) -> dict[str, Any]:
        """The ``GET /servos.json`` payload: every servo's state + the active driver name."""
        return {
            "servos": [asdict(state) for state in self.states()],
            "driver": self.driver_name,
        }

    def apply(self, payload: dict[str, Any]) -> None:
        """Apply a ``POST /servo`` command.

        Recognized keys (alongside ``channel``): ``calibration`` to set the mid-point trim,
        ``neutral: true`` to center, or ``angle`` to move. ``calibration`` is applied first so
        a single command may both trim and move.
        """
        if payload.get("channel") is None:
            return
        channel = int(payload["channel"])
        if payload.get("calibration") is not None:
            self.set_calibration(channel, float(payload["calibration"]))
        if payload.get("neutral"):
            self.move_neutral(channel)
        elif payload.get("angle") is not None:
            self.set_angle(channel, float(payload["angle"]))
