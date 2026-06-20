"""Backend-agnostic 16-channel PWM driver — the robot's hardware seam for servos.

The only part of the servo stack that touches I2C is the driver, so this ABC is where we
abstract over "is real hardware attached or not". :class:`Pca9685PwmDriver` drives a physical
PCA9685 over I2C; :class:`FakePwmDriver` keeps channel state in memory so servos can be driven
and debugged with nothing wired up. ``PwmDriverFactory`` picks one per host. Mirrors the
``image`` subsystem's :class:`ImageDetector` ABC + ``backends/`` layout.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

#: Output channels a PCA9685 exposes (LED0..LED15).
CHANNEL_COUNT = 16
#: PWM resolution is 12-bit, so on/off tick counts run 0..4095.
MAX_COUNTS = 4095


@dataclass(frozen=True)
class PwmChannelState:
    """The last PWM window written to one channel.

    Attributes:
        on: Tick (0..4095) within the 4096-step period at which the output goes high.
        off: Tick (0..4095) at which the output goes low.
    """
    on: int
    off: int

    @property
    def duty(self) -> float:
        """Fraction of the period the output is high (``off`` over the full count range)."""
        return self.off / MAX_COUNTS


class PwmDriver(ABC):
    """A 16-channel PWM source. Servos and other actuators are built on top of this."""

    @property
    @abstractmethod
    def pwm_frequency_hz(self) -> float:
        """PWM refresh rate, shared by all channels (servos need it to size their pulses)."""

    @abstractmethod
    def set_pwm(self, channel: int, on: int, off: int) -> None:
        """Set a channel's high window: the output goes high at ``on`` and low at ``off``.

        Args:
            channel: Output channel, 0..15.
            on: Tick to go high, 0..4095.
            off: Tick to go low, 0..4095.
        """

    def set_duty_cycle(self, channel: int, duty: float) -> None:
        """Drive ``channel`` at a constant duty cycle (``0.0``..``1.0``), high from tick 0."""
        duty = min(1.0, max(0.0, duty))
        self.set_pwm(channel, 0, round(duty * MAX_COUNTS))

    def close(self) -> None:
        """Release hardware resources. Safe to call repeatedly; a no-op by default."""

    def __enter__(self) -> PwmDriver:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def validate_channel(channel: int) -> int:
    """Return ``channel`` if it is a valid 0..15 index, otherwise raise ``ValueError``."""
    if not 0 <= channel < CHANNEL_COUNT:
        raise ValueError(f"channel must be 0..{CHANNEL_COUNT - 1}, got {channel}")
    return channel


def clamp_counts(counts: int) -> int:
    """Clamp a tick count into the valid 0..4095 PWM range."""
    return min(MAX_COUNTS, max(0, int(counts)))
