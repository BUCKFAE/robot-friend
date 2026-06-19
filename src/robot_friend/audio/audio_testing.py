import time

from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException
from robot_friend.audio.capture.sound_device import SoundDevice
from robot_friend.audio.audio_detector_factory import AudioDetectorFactory
from robot_friend.utils.finch_logger import finch_logger


def main() -> None:

    threshold = 0.005
    debug: bool = True

    try:
        # device=None -> auto-pick the only mic, or prompt when there are several.
        sound_device = SoundDevice(threshold=threshold, debug=debug)
    except MissingSoundDeviceException as e:
        # The Pi has no mic yet; fail clearly rather than crashing on PortAudio.
        finch_logger.error("No microphone available: %s", e)
        return

    speech_detector = AudioDetectorFactory.get_audio_detector()

    with sound_device as mic:
        finch_logger.info(
            "Listening: %s (Ctrl-C to stop)", speech_detector.get_model_names
        )
        try:
            for utterance in mic.listen():
                started = time.perf_counter()
                transcript = speech_detector.transcribe(utterance)
                elapsed = time.perf_counter() - started
                finch_logger.info(
                    "transcribe: %.2fs -> %s", elapsed, transcript.as_log_line()
                )

        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
