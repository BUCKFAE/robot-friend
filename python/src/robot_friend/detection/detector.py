from abc import ABC, abstractmethod

import numpy as np

from robot_friend.detection.detection import DetectedObject


class Detector(ABC):

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[DetectedObject]:
        pass
