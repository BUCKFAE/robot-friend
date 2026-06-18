from abc import ABC, abstractmethod

import numpy as np

from robot_friend.image.detection import BoundingBox, DetectedObject, DetectedObjectType


class ImageDetector(ABC):
    """
    TODO: Unify naming for images / speech
    """

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        pass

    @staticmethod
    def get_classes_to_predict():
        return [object_type.value.coco_class_id for object_type in DetectedObjectType]
