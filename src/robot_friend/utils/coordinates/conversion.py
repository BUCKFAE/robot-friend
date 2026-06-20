"""Conversions between the image pixel frame and the robot's aiming frame.

Keeping the flip-and-normalize math in one place ensures every consumer
(servo aiming, face targeting, Lidar fusion) reads coordinates the same way.
"""

from robot_friend.image.detection import BoundingBox
from robot_friend.utils.coordinates.coordinate import Coordinate


def bounding_box_to_coordinate(
    box: BoundingBox, frame_width: int, frame_height: int
) -> Coordinate:
    """Maps a pixel-space bounding box to a robot-frame aiming coordinate.

    Takes the box center in image pixels (top-left origin, y-down) and converts
    it to the robot's aiming frame (center origin, y-up, normalized to [-1, 1]).
    See ``Coordinate`` for the target frame's definition.

    Args:
        box: The detection's bounding box in image pixel coordinates.
        frame_width: Width of the source frame in pixels (must be > 0).
        frame_height: Height of the source frame in pixels (must be > 0).

    Returns:
        The box center expressed in the robot's aiming frame.

    Raises:
        ValueError: If ``frame_width`` or ``frame_height`` is not positive.
    """
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError(
            f'Frame size must be positive, got {frame_width}x{frame_height}'
        )

    center_x = (box.x1 + box.x2) / 2
    center_y = (box.y1 + box.y2) / 2

    pos_x = (2 * center_x - frame_width) / frame_width
    pos_y = (frame_height - 2 * center_y) / frame_height
    return Coordinate(pos_x=pos_x, pos_y=pos_y)
