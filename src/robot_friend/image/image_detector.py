from abc import ABC, abstractmethod

import numpy as np

from robot_friend.image.detection import DetectedObject, DetectedObjectType


class ImageDetector(ABC):
    """Backend-agnostic object detector over single image frames.

    Concrete backends (Hailo on the Pi, YOLO on a laptop) implement :meth:`detect`;
    ``ImageDetectorFactory`` picks one per host. Mirrors the audio side's ``AudioDetector``.
    """

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        """Detect known objects in a BGR ``image``.

        Returns:
            One :class:`DetectedObject` per accepted bounding box.
        """

    @staticmethod
    def get_classes_to_predict() -> list[int]:
        """Return the COCO class ids worth keeping; backends drop everything else."""
        return [object_type.value.coco_class_id for object_type in DetectedObjectType]
