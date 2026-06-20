import pytest

from robot_friend.image.detection import BoundingBox
from robot_friend.utils.coordinates.conversion import (
    bounding_box_to_coordinate,
    bounding_box_to_coordinate_in,
)


class _FakeFrame:
    """Minimal FrameSized stand-in (avoids needing real camera hardware)."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height


def test_center_box_maps_to_origin():
    box = BoundingBox(40, 30, 60, 50)  # center at (50, 40)
    coord = bounding_box_to_coordinate(box, frame_width=100, frame_height=80)
    assert (coord.pos_x, coord.pos_y) == (0.0, 0.0)


def test_corners_map_to_frame_edges():
    box = BoundingBox(0, 0, 100, 80)  # spans the whole frame, center (50, 40)
    coord = bounding_box_to_coordinate(box, frame_width=100, frame_height=80)
    assert (coord.pos_x, coord.pos_y) == (0.0, 0.0)


def test_top_left_corner_box_is_left_and_up():
    box = BoundingBox(0, 0, 0, 0)  # degenerate box at the top-left pixel
    coord = bounding_box_to_coordinate(box, frame_width=100, frame_height=80)
    assert coord.pos_x == -1.0  # far left
    assert coord.pos_y == 1.0  # top of frame -> +y (y-up flip)


def test_bottom_right_corner_box_is_right_and_down():
    box = BoundingBox(100, 80, 100, 80)
    coord = bounding_box_to_coordinate(box, frame_width=100, frame_height=80)
    assert coord.pos_x == 1.0  # far right
    assert coord.pos_y == -1.0  # bottom of frame -> -y


def test_offset_target_keeps_sign_convention():
    # Center at (75, 20) in a 100x80 frame: right of center, above center.
    box = BoundingBox(70, 10, 80, 30)
    coord = bounding_box_to_coordinate(box, frame_width=100, frame_height=80)
    assert coord.pos_x == pytest.approx(0.5)  # right -> positive x
    assert coord.pos_y == pytest.approx(0.5)  # upper half -> positive y


@pytest.mark.parametrize('width,height', [(0, 80), (100, 0), (-100, 80)])
def test_non_positive_frame_size_raises(width, height):
    with pytest.raises(ValueError):
        bounding_box_to_coordinate(BoundingBox(0, 0, 1, 1), width, height)


def test_in_frame_reads_dimensions_from_source():
    box = BoundingBox(70, 10, 80, 30)  # center (75, 20)
    frame = _FakeFrame(width=100, height=80)
    coord = bounding_box_to_coordinate_in(box, frame)
    assert coord.pos_x == pytest.approx(0.5)
    assert coord.pos_y == pytest.approx(0.5)


def test_in_frame_matches_explicit_call():
    box = BoundingBox(10, 20, 50, 60)
    frame = _FakeFrame(width=320, height=240)
    assert bounding_box_to_coordinate_in(box, frame) == bounding_box_to_coordinate(
        box, 320, 240
    )
