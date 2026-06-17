import numpy as np

# Whisper expects mono 16 kHz; capturing at that rate avoids a resample step.
SAMPLE_RATE = 16000
BLOCK_DURATION = 0.03  # 30 ms blocks, the granularity the energy VAD works at


class VadSegmenter:
    """Groups fixed-size audio blocks into whole utterances with a crude
    energy gate.

    Whisper works best on whole phrases, so instead of transcribing every block
    we buffer blocks whose RMS energy clears `threshold` and emit the buffer once
    a run of quiet blocks closes the utterance out. Energy VAD is dependency-free
    and good enough for keyword spotting; swap in webrtcvad/silero later if the
    room gets noisy. Pure (no audio hardware) so it can be unit tested.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_duration: float = BLOCK_DURATION,
                 threshold: float = 0.01, silence_duration: float = 0.6,
                 min_speech_duration: float = 0.15, max_utterance_duration: float = 12.0):
        self.threshold = threshold
        self._silence_blocks = max(1, int(silence_duration / block_duration))
        self._min_speech_samples = int(min_speech_duration * sample_rate)
        self._max_utterance_samples = int(max_utterance_duration * sample_rate)
        self._buffer: list[np.ndarray] = []
        self._buffered_samples = 0
        self._speech_samples = 0
        self._silence_run = 0
        self._speaking = False
        # Exposed for tracing/calibration (see SoundDevice debug output).
        self.last_rms = 0.0
        self.peak_rms = 0.0
        self.last_utterance_peak_rms = 0.0
        self.last_utterance_dropped = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def push(self, block: np.ndarray) -> np.ndarray | None:
        """Feed one block; returns a finished utterance, or None if still open."""
        rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
        voiced = rms >= self.threshold
        self.last_rms = rms

        if voiced:
            self._speaking = True
            self._silence_run = 0
            self.peak_rms = max(self.peak_rms, rms)

        # Keep trailing silence in the buffer so Whisper sees the word decay.
        if self._speaking:
            self._buffer.append(block)
            self._buffered_samples += block.size
            if voiced:
                self._speech_samples += block.size
            else:
                self._silence_run += 1

            if self._silence_run >= self._silence_blocks or \
                    self._buffered_samples >= self._max_utterance_samples:
                return self.flush()
        return None

    def flush(self) -> np.ndarray | None:
        """Close the current utterance, returning it if it was long enough."""
        utterance = np.concatenate(self._buffer) if self._buffer else np.empty(0, dtype=np.float32)
        long_enough = self._speech_samples >= self._min_speech_samples
        # Snapshot stats of the utterance we're closing before resetting.
        self.last_utterance_peak_rms = self.peak_rms
        self.last_utterance_dropped = not long_enough
        self._buffer = []
        self._buffered_samples = 0
        self._speech_samples = 0
        self._silence_run = 0
        self._speaking = False
        self.peak_rms = 0.0
        return utterance if long_enough else None
