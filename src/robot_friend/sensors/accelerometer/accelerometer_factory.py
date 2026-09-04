from robot_friend.exceptions.missing_hardware_exception import MissingHardwareException
from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.sensors.accelerometer.acceleration import Acceleration
from robot_friend.sensors.accelerometer.accelerometer import Accelerometer
from robot_friend.sensors.accelerometer.calibration_store import load_calibration
from robot_friend.sensors.calibration import SensorCalibration
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host


class AccelerometerFactory:

    @staticmethod
    def get_accelerometer(
        *,
        bus: int = 1,
        address: int = 0x53,
        calibration: SensorCalibration[Acceleration] | None = None,
    ) -> Accelerometer:
        """Return a real ADXL345 on the Pi, otherwise (or on failure) a fake one.

        Args:
            bus: I2C bus number for the real sensor.
            address: I2C address of the ADXL345 (``0x53``, or ``0x1D`` with SDO high).
            calibration: Correction to apply to readings. Omit it to use whatever
                ``robot-friend-calibrate`` last measured for this robot.
        """
        if calibration is None:
            calibration = _stored_calibration()

        if is_pi_host():
            from robot_friend.i2c.backends.smbus.smbus_i2c_device import SmbusI2cDevice
            from robot_friend.sensors.accelerometer.backends.adxl345.adxl345_accelerometer import (
                Adxl345Accelerometer,
            )
            try:
                device = SmbusI2cDevice(address=address, bus=bus)
                return Adxl345Accelerometer(device, calibration=calibration)
            except MissingHardwareException as exc:
                finch_logger.warning("ADXL345 unavailable (%s); using FakeAccelerometer", exc)
        else:
            finch_logger.info("not a Pi host; using FakeAccelerometer")

        from robot_friend.sensors.accelerometer.backends.fake.fake_accelerometer import (
            FakeAccelerometer,
        )
        return FakeAccelerometer(calibration=calibration)


def _stored_calibration() -> SensorCalibration[Acceleration] | None:
    """The calibration ``robot-friend-calibrate`` measured, if this robot has one."""
    try:
        calibration = load_calibration()
    except SensorCalibrationException as exc:
        # Running uncalibrated is better than refusing to start, but it must be loud.
        finch_logger.warning("ignoring the stored calibration: %s", exc)
        return None
    if calibration is not None:
        finch_logger.info("using the stored accelerometer calibration")
    return calibration
