from enum import Enum

from robot_friend.speech.speech_detection_model import SpeechDetectionModel
from robot_friend.speech.transcript import Language


class WhisperModel(Enum, SpeechDetectionModel):
    TINY = 'tiny'
    BASE = 'base'
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE_V3_TURBO = 'large-v3-turbo'

    def get_name(self) -> str:
        return self.name


class WhisperSpeechDetector:

    def __init__(self, model: WhisperModel, language: Language | None = None):
        raise NotImplementedError
