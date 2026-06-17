from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

@dataclass
class SpeechKeywordConfig:
    aliases_en: list[str]
    aliases_de: list[str]

    @property
    def aliases(self) -> list[str]:
        return self.aliases_en + self.aliases_de


class SpeechKeyword(Enum):
    """Words/phrases that trigger an action. We match every language's aliases
    regardless of the detected language: Whisper's language guess is unreliable
    on the short utterances keywords tend to be, and the alias sets don't clash."""
    YES = SpeechKeywordConfig(
        aliases_en=['yes'],
        aliases_de=['ja'],
    )
    NO = SpeechKeywordConfig(
        aliases_en=['no'],
        aliases_de=['nein'],
    )


@dataclass
class DetectedSpeechKeyword:
    """A keyword spotted in a :class:`Transcript`."""
    keyword: SpeechKeyword
    matched_alias: str

