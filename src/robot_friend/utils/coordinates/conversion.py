"""Conversions between the image pixel frame and the robot's aiming frame.

Keeping the flip-and-normalize math in one place ensures every consumer
(servo aiming, face targeting, Lidar fusion) reads coordinates the same way.
"""

from typing import Protocol

from robot_friend.image.detection import BoundingBox
from robot_friend.utils.coordinates.coordinate import Coordinate


class FrameSized(Protocol):
    """Anything that knows its frame dimensions in pixels (e.g. a ``Camera``).

    Declared structurally so this module stays decoupled from the hardware
    layer: any frame source exposing ``width``/``height`` qualifies.
    """

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...


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


def bounding_box_to_coordinate_in(box: BoundingBox, frame: FrameSized) -> Coordinate:
    """Maps a bounding box to the robot frame using a source's dimensions.

    Convenience wrapper over ``bounding_box_to_coordinate`` that reads the
    frame size straight off the producing source (e.g. the ``Camera``), so
    callers do not hand-pass width and height.

    Args:
        box: The detection's bounding box in image pixel coordinates.
        frame: The source the box was produced against (must expose
            ``width``/``height``, e.g. a ``Camera``).

    Returns:
        The box center expressed in the robot's aiming frame.

    Raises:
        ValueError: If the source reports a non-positive width or height.
    """
    return bounding_box_to_coordinate(box, frame.width, frame.height)
