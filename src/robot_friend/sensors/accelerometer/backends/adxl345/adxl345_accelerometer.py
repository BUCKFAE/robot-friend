"""Real ADXL345 over I2C."""
from typing import Final

from robot_friend.exceptions.i2c_exception import I2cTransferException
from robot_friend.exceptions.missing_hardware_exception import MissingI2cDeviceException
from robot_friend.exceptions.sensor_exception import SensorReadException
from robot_friend.i2c.i2c_device import I2cDevice
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2, Acceleration
from robot_friend.sensors.accelerometer.accelerometer import Accelerometer
from robot_friend.sensors.calibration import SensorCalibration

# ADXL345 registers.
_DEVID: Final = 0x00
_BW_RATE: Final = 0x2C
_POWER_CTL: Final = 0x2D
_DATA_FORMAT: Final = 0x31
_DATAX0: Final = 0x32

_DEVICE_ID: Final = 0xE5  # the part always reports this; nothing else does
_MEASURE: Final = 0x08  # POWER_CTL: leave standby
_FULL_RES_2G: Final = 0x08  # DATA_FORMAT: full resolution, +/-2 g
_RATE_100_HZ: Final = 0x0A
_LSB_PER_G: Final = 256  # full resolution is 3.9 mg/LSB at every range
_MS2_PER_LSB: Final = GRAVITY_MS2 / _LSB_PER_G

_AXIS_BYTES: Final = 6  # DATAX0..DATAZ1, little-endian signed pairs


class Adxl345Accelerometer(Accelerometer):
    """Drives a physical ADXL345 through an :class:`I2cDevice`."""

    def __init__(
        self,
        device: I2cDevice,
        *,
        calibration: SensorCalibration[Acceleration] | None = None,
    ) -> None:
        """Confirm the part really is an ADXL345, then put it into measure mode.

        Takes ownership of ``device`` and closes it if setup fails.

        Args:
            device: The ADXL345's place on the bus (``0x53``, or ``0x1D`` with SDO high).
            calibration: Correction to apply to readings, if any.

        Raises:
            MissingI2cDeviceException: If nothing answers, or the part is not an ADXL345
                — a different board at that address, or CS left floating so it talks SPI.
        """
        super().__init__(calibration=calibration)
        self._device = device
        try:
            device.require_device_id(_DEVID, _DEVICE_ID)
            device.write_byte(_DATA_FORMAT, _FULL_RES_2G)
            device.write_byte(_BW_RATE, _RATE_100_HZ)
            device.write_byte(_POWER_CTL, _MEASURE)
        except I2cTransferException as exc:
            device.close()
            raise MissingI2cDeviceException(
                f"ADXL345 at {device.address:#04x} on I2C bus {device.bus_number} "
                f"answered but could not be configured"
            ) from exc
        except Exception:
            device.close()
            raise

    def read_raw(self) -> Acceleration:
        try:
            raw = self._device.read_block(_DATAX0, _AXIS_BYTES)
        except I2cTransferException as exc:
            raise SensorReadException(f"could not read the ADXL345: {exc}") from exc
        counts = [
            int.from_bytes(bytes(raw[index:index + 2]), "little", signed=True)
            for index in (0, 2, 4)
        ]
        x, y, z = (count * _MS2_PER_LSB for count in counts)
        return Acceleration(x=x, y=y, z=z)

    def close(self) -> None:
        self._device.close()
