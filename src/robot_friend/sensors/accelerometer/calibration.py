from dataclasses import dataclass

from robot_friend.sensors.accelerometer.acceleration import Acceleration
from robot_friend.sensors.calibration import SensorCalibration


@dataclass(frozen=True, slots=True)
class AccelerometerCalibration(SensorCalibration[Acceleration]):
    """Per-axis correction applied as ``(raw - offset) * scale``.

    Attributes:
        offset: Zero-g offset per axis, in m/s^2.
        scale: Sensitivity correction per axis, dimensionless.
    """
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def apply(self, reading: Acceleration) -> Acceleration:
        offset_x, offset_y, offset_z = self.offset
        scale_x, scale_y, scale_z = self.scale
        return Acceleration(
            x=(reading.x - offset_x) * scale_x,
            y=(reading.y - offset_y) * scale_y,
            z=(reading.z - offset_z) * scale_z,
            timestamp=reading.timestamp,
        )
