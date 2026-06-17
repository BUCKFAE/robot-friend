import re

from robot_friend.speech.keywords.keyword import DetectedSpeechKeyword, SpeechKeyword
from robot_friend.speech.transcript import Transcript


def match_keywords(transcript: Transcript) -> list[DetectedSpeechKeyword]:
    """Find every keyword whose alias occurs in ``transcript.text``.

    Matching is case-insensitive and on whole words only, so ``"no"`` triggers
    :attr:`SpeechKeyword.NO` while ``"nope"`` does not. Every language's aliases
    are tried regardless of the transcript's detected language (see
    :class:`SpeechKeyword`); a keyword is reported at most once, tagged with the
    first alias that matched.
    """
    text = transcript.text
    if not text:
        return []

    haystack = text.lower()
    detected: list[DetectedSpeechKeyword] = []
    for keyword in SpeechKeyword:
        for alias in keyword.value.aliases:
            if re.search(rf'\b{re.escape(alias.lower())}\b', haystack):
                detected.append(DetectedSpeechKeyword(keyword=keyword, matched_alias=alias))
                break
    return detected
