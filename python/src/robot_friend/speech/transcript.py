from dataclasses import dataclass
from enum import Enum

from robot_friend.speech.keywords.keyword import DetectedSpeechKeyword


class Language(Enum):
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
    """
    Transcript of one utterance
    """
    text: str | None
    keywords: list[DetectedSpeechKeyword] | None = None
    language: Language | None = None
    language_probability: float = 0.0

    def as_log_line(self) -> str:

        if self.keywords:
            return ", ".join(d.keyword.name for d in self.keywords)

        return self.text or "No output"

