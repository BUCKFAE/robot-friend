from enum import Enum

from robot_friend.speech.backends.vosk.vosk_model import VoskModel
from robot_friend.speech.backends.vosk.vosk_speech_detector import VoskSpeechDetector
from robot_friend.speech.speech_detector import SpeechDetector
from robot_friend.speech.transcript import Language

class SpeechDetectorFactory:

    @staticmethod
    def get_speech_detector(languages: list[Language] | None = None) -> SpeechDetector:
        """
        Build speech detector with the selected model, picks a sane default if not provided

        TODO: Implement this properly
        """
        return VoskSpeechDetector([VoskModel.VOSK_SMALL_DE_015])

