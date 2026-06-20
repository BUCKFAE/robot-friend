from dataclasses import dataclass


@dataclass
class Coordinate:
    """A 2D point in the robot's aiming frame.

    The origin is the *center* of the camera frame, with +x pointing right and
    +y pointing *up* (math convention, not image convention). Values are
    normalized so the frame spans roughly [-1, 1] on each axis: (0, 0) is dead
    ahead, x = -1/+1 the left/right edge, y = -1/+1 the bottom/top edge. This
    keeps targets resolution-independent and lets the sign read directly as a
    steering direction (negative x -> turn left, positive y -> look up).

    This is distinct from the image pixel frame used by
    ``robot_friend.image.detection.BoundingBox`` (top-left origin, y-down,
    absolute pixels). Convert between them with ``bounding_box_to_coordinate``.

    Attributes:
        pos_x: Horizontal offset from center, normalized to [-1, 1] (+ = right).
        pos_y: Vertical offset from center, normalized to [-1, 1] (+ = up).
    """
    pos_x: float
    pos_y: float
