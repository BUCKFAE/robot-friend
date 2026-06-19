from dataclasses import dataclass


@dataclass
class Coordinate:
    """A 2D point in the robot's frame.

    Attributes:
        pos_x: Horizontal position.
        pos_y: Vertical position.
    """
    # TODO: Define where the origin is.
    pos_x: int
    pos_y: int
