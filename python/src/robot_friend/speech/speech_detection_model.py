from abc import ABC, abstractmethod




class SpeechDetectionModel(ABC):

    @abstractmethod
    def get_name(self) -> str:
        pass