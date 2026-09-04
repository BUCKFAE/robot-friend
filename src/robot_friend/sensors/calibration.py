from abc import ABC, abstractmethod

from robot_friend.sensors.sensor_reading import SensorReading


class SensorCalibration[ReadingT: SensorReading](ABC):
    """Correction a sensor applies to every reading it produces.

    A value object rather than a method on the sensor, so a calibration measured once
    can be stored and handed back at startup.
    """

    @abstractmethod
    def apply(self, reading: ReadingT) -> ReadingT:
        """Return ``reading`` corrected, keeping its timestamp."""


class IdentityCalibration[ReadingT: SensorReading](SensorCalibration[ReadingT]):
    """What an uncalibrated sensor uses: hands every reading back untouched."""

    def apply(self, reading: ReadingT) -> ReadingT:
        return reading
