import numpy as np

from robot_friend.speech.audio.vad_segmenter import VadSegmenter

SAMPLE_RATE = 16000
BLOCK_DURATION = 0.03
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)


def _block(amplitude: float) -> np.ndarray:
    return np.full(BLOCK_SIZE, amplitude, dtype=np.float32)


def _segmenter() -> VadSegmenter:
    return VadSegmenter(SAMPLE_RATE, BLOCK_DURATION, threshold=0.01,
                        silence_duration=0.6, min_speech_duration=0.2)


def test_emits_utterance_after_trailing_silence():
    seg = _segmenter()
    silence_blocks = int(0.6 / BLOCK_DURATION)

    # Half a second of speech keeps the utterance open.
    for _ in range(int(0.5 / BLOCK_DURATION)):
        assert seg.push(_block(0.5)) is None

    # Silence shorter than the timeout still doesn't close it.
    assert seg.push(_block(0.0)) is None

    utterance = None
    for _ in range(silence_blocks):
        result = seg.push(_block(0.0))
        if result is not None:
            utterance = result
    assert utterance is not None
    assert utterance.size > int(0.5 * SAMPLE_RATE)


def test_silence_before_speech_is_ignored():
    seg = _segmenter()
    for _ in range(10):
        assert seg.push(_block(0.0)) is None


def test_too_short_utterance_is_dropped():
    seg = _segmenter()
    # One block of speech is below min_speech_duration, so the flush yields nothing.
    seg.push(_block(0.5))
    for _ in range(int(0.6 / BLOCK_DURATION)):
        result = seg.push(_block(0.0))
        assert result is None
