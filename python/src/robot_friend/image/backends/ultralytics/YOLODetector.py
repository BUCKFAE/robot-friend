from enum import Enum

import numpy as np
from ultralytics import YOLO

from robot_friend.image.detection import DetectedObject, DetectedObjectType, BoundingBox
from robot_friend.image.detector import ImageDetector
from robot_friend.resource_handler import get_yolo_model_dir


class YOLOModel(Enum):
    YOLO_V8N = 'yolov8n.pt'

class YoloImageDetector(ImageDetector):
    """Laptop backend. On the Pi this is replaced by IMX500/Hailo."""
    def __init__(self, model: YOLOModel, conf: float = 0.4):
        model_dir = get_yolo_model_dir() / model.value
        assert model_dir.exists(), f'Did not find model at path {model_dir}'
        self.model = YOLO(model_dir)
        self.conf = conf


    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        res = self.model.predict(image, classes=[DetectedObjectType.PERSON.value.coco_class_id], conf=self.conf, verbose=False)[0]
        out: list[DetectedObject] = []
        for b in res.boxes:
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
            out.append(DetectedObject(
                DetectedObjectType.PERSON,
                BoundingBox(x1, y1, x2, y2), float(b.conf[0])))
        return out

