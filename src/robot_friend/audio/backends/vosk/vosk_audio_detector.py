import json

import numpy as np

from robot_friend.audio.backends.vosk.vosk_model import VoskModel
from robot_friend.audio.keywords.match_keywords import match_keywords
from robot_friend.audio.audio_detector import AudioDetector
from robot_friend.audio.transcript import Language, Transcript
from robot_friend.audio.capture.audio import float_to_pcm16


def _collect(segment: dict, words: list[str], confidences: list[float]) -> None:
    """Append a Vosk result segment's text and per-word confidences in place."""
    text = segment.get('text', '').strip()
    if text:
        words.append(text)
    confidences.extend(word['conf'] for word in segment.get('result', []))


def _decode(recognizer, pcm: bytes) -> tuple[str, float]:
    """Run a whole utterance through one recognizer and return (text, confidence).

    Vosk emits a result whenever ``AcceptWaveform`` returns True (a silence is
    detected mid-stream) and the remainder via ``FinalResult``; for utterances
    longer than Vosk's internal buffer the spoken text is split across both, so
    we stitch the segments back together. Confidence is the mean of the per-word
    confidences, or 0.0 when nothing was recognized.
    """
    words: list[str] = []
    confidences: list[float] = []

    if recognizer.AcceptWaveform(pcm):
        _collect(json.loads(recognizer.Result()), words, confidences)
    _collect(json.loads(recognizer.FinalResult()), words, confidences)

    text = ' '.join(words)
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return text, confidence


class VoskAudioDetector(AudioDetector):
    """Offline speech detector backed by Vosk.

    Runs the utterance through one recognizer per configured language and keeps
    the transcript from the recognizer that was most confident, which doubles as
    a crude language guess.
    """

    def __init__(self, vosk_models: list[VoskModel], sample_rate: int = 16000):
        from vosk import KaldiRecognizer, Model, SetLogLevel
        SetLogLevel(-1)

        assert len(vosk_models) > 0, f'Expected at least one vosk model'
        assert len({m.config.language for m in vosk_models}) == len(vosk_models), f'Expected exactly one vosk model per language'

        self.sample_rate = sample_rate
        self._model_names = [model.get_name() for model in vosk_models]
        self._recognizers: dict[Language, KaldiRecognizer] = {}

        for model in vosk_models:
            vosk_model = Model(str(model.get_model_dir()))
            recognizer = KaldiRecognizer(vosk_model, sample_rate)
            recognizer.SetWords(True)  # per-word confidences -> language pick
            self._recognizers[model.config.language] = recognizer

    @property
    def backend_name(self) -> str:
        return 'vosk'

    @property
    def get_model_names(self) -> list[str]:
        return self._model_names

    def transcribe(self, samples: np.ndarray) -> Transcript:
        """Transcribe one utterance, keeping the most confident language.

        Args:
            samples: Mono 16 kHz float32 audio for a single utterance.

        Returns:
            The best :class:`Transcript`, with matched keywords attached.
        """
        pcm = float_to_pcm16(samples)

        best = Transcript(text='', language=None)
        for language, recognizer in self._recognizers.items():
            text, confidence = _decode(recognizer, pcm)
            if text and confidence > best.language_probability:
                best = Transcript(text=text, language=language, language_probability=confidence)

        best.keywords = match_keywords(best)
        return best
