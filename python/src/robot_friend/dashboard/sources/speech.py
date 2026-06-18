"""Live speech source for the diagnostics dashboard."""
from __future__ import annotations

import threading
import time

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.controls import DashboardControls
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.dashboard.sources.dataclass import TRANSCRIPT_CHANNEL
from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException
from robot_friend.speech.audio.sound_device import SoundDevice
from robot_friend.utils.finch_logger import finch_logger


class SpeechSource(DashboardDataSource):
    channel = TRANSCRIPT_CHANNEL

    def __init__(self, controls: DashboardControls) -> None:
        self._controls = controls
        self._stop = threading.Event()
        self._restart = threading.Event()
        self._thread: threading.Thread | None = None
        self._mic_lock = threading.Lock()
        self._mic: SoundDevice | None = None
        self._controls.on_sound_device_changed(self._request_restart)

    def start(self, bus: Bus) -> None:
        self._thread = threading.Thread(
            target=self._run, args=(bus,), daemon=True, name="speech-source"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._request_restart(self._controls.sound_device)

    def _request_restart(self, device: int | str | None) -> None:
        self._restart.set()
        with self._mic_lock:
            if self._mic is not None:
                self._mic.close()

    def _run(self, bus: Bus) -> None:
        from robot_friend.speech.speech_detector_factory import SpeechDetectorFactory

        detector = SpeechDetectorFactory.get_speech_detector()
        while not self._stop.is_set():
            self._restart.clear()
            device = self._controls.sound_device
            try:
                with SoundDevice(device=device, threshold=0.005, interactive=False) as mic:
                    with self._mic_lock:
                        self._mic = mic
                    finch_logger.info("speech source listening on device %s", device)
                    for utterance in mic.listen(stop_event=self._restart):
                        if self._stop.is_set() or self._restart.is_set():
                            break
                        started = time.perf_counter()
                        transcript = detector.transcribe(utterance)
                        elapsed = time.perf_counter() - started
                        finch_logger.info(
                            "speech transcript in %.2fs: %s",
                            elapsed,
                            transcript.as_log_line(),
                        )
                        bus.publish(TRANSCRIPT_CHANNEL, transcript)
            except MissingSoundDeviceException as exc:
                finch_logger.warning("speech source has no input device: %s", exc)
                self._stop.wait(2.0)
            except Exception as exc:
                if not self._restart.is_set() and not self._stop.is_set():
                    finch_logger.exception("speech source failed: %s", exc)
                    self._stop.wait(2.0)
            finally:
                with self._mic_lock:
                    self._mic = None
