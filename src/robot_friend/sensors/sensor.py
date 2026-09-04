from abc import ABC, abstractmethod
from typing import Self

from robot_friend.sensors.calibration import IdentityCalibration, SensorCalibration
from robot_friend.sensors.sensor_reading import SensorReading


class Sensor[ReadingT: SensorReading](ABC):
    """A sensor that can be read on demand.

    Backends implement :meth:`read_raw`; the calibration is applied here, so no backend
    has to remember to do it and no caller has to ask whether a reading is corrected.
    """

    def __init__(self, *, calibration: SensorCalibration[ReadingT] | None = None) -> None:
        self._calibration: SensorCalibration[ReadingT] = calibration or IdentityCalibration()

    @property
    def calibration(self) -> SensorCalibration[ReadingT]:
        return self._calibration

    def apply_calibration(self, calibration: SensorCalibration[ReadingT]) -> None:
        """Use ``calibration`` for subsequent reads."""
        self._calibration = calibration

    def read(self) -> ReadingT:
        """Take one calibrated reading.

        Raises:
            SensorReadException: If the reading could not be taken.
        """
        return self._calibration.apply(self.read_raw())

    @abstractmethod
    def read_raw(self) -> ReadingT:
        """Take one uncalibrated reading."""

    def close(self) -> None:
        """Release hardware resources. Safe to call repeatedly; a no-op by default."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
