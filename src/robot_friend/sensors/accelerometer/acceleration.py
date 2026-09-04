import math
from dataclasses import dataclass

from robot_friend.sensors.sensor_reading import SensorReading

#: Standard gravity, in m/s^2. A level, still sensor reads this as its magnitude.
GRAVITY_MS2 = 9.80665


@dataclass(frozen=True, kw_only=True, slots=True)
class Acceleration(SensorReading):
    """Proper acceleration along the sensor's own axes, in m/s^2.

    Axes are the sensor's, not the robot's: how they map onto the robot depends on
    how the part is mounted, the way ``BoundingBox`` is in the image frame rather
    than the aiming frame. At rest the vector points *up* with magnitude ~9.81.

    Attributes:
        x: Acceleration along the sensor's x axis.
        y: Acceleration along the sensor's y axis.
        z: Acceleration along the sensor's z axis.
    """
    x: float
    y: float
    z: float

    @property
    def magnitude(self) -> float:
        """Length of the acceleration vector, in m/s^2."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
