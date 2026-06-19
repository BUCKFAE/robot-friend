import json

import numpy as np

from robot_friend.audio.backends.vosk.vosk_audio_detector import VoskAudioDetector, _decode
from robot_friend.audio.transcript import Language


class FakeRecognizer:
    """Stands in for a vosk KaldiRecognizer: replays canned JSON results so the
    decode/selection logic can be tested without the model binary."""

    def __init__(self, final: dict, mid: dict | None = None):
        self._final = final
        self._mid = mid

    def AcceptWaveform(self, _pcm: bytes) -> bool:
        return self._mid is not None

    def Result(self) -> str:
        return json.dumps(self._mid or {})

    def FinalResult(self) -> str:
        return json.dumps(self._final)


def _result(text: str, confs: list[float]) -> dict:
    return {'text': text, 'result': [{'word': w, 'conf': c}
                                     for w, c in zip(text.split(), confs)]}


def test_decode_returns_text_and_mean_confidence():
    text, conf = _decode(FakeRecognizer(_result('hello world', [0.8, 0.6])), b'')
    assert text == 'hello world'
    assert conf == 0.7


def test_decode_joins_mid_buffer_and_final_segments():
    rec = FakeRecognizer(final=_result('world', [1.0]), mid=_result('hello', [1.0]))
    text, conf = _decode(rec, b'')
    assert text == 'hello world'
    assert conf == 1.0


def test_decode_empty_result():
    text, conf = _decode(FakeRecognizer({'text': ''}), b'')
    assert text == ''
    assert conf == 0.0


def _transcriber(recognizers: dict[Language, FakeRecognizer]) -> VoskAudioDetector:
    transcriber = VoskAudioDetector.__new__(VoskAudioDetector)  # skip model loading
    transcriber.sample_rate = 16000
    transcriber._recognizers = recognizers
    return transcriber


def test_transcribe_picks_highest_confidence_language():
    transcriber = _transcriber({
        Language.ENGLISH: FakeRecognizer(_result('yeah', [0.2])),
        Language.GERMAN: FakeRecognizer(_result('ja', [0.95])),
    })
    transcript = transcriber.transcribe(np.zeros(1600, dtype=np.float32))
    assert transcript.text == 'ja'
    assert transcript.language is Language.GERMAN
    assert transcript.language_probability == 0.95


def test_transcribe_empty_when_nothing_recognized():
    transcriber = _transcriber({
        Language.ENGLISH: FakeRecognizer({'text': ''}),
        Language.GERMAN: FakeRecognizer({'text': ''}),
    })
    transcript = transcriber.transcribe(np.zeros(1600, dtype=np.float32))
    assert transcript.text == ''
    assert transcript.language is None
