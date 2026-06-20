"""In-memory PWM driver for running and debugging servos with no hardware attached.

Records the last window written to each channel and logs every write, so the same servo code
path (and the dashboard) runs on a laptop exactly as on the Pi — just without an I2C bus. This
is the no-hardware analog of the dashboard's demo :class:`DashboardControls`.
"""
from __future__ import annotations

from robot_friend.servo.pwm_driver import (
    PwmChannelState,
    PwmDriver,
    clamp_counts,
    validate_channel,
)
from robot_friend.utils.finch_logger import finch_logger

_DEFAULT_PWM_FREQ_HZ = 50.0


class FakePwmDriver(PwmDriver):
    """A PWM driver that writes nowhere but remembers what it was told."""

    def __init__(self, *, pwm_freq_hz: float = _DEFAULT_PWM_FREQ_HZ) -> None:
        self._pwm_freq_hz = float(pwm_freq_hz)
        self._channels: dict[int, PwmChannelState] = {}

    @property
    def pwm_frequency_hz(self) -> float:
        return self._pwm_freq_hz

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        validate_channel(channel)
        state = PwmChannelState(clamp_counts(on), clamp_counts(off))
        self._channels[channel] = state
        finch_logger.debug(
            "fake pwm: channel %d on=%d off=%d (duty %.0f%%)",
            channel,
            state.on,
            state.off,
            state.duty * 100,
        )

    def channel_state(self, channel: int) -> PwmChannelState:
        """Return the last window written to ``channel`` (zeros if it was never written)."""
        validate_channel(channel)
        return self._channels.get(channel, PwmChannelState(0, 0))
