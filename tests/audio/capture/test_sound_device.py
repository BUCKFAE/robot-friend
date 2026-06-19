"""Capture-rate negotiation and resampling (the hardware-free parts of SoundDevice)."""
import numpy as np
import pytest
import sounddevice

from robot_friend.audio.capture.sound_device import _resample_to, _select_capture_rate
from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException


def _fake_device(monkeypatch, *, default_rate: int, supported: set[int]) -> None:
    """Stand in for a capture device that accepts only `supported` rates."""
    def query_devices(device=None, kind=None):
        return {"name": "fake mic", "default_samplerate": float(default_rate),
                "max_input_channels": 1}

    def check_input_settings(device=None, samplerate=None, channels=None, dtype=None):
        if samplerate not in supported:
            raise sounddevice.PortAudioError("Invalid sample rate", -9997)

    monkeypatch.setattr(sounddevice, "query_devices", query_devices)
    monkeypatch.setattr(sounddevice, "check_input_settings", check_input_settings)


def test_prefers_target_rate_to_avoid_resampling(monkeypatch):
    _fake_device(monkeypatch, default_rate=48000, supported={16000, 48000})
    assert _select_capture_rate(0, 16000) == 16000


def test_falls_back_to_device_default_rate(monkeypatch):
    # The Pi's CD04 USB mic: 32 kHz native, rejects 16 kHz.
    _fake_device(monkeypatch, default_rate=32000, supported={32000})
    assert _select_capture_rate(0, 16000) == 32000


def test_raises_clear_error_when_no_rate_works(monkeypatch):
    _fake_device(monkeypatch, default_rate=8000, supported=set())
    with pytest.raises(MissingSoundDeviceException):
        _select_capture_rate(0, 16000)


def test_resample_downsamples_32k_to_16k():
    one_second = np.zeros(32000, dtype=np.float32)
    out = _resample_to(one_second, 32000, 16000)
    assert out.dtype == np.float32
    assert abs(out.size - 16000) <= 2  # one second at the target rate


def test_resample_is_identity_when_rates_match():
    audio = np.arange(100, dtype=np.float32)
    assert _resample_to(audio, 16000, 16000) is audio
