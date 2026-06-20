"""Mic-to-transcript loop shared by the ``robot-friend-audio`` CLI and the robot's audio
thread.

Opens the microphone, transcribes each spoken utterance, and yields a :class:`Transcript`.
Raises :class:`MissingSoundDeviceException` when there is no usable mic so callers decide
whether that is fatal (the CLI reports and exits; the robot logs and runs vision-only).
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from threading import Event

from robot_friend.audio.audio_detector_factory import AudioDetectorFactory
from robot_friend.audio.capture.sound_device import SoundDevice
from robot_friend.audio.transcript import Transcript
from robot_friend.utils.finch_logger import finch_logger


def iter_transcripts(
    *,
    device: int | str | None = None,
    threshold: float | None = 0.005,
    interactive: bool = False,
    debug: bool = False,
    stop_event: Event | None = None,
) -> Iterator[Transcript]:
    """Yield one :class:`Transcript` per spoken utterance until stopped.

    Args:
        device: Microphone to use, or None to auto-pick / prompt (see :class:`SoundDevice`).
        threshold: Fixed VAD threshold, or None to auto-calibrate from the noise floor.
        interactive: Whether to prompt when several microphones are present.
        debug: Forward verbose VAD/capture diagnostics from :class:`SoundDevice`.
        stop_event: Set to stop the loop and release the microphone.

    Yields:
        The transcript of each detected utterance.

    Raises:
        MissingSoundDeviceException: When there is no usable microphone.
    """
    detector = AudioDetectorFactory.get_audio_detector()
    with SoundDevice(
        device=device, threshold=threshold, interactive=interactive, debug=debug
    ) as mic:
        finch_logger.info("listening for speech on device %s", device)
        for utterance in mic.listen(stop_event=stop_event):
            if stop_event is not None and stop_event.is_set():
                break
            started = time.perf_counter()
            transcript = detector.transcribe(utterance)
            finch_logger.debug(
                "transcribe: %.2fs -> %s",
                time.perf_counter() - started,
                transcript.as_log_line(),
            )
            yield transcript
