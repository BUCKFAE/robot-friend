import numpy as np

from robot_friend.image.backends.hailo.HailoDetector import HailoImageDetector
from robot_friend.image.detection import DetectedObjectType


def _empty_output() -> list[np.ndarray]:
    return [np.empty((0, 5), dtype=np.float32) for _ in range(80)]


def test_parse_output_scales_and_filters():
    output = _empty_output()
    output[0] = np.array([
        [0.1, 0.2, 0.5, 0.6, 0.9],  # (y0, x0, y1, x1, score)
        [0.0, 0.0, 1.0, 1.0, 0.2],  # below confidence threshold
    ], dtype=np.float32)

    detections = HailoImageDetector.parse_output(output, width=1000, height=500, conf=0.4)

    assert len(detections) == 1
    d = detections[0]
    assert d.detected_object_type == DetectedObjectType.PERSON
    assert (d.bounding_box.x1, d.bounding_box.y1) == (200, 50)
    assert (d.bounding_box.x2, d.bounding_box.y2) == (600, 250)
    assert d.confidence == np.float32(0.9)


def test_parse_output_ignores_other_classes():
    output = _empty_output()
    output[16] = np.array([[0.1, 0.2, 0.5, 0.6, 0.9]], dtype=np.float32)  # dog

    assert HailoImageDetector.parse_output(output, width=640, height=480, conf=0.4) == []
