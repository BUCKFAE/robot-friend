from dataclasses import dataclass
from enum import Enum

from robot_friend.audio.keywords.keyword import DetectedSpeechKeyword


class Language(Enum):
    """Languages we transcribe, keyed by ISO 639-1 code."""
    ENGLISH = 'en'
    GERMAN = 'de'

    @classmethod
    def from_code(cls, code: str | None) -> "Language":
        for language in cls:
            if language.value == code:
                return language
        raise ValueError(f'Unknown language code: \'{code}\'')


@dataclass
class Transcript:
    """Transcript of one utterance.

    Attributes:
        text: The recognized text, or None if nothing was recognized.
        keywords: Keywords spotted in the utterance, if any.
        language: The detected language, or None if unknown.
        language_probability: Confidence in the detected language, in [0, 1].
    """
    text: str | None
    keywords: list[DetectedSpeechKeyword] | None = None
    language: Language | None = None
    language_probability: float = 0.0

    def as_log_line(self) -> str:
        """Returns a one-line summary, preferring spotted keywords over raw text."""
        if self.keywords:
            return ", ".join(d.keyword.name for d in self.keywords)

        return self.text or "No output"

