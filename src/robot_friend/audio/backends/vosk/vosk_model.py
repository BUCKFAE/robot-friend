from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from robot_friend.exceptions.missing_model_exception import MissingModelException
from robot_friend.resource_handler import get_vosk_model_dir
from robot_friend.audio.audio_model import AudioModel
from robot_friend.audio.transcript import Language
from robot_friend.utils.ABCEnumMeta import ABCEnumMeta


@dataclass
class VoskModelConfig:
    identifier: str
    language: Language
    base_url: str = 'https://alphacephei.com/vosk/models'


class VoskModel(AudioModel, Enum, metaclass=ABCEnumMeta):
    """A Vosk model: a :class:`AudioModel` whose value is its
    :class:`VoskModelConfig` (accessed via :attr:`config`)."""

    VOSK_SMALL_EN_US_015 = VoskModelConfig('vosk-model-small-en-us-0.15', Language.ENGLISH)
    VOSK_SMALL_DE_015 = VoskModelConfig('vosk-model-small-de-0.15', Language.GERMAN)

    @property
    def config(self) -> VoskModelConfig:
        return self.value

    def get_name(self) -> str:
        return self.name

    def get_model_dir(self) -> Path:
        model_dir = get_vosk_model_dir() / self.config.identifier
        if not model_dir.exists():
            raise MissingVoskModelException(self)
        return model_dir


class MissingVoskModelException(MissingModelException):
    def __init__(self, missing_model: 'VoskModel'):
        super().__init__(
            f'Vosk model {missing_model.get_name()!r} '
            f'({missing_model.config.identifier}) is not downloaded.'
        )
        self.missing_model = missing_model
