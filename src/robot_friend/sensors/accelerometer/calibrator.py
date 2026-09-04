"""Measuring an accelerometer's calibration from the six axis-aligned orientations."""
import time
from dataclasses import dataclass
from enum import Enum

from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2, Acceleration
from robot_friend.sensors.accelerometer.accelerometer import Accelerometer
from robot_friend.sensors.accelerometer.calibration import AccelerometerCalibration

_AXES = ('x', 'y', 'z')


@dataclass(frozen=True)
class OrientationConfig:
    """Attributes:
        axis: Index of the axis under test, 0..2 for x, y, z.
        sign: +1 when that axis points up, -1 when it points down.
        instruction: What the person holding the sensor has to do.
    """
    axis: int
    sign: int
    instruction: str


class AccelerometerOrientation(Enum):
    """The six placements a full calibration needs."""
    X_UP = OrientationConfig(0, +1, 'x axis pointing up')
    X_DOWN = OrientationConfig(0, -1, 'x axis pointing down')
    Y_UP = OrientationConfig(1, +1, 'y axis pointing up')
    Y_DOWN = OrientationConfig(1, -1, 'y axis pointing down')
    Z_UP = OrientationConfig(2, +1, 'z axis pointing up (flat, chip facing up)')
    Z_DOWN = OrientationConfig(2, -1, 'z axis pointing down (flat, chip facing down)')


class AccelerometerCalibrator:
    """Collects the six orientations and solves them for offset and scale.

    Each axis is measured once pointing up (+1 g) and once down (-1 g). The midpoint of
    those two is the zero-g offset and their span is the sensitivity, which is why one
    orientation is not enough. Readings are taken uncalibrated, so re-running a
    calibration never stacks on top of the last one.
    """

    def __init__(
        self,
        accelerometer: Accelerometer,
        *,
        samples: int = 100,
        delay: float = 0.01,
    ) -> None:
        """
        Args:
            accelerometer: The sensor being calibrated.
            samples: Readings averaged per orientation, to smooth out noise.
            delay: Seconds between those readings.
        """
        self._accelerometer = accelerometer
        self._samples = samples
        self._delay = delay
        self._measured: dict[AccelerometerOrientation, Acceleration] = {}

    def record(self, orientation: AccelerometerOrientation) -> Acceleration:
        """Average a burst of raw readings and keep them as this orientation's measurement."""
        totals = [0.0, 0.0, 0.0]
        for _ in range(self._samples):
            reading = self._accelerometer.read_raw()
            for axis, value in enumerate(_components(reading)):
                totals[axis] += value
            time.sleep(self._delay)
        mean = Acceleration(
            x=totals[0] / self._samples,
            y=totals[1] / self._samples,
            z=totals[2] / self._samples,
        )
        self._measured[orientation] = mean
        return mean

    @property
    def missing(self) -> list[AccelerometerOrientation]:
        """Orientations still to be recorded, in the order they should be asked for."""
        return [o for o in AccelerometerOrientation if o not in self._measured]

    def calibration(self) -> AccelerometerCalibration:
        """Solve the recorded orientations for a calibration.

        Raises:
            SensorCalibrationException: If an orientation is missing, or an axis read
                the same up as down — the sensor was not actually turned, or it is dead.
        """
        if self.missing:
            raise SensorCalibrationException(
                'still need: ' + ', '.join(o.name for o in self.missing)
            )

        offsets: list[float] = []
        scales: list[float] = []
        for axis in range(3):
            up = _components(self._measured[_orientation(axis, +1)])[axis]
            down = _components(self._measured[_orientation(axis, -1)])[axis]
            span = up - down
            if span <= 0:
                raise SensorCalibrationException(
                    f'{_AXES[axis]} axis read {up:.2f} up and {down:.2f} down '
                    f'(m/s^2); it should swing by 2 g between them'
                )
            offsets.append((up + down) / 2)
            scales.append(2 * GRAVITY_MS2 / span)

        return AccelerometerCalibration(
            offset=(offsets[0], offsets[1], offsets[2]),
            scale=(scales[0], scales[1], scales[2]),
        )


def _components(reading: Acceleration) -> tuple[float, float, float]:
    return reading.x, reading.y, reading.z


def _orientation(axis: int, sign: int) -> AccelerometerOrientation:
    for orientation in AccelerometerOrientation:
        if orientation.value.axis == axis and orientation.value.sign == sign:
            return orientation
    raise ValueError(f'no orientation for axis {axis} sign {sign}')
