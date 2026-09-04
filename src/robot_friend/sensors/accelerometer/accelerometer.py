from robot_friend.sensors.accelerometer.acceleration import Acceleration
from robot_friend.sensors.sensor import Sensor


class Accelerometer(Sensor[Acceleration]):
    """Backend-agnostic accelerometer: proper acceleration in m/s^2, sensor axes."""
