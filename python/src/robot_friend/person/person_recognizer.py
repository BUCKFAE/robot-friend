from abc import ABC, abstractmethod
from ultralytics import YOLO
from enum import Enum

from robot_friend.person.detection import DetectedObject, BoundingBox, DetectedObjectType
from robot_friend.resource_handler import get_model_dir


class PersonRecognizer(ABC):

    @abstractmethod
    def recognize_persons(self, image) -> list[DetectedObject]:
        pass

class YOLOModel(Enum):
    YOLO_V8N = 'yolov8n.pt'

class YoloDetector(PersonRecognizer):
    """Laptop backend. On the Pi this is replaced by IMX500/Hailo."""
    def __init__(self, model: YOLOModel, conf: float = 0.4):
        model_dir = get_model_dir() / model.value
        assert model_dir.exists(), f'Did not find model at path {model_dir}'
        self.model = YOLO(model_dir)
        self.conf = conf


    def recognize_persons(self, image) -> list[DetectedObject]:
        # class 0 == person (COCO)
        # TODO: Enum for coco classes
        res = self.model.predict(image, classes=[0], conf=self.conf, verbose=False)[0]
        out: list[DetectedObject] = []
        for b in res.boxes:
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
            out.append(DetectedObject(
                DetectedObjectType.PERSON,
                BoundingBox(x1, y1, x2, y2), float(b.conf[0])))
        return out

