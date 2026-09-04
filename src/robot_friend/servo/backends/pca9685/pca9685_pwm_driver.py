"""Real PCA9685 16-channel PWM driver over I2C.

Typed, project-style rewrite of Stefan Saam's MIT-licensed ``lib_PCA9685.py``
(https://github.com/outdoorbits/Simple-python3-library-for-PCA9685). The register sequence and
prescale math are preserved; the original ``smbus`` import is swapped for the project's
:class:`I2cDevice`, the four per-channel byte writes are coalesced into one auto-incremented
block write, and a board that does not answer is surfaced as
:class:`MissingI2cDeviceException` so the factory can fall back to the fake driver.
"""
from __future__ import annotations

import math
import time
from typing import Final

from robot_friend.exceptions.i2c_exception import I2cTransferException
from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.i2c.i2c_device import I2cDevice
from robot_friend.servo.pwm_driver import PwmDriver, clamp_counts, validate_channel

# PCA9685 registers.
_MODE1: Final = 0x00
_MODE2: Final = 0x01
_PRE_SCALE: Final = 0xFE
_LED0_ON_L: Final = 0x06

# MODE1 bits.
_RESTART: Final = 0x80
_SLEEP: Final = 0x10
_AUTO_INCREMENT: Final = 0x20

# MODE2 bits.
_OUTDRV: Final = 0x04  # totem-pole output, the usual default for servo-driver boards.

_DEFAULT_OSC_CLOCK_HZ: Final = 25_000_000
_STEPS_PER_PERIOD: Final = 4096
_REGISTERS_PER_CHANNEL: Final = 4


class Pca9685PwmDriver(PwmDriver):
    """Drives a physical PCA9685 through an :class:`I2cDevice`."""

    def __init__(
        self,
        device: I2cDevice,
        *,
        osc_clock_hz: int = _DEFAULT_OSC_CLOCK_HZ,
        pwm_freq_hz: float = 50.0,
    ) -> None:
        """Configure the device.

        Takes ownership of ``device`` and closes it if setup fails.

        Args:
            device: The PCA9685's place on the bus (``0x40`` by default).
            osc_clock_hz: Internal oscillator frequency used for the prescale calculation.
            pwm_freq_hz: PWM refresh rate; ``50`` Hz suits typical hobby servos.

        Raises:
            MissingI2cDeviceException: If no board answers at the device's address.
        """
        self._device = device
        self._osc_clock_hz = osc_clock_hz
        self._pwm_freq_hz = float(pwm_freq_hz)

        try:
            device.probe()
            self._init_device()
            self._set_pwm_freq(self._pwm_freq_hz)
        except I2cTransferException as exc:
            device.close()
            raise MissingI2cDeviceException(
                f"PCA9685 at {device.address:#04x} on I2C bus {device.bus_number} "
                f"answered but could not be configured"
            ) from exc
        except Exception:
            device.close()
            raise

    @property
    def pwm_frequency_hz(self) -> float:
        return self._pwm_freq_hz

    def _write8(self, register: int, value: int) -> None:
        self._device.write_byte(register, value)

    def _read8(self, register: int) -> int:
        return self._device.read_byte(register)

    def _init_device(self) -> None:
        self._write8(_MODE1, _AUTO_INCREMENT)
        self._write8(_MODE2, _OUTDRV)
        time.sleep(0.01)

    def _set_pwm_freq(self, pwm_freq_hz: float) -> None:
        prescale_value = (self._osc_clock_hz / (_STEPS_PER_PERIOD * pwm_freq_hz)) - 1.0
        prescale = int(math.floor(prescale_value + 0.5))

        old_mode = self._read8(_MODE1)
        sleep_mode = (old_mode & ~_RESTART) | _SLEEP  # the device must sleep to set the prescaler
        self._write8(_MODE1, sleep_mode)
        self._write8(_PRE_SCALE, prescale)
        self._write8(_MODE1, old_mode)
        time.sleep(0.005)
        self._write8(_MODE1, old_mode | _RESTART | _AUTO_INCREMENT)
        time.sleep(0.01)

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        validate_channel(channel)
        on = clamp_counts(on)
        off = clamp_counts(off)
        base = _LED0_ON_L + _REGISTERS_PER_CHANNEL * channel
        # Auto-increment is enabled, so the four LED registers (ON_L, ON_H, OFF_L, OFF_H) are
        # written in one block transaction instead of four separate byte writes.
        self._device.write_block(
            base,
            [on & 0xFF, (on >> 8) & 0xFF, off & 0xFF, (off >> 8) & 0xFF],
        )

    def close(self) -> None:
        self._device.close()
