from enum import Enum

from robot_friend.audio.backends.vosk.vosk_model import VoskModel
from robot_friend.audio.backends.vosk.vosk_audio_detector import VoskAudioDetector
from robot_friend.audio.audio_detector import AudioDetector
from robot_friend.audio.transcript import Language

class AudioDetectorFactory:

    @staticmethod
    def get_audio_detector(languages: list[Language] | None = None) -> AudioDetector:
        """
        Build speech detector with the selected model, picks a sane default if not provided

        TODO: Implement this properly
        """
        return VoskAudioDetector([VoskModel.VOSK_SMALL_DE_015])

