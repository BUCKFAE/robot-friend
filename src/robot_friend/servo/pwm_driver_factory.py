"""Picks a concrete :class:`PwmDriver` for the current host.

On a Raspberry Pi it drives the real PCA9685; everywhere else — or if the I2C bus can't be
opened — it returns the in-memory :class:`FakePwmDriver`, so servo code and the dashboard run
unchanged with no hardware. Mirrors :class:`ImageDetectorFactory`.
"""
from __future__ import annotations

from robot_friend.exceptions.missing_hardware_exception import MissingI2cBusException
from robot_friend.servo.pwm_driver import PwmDriver
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host


class PwmDriverFactory:

    @staticmethod
    def get_pwm_driver(
        *,
        bus: int = 1,
        address: int = 0x40,
        pwm_freq_hz: float = 50.0,
    ) -> PwmDriver:
        """Return a real PCA9685 driver on the Pi, otherwise (or on failure) a fake one.

        Args:
            bus: I2C bus number for the real driver.
            address: I2C address of the PCA9685.
            pwm_freq_hz: PWM refresh rate for whichever backend is chosen.
        """
        if is_pi_host():
            from robot_friend.servo.backends.pca9685.pca9685_pwm_driver import (
                Pca9685PwmDriver,
            )
            try:
                return Pca9685PwmDriver(bus=bus, address=address, pwm_freq_hz=pwm_freq_hz)
            except MissingI2cBusException as exc:
                # I2C disabled or no board wired: fall back so the robot still runs (and the
                # dashboard still renders) without servos, rather than crashing the process.
                finch_logger.warning("PCA9685 unavailable (%s); using FakePwmDriver", exc)
        else:
            finch_logger.info("not a Pi host; using FakePwmDriver for servos")

        from robot_friend.servo.backends.fake.fake_pwm_driver import FakePwmDriver
        return FakePwmDriver(pwm_freq_hz=pwm_freq_hz)
