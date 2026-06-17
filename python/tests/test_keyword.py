from robot_friend.speech.keywords.keyword import SpeechKeyword
from robot_friend.speech.keywords.match_keywords import match_keywords
from robot_friend.speech.transcript import Language, Transcript


def _transcript(text: str, language: Language | None = Language.ENGLISH) -> Transcript:
    return Transcript(text=text, language=language)


def test_matches_english_and_german_aliases():
    yes = match_keywords(_transcript('Yes, please!'))
    assert [d.keyword for d in yes] == [SpeechKeyword.YES]
    assert yes[0].matched_alias == 'yes'

    # German is matched even when the transcript was tagged English.
    assert [d.keyword for d in match_keywords(_transcript('ja'))] == [SpeechKeyword.YES]


def test_matches_on_whole_words_only():
    # "nope" contains "no" but must not trigger the NO keyword.
    assert match_keywords(_transcript('nope')) == []
    assert [d.keyword for d in match_keywords(_transcript('no'))] == [SpeechKeyword.NO]


def test_no_keywords_returns_empty():
    assert match_keywords(_transcript('the weather is nice today')) == []
