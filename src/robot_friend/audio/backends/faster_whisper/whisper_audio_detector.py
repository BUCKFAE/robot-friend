from enum import Enum

from robot_friend.audio.audio_model import AudioModel
from robot_friend.audio.transcript import Language
from robot_friend.utils.ABCEnumMeta import ABCEnumMeta


class WhisperModel(AudioModel, Enum, metaclass=ABCEnumMeta):
    TINY = 'tiny'
    BASE = 'base'
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE_V3_TURBO = 'large-v3-turbo'

    def get_name(self) -> str:
        return self.name


class WhisperAudioDetector:

    def __init__(self, model: WhisperModel, language: Language | None = None):
        raise NotImplementedError
