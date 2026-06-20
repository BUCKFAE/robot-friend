"""Angle-controlled hobby servo on top of a backend-agnostic :class:`PwmDriver`.

Typed, project-style rewrite of the ``Servo`` class and group helpers from Stefan Saam's
MIT-licensed ``lib_PCA9685.py``. The angle→microsecond→counts mapping, mid-point calibration,
and move-timing are preserved; the servo talks to a :class:`PwmDriver` (real or fake) rather
than a concrete PCA9685, so identical code drives hardware on the Pi and the in-memory fake on
a laptop.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass

from robot_friend.servo.pwm_driver import PwmDriver
from robot_friend.utils.finch_logger import finch_logger

_STEPS_PER_PERIOD = 4096
_US_PER_SECOND = 1_000_000


@dataclass(frozen=True)
class ServoConfig:
    """Tunable pulse/range parameters for one servo model.

    Attributes:
        max_angle: Full sweep in degrees; the neutral position is half of this.
        min_us: Pulse width (µs) at angle 0.
        mid_us: Pulse width (µs) at the midpoint angle.
        max_us: Pulse width (µs) at ``max_angle``.
        moving_max_ms: Time budget (ms) for a full-range move, used to estimate when a
            commanded move has finished (see :func:`wait_all_servos`).
    """
    max_angle: float = 180.0
    min_us: float = 1000.0
    mid_us: float = 1500.0
    max_us: float = 2000.0
    moving_max_ms: float = 200.0


@dataclass(frozen=True)
class ServoState:
    """A servo's commanded state — the JSON shape shared by the robot and the dashboard.

    Attributes:
        channel: PWM channel the servo is wired to.
        label: Human-readable name for the UI.
        angle: Last *requested* angle in degrees (neutral until the first command);
            excludes calibration, so it matches the slider position.
        min_angle: Lowest settable angle (always 0).
        max_angle: Highest settable angle.
        off_counts: PWM off-tick last written for this angle (a debug readout).
        calibration: Mid-point calibration offset (degrees) applied on top of the request.
    """
    channel: int
    label: str
    angle: float
    min_angle: float
    max_angle: float
    off_counts: int
    calibration: float


class Servo:
    """Drives one servo channel by angle, with calibration and move-time tracking."""

    def __init__(
        self,
        driver: PwmDriver,
        channel: int,
        config: ServoConfig | None = None,
        *,
        label: str = "",
    ) -> None:
        """Bind a servo to a driver channel.

        Args:
            driver: The PWM source (real PCA9685 or fake) this servo writes to.
            channel: Output channel on the driver, 0..15.
            config: Pulse/range tuning; defaults to a standard 180° hobby servo.
            label: Human-readable name; defaults to ``"servo <channel>"``.
        """
        self._driver = driver
        self._channel = channel
        self._config = config or ServoConfig()
        self._label = label or f"servo {channel}"

        self._calib_mid = 0.0
        self._old_angle: float | None = None
        # The last *requested* angle (what the UI shows). Calibration is applied on top when
        # computing the pulse, so re-applying this after a calibration change can't drift.
        self._requested_angle = self._config.max_angle / 2
        self._last_off_counts = 0
        #: Monotonic deadline by which the most recent move should be finished (or ``None``).
        self.wait_until: float | None = None

        self._period_us = _US_PER_SECOND / driver.pwm_frequency_hz

    @property
    def channel(self) -> int:
        return self._channel

    @property
    def label(self) -> str:
        return self._label

    @property
    def config(self) -> ServoConfig:
        return self._config

    @property
    def current_angle(self) -> float:
        """Last *requested* angle (neutral before the first move); excludes calibration."""
        return self._requested_angle

    @property
    def calibration(self) -> float:
        """Mid-point calibration offset (degrees) applied to every commanded angle."""
        return self._calib_mid

    @property
    def last_off_counts(self) -> int:
        """PWM off-tick last written — handy for debugging with no hardware attached."""
        return self._last_off_counts

    def state(self) -> ServoState:
        """Snapshot for the dashboard / ``GET /servos.json``."""
        return ServoState(
            channel=self._channel,
            label=self._label,
            angle=self._requested_angle,
            min_angle=0.0,
            max_angle=self._config.max_angle,
            off_counts=self._last_off_counts,
            calibration=self._calib_mid,
        )

    def _us_to_counts(self, microseconds: float) -> int:
        return int((microseconds / self._period_us) * _STEPS_PER_PERIOD)

    def _limit_angle(self, angle: float) -> float:
        return max(0.0, min(self._config.max_angle, angle))

    def _calibrate(self, angle: float) -> float:
        """Apply the mid-point calibration offset, keeping the result within range."""
        angle = self._limit_angle(angle)
        half = self._config.max_angle / 2
        if angle <= half:
            fraction = (half + self._calib_mid) / half
        else:
            fraction = (half - self._calib_mid) / half
        angle = half + self._calib_mid + (angle - half) * fraction
        return self._limit_angle(angle)

    def calibrate(self, middle_angle_deviation: float | None = None) -> None:
        """Set the mechanical mid-point offset (degrees) applied to every commanded angle."""
        if middle_angle_deviation is not None:
            self._calib_mid = middle_angle_deviation

    def _set_wait_moving(self, old_angle: float | None, new_angle: float) -> None:
        budget_s = self._config.moving_max_ms / 1000
        if old_angle is not None:
            travel = abs(new_angle - old_angle) / self._config.max_angle
            self.wait_until = time.monotonic() + travel * budget_s
        else:
            self.wait_until = time.monotonic() + budget_s

    def angle(self, requested_angle: float) -> None:
        """Command the servo to ``requested_angle`` degrees (clamped to ``0..max_angle``).

        The mid-point calibration offset is applied on top of the request when computing the
        pulse; :attr:`current_angle` still reports the un-calibrated request.
        """
        requested = self._limit_angle(requested_angle)
        calibrated = self._calibrate(requested)
        half = self._config.max_angle / 2
        if calibrated <= half:
            microseconds = self._config.min_us + (
                calibrated / self._config.max_angle * 2
            ) * (self._config.mid_us - self._config.min_us)
        else:
            microseconds = self._config.mid_us + (
                (calibrated - half) / self._config.max_angle * 2
            ) * (self._config.max_us - self._config.mid_us)

        counts = self._us_to_counts(microseconds)
        self._set_wait_moving(self._old_angle, calibrated)
        self._old_angle = calibrated
        self._requested_angle = requested
        self._last_off_counts = counts
        finch_logger.debug(
            "servo %s -> %.1f° (cal %+.1f° -> %.0f µs, off=%d)",
            self._label,
            requested,
            self._calib_mid,
            microseconds,
            counts,
        )
        self._driver.set_pwm(self._channel, 0, counts)

    def move_neutral(self) -> None:
        """Move to the mid-point angle."""
        self.angle(self._config.max_angle / 2)


def wait_all_servos(servos: Iterable[Servo]) -> None:
    """Block until every servo's estimated move deadline has passed."""
    deadlines = [s.wait_until for s in servos if s.wait_until is not None]
    if not deadlines:
        return
    remaining = max(deadlines) - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)


def move_group(servo_angles: Iterable[tuple[Servo, float]]) -> None:
    """Command several servos together, then wait for the slowest to finish.

    Args:
        servo_angles: ``(servo, angle)`` pairs to move at once.
    """
    pairs = list(servo_angles)
    for servo, target in pairs:
        servo.angle(target)
    wait_all_servos([servo for servo, _ in pairs])
