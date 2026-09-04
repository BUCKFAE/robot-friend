"""In-memory accelerometer for running and testing with no hardware attached."""
import random

from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2, Acceleration
from robot_friend.sensors.accelerometer.accelerometer import Accelerometer
from robot_friend.sensors.calibration import SensorCalibration

_AT_REST = (0.0, 0.0, GRAVITY_MS2)


class FakeAccelerometer(Accelerometer):
    """Reports whatever it was last told, level and still by default."""

    def __init__(
        self,
        *,
        acceleration: tuple[float, float, float] = _AT_REST,
        noise: float = 0.0,
        seed: int | None = None,
        calibration: SensorCalibration[Acceleration] | None = None,
    ) -> None:
        """
        Args:
            acceleration: Starting x, y, z in m/s^2.
            noise: Peak jitter added per axis, in m/s^2. Zero by default so tests
                can assert exact values.
            seed: Seeds the jitter, for repeatable non-zero noise.
            calibration: Correction to apply to readings, if any.
        """
        super().__init__(calibration=calibration)
        self._acceleration = acceleration
        self._noise = noise
        self._random = random.Random(seed)

    def set_acceleration(self, *, x: float, y: float, z: float) -> None:
        """Set what subsequent reads report, in m/s^2."""
        self._acceleration = (x, y, z)

    def read_raw(self) -> Acceleration:
        x, y, z = (value + self._jitter() for value in self._acceleration)
        return Acceleration(x=x, y=y, z=z)

    def _jitter(self) -> float:
        return self._random.uniform(-self._noise, self._noise) if self._noise else 0.0
