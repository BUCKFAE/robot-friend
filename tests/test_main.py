"""The robot must run vision-only when there's no microphone — audio is best-effort and
must never block or crash detection (the headline standalone guarantee)."""
import threading
import time

import pytest


def test_run_audio_is_vision_only_without_a_mic(monkeypatch):
    pytest.importorskip("vosk")  # the audio backend; skip where the extra isn't installed
    import robot_friend.main as rf_main
    from robot_friend.control import RobotControls
    from robot_friend.exceptions.missing_hardware_exception import (
        MissingSoundDeviceException,
    )
    from robot_friend.telemetry.store import TelemetryStore

    attempts: list[int] = []

    def _no_mic(**_kwargs):
        attempts.append(1)
        raise MissingSoundDeviceException("no mic")

    # _run_audio imports iter_transcripts lazily, so patching the module attribute works.
    monkeypatch.setattr("robot_friend.audio.transcribe_loop.iter_transcripts", _no_mic)

    store = TelemetryStore()
    controls = RobotControls()
    stop, wakeup = threading.Event(), threading.Event()
    thread = threading.Thread(
        target=rf_main._run_audio, args=(store, controls, stop, wakeup), daemon=True
    )
    thread.start()

    deadline = time.monotonic() + 2.0
    while not attempts and time.monotonic() < deadline:
        time.sleep(0.01)
    stop.set()
    wakeup.set()  # unblock the retry wait so the loop exits
    thread.join(timeout=3.0)

    assert attempts, "audio loop never attempted to open the mic"
    assert not thread.is_alive(), "audio loop did not exit on stop"
    assert store.snapshot()["transcript"] is None  # vision-only: no transcript published
