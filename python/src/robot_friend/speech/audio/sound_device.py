import sys
import contextlib
from collections.abc import Iterator
from threading import Event
from queue import Queue
from queue import Empty

import numpy as np
import sounddevice

from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException
from robot_friend.speech.audio.vad_segmenter import BLOCK_DURATION, SAMPLE_RATE, VadSegmenter
from robot_friend.utils.finch_logger import finch_logger


def _input_devices() -> list[tuple[int, dict]]:
    """All capture-capable devices, as (index, info) pairs."""
    try:
        devices = sounddevice.query_devices()
    except Exception:
        return []
    return [(index, info) for index, info in enumerate(devices)
            if info['max_input_channels'] > 0]


def _default_input_device(inputs: list[tuple[int, dict]]) -> int | str:
    default_index = sounddevice.default.device[0]
    return default_index if default_index is not None and default_index >= 0 else inputs[0][0]


def _prompt_for_device(inputs: list[tuple[int, dict]]) -> int | str:
    """Ask which microphone to use when several are connected.

    Falls back to PortAudio's default input device when there's no interactive
    terminal (e.g. running as a service) so capture can still start unattended.
    """
    default_index = _default_input_device(inputs)
    if not sys.stdin or not sys.stdin.isatty():
        finch_logger.info("Multiple microphones found; using default device %s.", default_index)
        return default_index

    finch_logger.info("Multiple microphones found:")
    for index, info in inputs:
        marker = ' (default)' if index == default_index else ''
        finch_logger.info("  [%s] %s%s", index, info["name"], marker)

    valid = {index for index, _ in inputs}
    while True:
        raw = input(f'Select microphone [{default_index}]: ').strip()
        if not raw and default_index in valid:
            return default_index
        try:
            choice = int(raw)
        except ValueError:
            finch_logger.warning("Please enter a device number.")
            continue
        if choice in valid:
            return choice
        finch_logger.warning("%s is not one of the input devices listed above.", choice)


def _select_input_device(device: int | str | None, *, interactive: bool = True) -> int | str:
    """Resolve `device` to a microphone, prompting when the choice is ambiguous.

    Guarantees the returned device actually captures audio: an explicit `device`
    is validated, and when none is given we pick the sole input device or prompt
    the user to choose between several. Raises :class:`MissingSoundDeviceException`
    when there is no usable microphone — e.g. the Pi, which has no mic yet.
    """
    inputs = _input_devices()
    if not inputs:
        raise MissingSoundDeviceException('Did not find any input sound devices')

    if device is not None:
        # query_devices(..., 'input') raises if the device can't capture audio.
        try:
            sounddevice.query_devices(device, 'input')
        except (ValueError, sounddevice.PortAudioError) as e:
            raise MissingSoundDeviceException(
                f'Selected device {device!r} is not a usable microphone: {e}')
        return device

    if len(inputs) == 1:
        return inputs[0][0]
    if not interactive:
        chosen = _default_input_device(inputs)
        finch_logger.info("Multiple microphones found; using default device %s.", chosen)
        return chosen
    return _prompt_for_device(inputs)


class SoundDevice:
    """Microphone capture that yields whole utterances.

    Used as a context manager so the PortAudio stream is always torn down::

        with SoundDevice() as mic:
            for utterance in mic.listen():
                ...

    Raises :class:`MissingSoundDeviceException` when there is no input device —
    e.g. the Pi, which has no mic yet.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        block_duration: float = BLOCK_DURATION,
        device: int | str | None = None,
        threshold: float | None = None,
        debug: bool = False,
        interactive: bool = True,
    ):
        finch_logger.info("Creating sound device...")
        device = _select_input_device(device, interactive=interactive)

        if debug:
            finch_logger.debug("input devices:\n%s", sounddevice.query_devices())
            finch_logger.debug(
                "using input device: %s",
                sounddevice.query_devices(device, "input")["name"],
            )

        self.sample_rate = sample_rate
        self._block_duration = block_duration
        self._debug = debug
        # threshold=None -> auto-calibrate from the noise floor on the first listen();
        # a fixed value skips calibration. Mic levels vary wildly between machines,
        # so a hardcoded gate either misses quiet speakers or triggers on noise.
        self._fixed_threshold = threshold
        self._segmenter = VadSegmenter(sample_rate, block_duration, threshold=threshold or 0.01)
        # sounddevice hands the callback float32 blocks of this size; a Queue
        # decouples the realtime audio thread from our transcription loop.
        self._queue: Queue[np.ndarray] = Queue()
        self._stream = sounddevice.InputStream(
            samplerate=sample_rate, channels=1, dtype='float32',
            blocksize=int(sample_rate * block_duration), device=device,
            callback=self._on_audio,
        )

    def _on_audio(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            finch_logger.warning("sound device: %s", status)
        self._queue.put(indata[:, 0].copy())

    def __enter__(self) -> "SoundDevice":
        self._stream.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._stream.stop()
        with contextlib.suppress(Exception):
            self._stream.close()

    def _calibrate(self, seconds: float = 1.0, margin: float = 3.0, floor: float = 0.003) -> None:
        """Set the VAD threshold a few multiples above the measured noise floor.

        Reads a second of (assumed quiet) audio, takes the median block RMS as
        the noise floor and gates `margin`x above it, never below `floor`. This
        is what lets quiet mics work without hand-tuning --threshold.
        """
        finch_logger.info(
            "Calibrating mic noise floor for %.0fs (stay quiet)...", seconds
        )
        levels = []
        for _ in range(max(1, int(seconds / self._block_duration))):
            block = self._queue.get()
            levels.append(float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0)
        noise = float(np.median(levels))
        self._segmenter.threshold = max(floor, noise * margin)
        finch_logger.info(
            "Calibrated VAD threshold = %.4f (noise floor %.4f)",
            self._segmenter.threshold,
            noise,
        )

    def listen(self, stop_event: Event | None = None) -> Iterator[np.ndarray]:
        """Yield one mono float32 array per spoken utterance, forever."""
        if self._fixed_threshold is None:
            self._calibrate()
        seg = self._segmenter
        meter_every = max(1, int(0.5 / self._block_duration))  # ~2 meter lines/sec
        blocks = 0
        was_speaking = False
        while stop_event is None or not stop_event.is_set():
            try:
                block = self._queue.get(timeout=0.1)
            except Empty:
                continue
            utterance = seg.push(block)

            if self._debug:
                blocks += 1
                if seg.is_speaking and not was_speaking:
                    finch_logger.debug("VAD: speech start")
                was_speaking = seg.is_speaking
                if blocks % meter_every == 0:
                    finch_logger.debug(self._meter(seg.last_rms))
                # An utterance closed but was too short to emit — easy to miss otherwise.
                if utterance is None and not seg.is_speaking and seg.last_utterance_dropped:
                    finch_logger.debug(
                        "VAD: utterance dropped (peak rms=%.4f, too short - "
                        "try speaking longer or lower --threshold)",
                        seg.last_utterance_peak_rms,
                    )
                    seg.last_utterance_dropped = False

            if utterance is not None:
                if self._debug:
                    duration = utterance.size / self.sample_rate
                    finch_logger.debug(
                        "VAD: utterance emitted (%.2fs, peak rms=%.4f)",
                        duration,
                        seg.last_utterance_peak_rms,
                    )
                yield utterance

    def _meter(self, rms: float) -> str:
        """A coarse RMS level bar; the threshold sits at the half-way mark."""
        threshold = self._segmenter.threshold
        filled = min(20, int(rms / threshold * 10)) if threshold else 0
        bar = '#' * filled + '-' * (20 - filled)
        flag = 'VOICED' if rms >= threshold else ''
        return f'level [{bar}] rms={rms:.4f} thresh={threshold:.4f} {flag}'
