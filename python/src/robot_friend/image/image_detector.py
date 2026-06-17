from abc import ABC, abstractmethod

import numpy as np

from robot_friend.image.detection import DetectedObject


class ImageDetector(ABC):
    """
    TODO: Unify naming for images / speech
    """

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        pass
