from pathlib import Path

import cv2
import numpy as np

from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.image.image_detector import ImageDetector

# Shipped by the hailo-models apt package (see scripts/setup.sh).
_MODEL_DIR = Path('/usr/share/hailo-models')
_HEF_MODEL = 'yolov8s_h8.hef'


class HailoImageDetector(ImageDetector):
    """Pi backend: runs a YOLOv8 HEF on the AI HAT via HailoRT.

    Needs the apt packages installed by `just setup` and a venv created with
    --system-site-packages (`just sync`) so the picamera2 Hailo bindings are
    importable.
    """

    def __init__(self, conf: float = 0.4):
        from picamera2.devices import Hailo  # only importable on the Pi

        model_path = _MODEL_DIR / _HEF_MODEL
        if not model_path.exists():
            raise FileNotFoundError(f'Did not find HEF model at path {model_path}')
        self.hailo = Hailo(str(model_path))
        self.input_h, self.input_w, _ = self.hailo.get_input_shape()
        self.conf = conf


    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.input_w, self.input_h))
        output = self.hailo.run(resized)
        height, width = image.shape[:2]
        return self.parse_output(output, width, height, self.conf)

    @staticmethod
    def parse_output(output, width: int, height: int, conf: float) -> list[DetectedObject]:
        """The HEF runs NMS on-chip: output is one (N, 5) array per COCO class
        with rows of normalized (y0, x0, y1, x1, score)."""
        out: list[DetectedObject] = []
        for y0, x0, y1, x1, score in output[DetectedObjectType.PERSON.value.coco_class_id]:
            if score < conf:
                continue
            box = BoundingBox(int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
            out.append(DetectedObject(DetectedObjectType.PERSON, box, float(score)))
        return out
