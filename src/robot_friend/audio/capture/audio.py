import numpy as np

# 16-bit signed PCM spans [-32768, 32767]; we scale by the positive max so a
# full-scale float32 sample of 1.0 maps to 32767 without overflowing into -32768.
_PCM16_MAX = 32767


def float_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert mono float32 audio in [-1, 1] to little-endian 16-bit PCM bytes.

    We capture audio as float32 (see :class:`SoundDevice`), but recognizers such
    as Vosk's ``KaldiRecognizer`` consume signed 16-bit PCM. Samples are clipped
    first so values slightly outside [-1, 1] don't wrap around on conversion.
    """
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * _PCM16_MAX).astype('<i2').tobytes()
