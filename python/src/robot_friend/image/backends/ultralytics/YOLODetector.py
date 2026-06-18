from enum import Enum

import numpy as np

from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType
from robot_friend.image.image_detector import ImageDetector
from robot_friend.resource_handler import get_yolo_model_dir


class YOLOModel(Enum):
    YOLO_V8N = "yolov8n.pt"


class YoloImageDetector(ImageDetector):
    """Laptop backend. On the Pi this is replaced by IMX500/Hailo."""

    def __init__(self, model: YOLOModel, conf: float = 0.4):
        # Imported lazily (like camera.py's picamera2) so this module and the YOLOModel
        # enum stay importable without the `yolo` extra — e.g. on the Pi, where
        # inference runs on the Hailo HAT, or in a diagnostics-only environment.
        from ultralytics import YOLO

        model_dir = get_yolo_model_dir() / model.value
        assert model_dir.exists(), f"Did not find model at path {model_dir}"
        self.model = YOLO(model_dir)
        self.conf = conf

    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        predictions = self.model.predict(
            image, classes=self.get_classes_to_predict(), conf=self.conf, verbose=False
        )
        out: list[DetectedObject] = []
        for pred in predictions:
            for b in pred.boxes:
                x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
                out.append(
                    DetectedObject(
                        DetectedObjectType.from_coco_class_id(int(b.cls[0])),
                        BoundingBox(x1, y1, x2, y2),
                        float(b.conf[0]),
                    )
                )
        return out
