from abc import ABC, abstractmethod

import numpy as np

from robot_friend.speech.transcript import Transcript


class SpeechDetector(ABC):
    """Turns a chunk of mono 16 kHz float32 audio into a :class:`Transcript`."""

    @property
    @abstractmethod
    def get_model_names(self) -> list[str]:
        ...


    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...

    @abstractmethod
    def transcribe(self, samples: np.ndarray) -> Transcript:
        ...
