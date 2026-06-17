import time

from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException
from robot_friend.speech.audio.sound_device import SoundDevice
from robot_friend.speech.speech_detector_factory import SpeechDetectorFactory


def main() -> None:

    threshold = 0.005
    debug: bool = True

    try:
        # device=None -> auto-pick the only mic, or prompt when there are several.
        sound_device = SoundDevice(threshold=threshold, debug=debug)
    except MissingSoundDeviceException as e:
        # The Pi has no mic yet; fail clearly rather than crashing on PortAudio.
        print(f'No microphone available: {e}', flush=True)
        return

    speech_detector = SpeechDetectorFactory.get_speech_detector()

    with sound_device as mic:
        print(f'Listening: {speech_detector.get_model_names} (Ctrl-C to stop)', flush=True)
        try:
            for utterance in mic.listen():
                started = time.perf_counter()
                transcript = speech_detector.transcribe(utterance)
                elapsed = time.perf_counter() - started
                print(f'transcribe: {elapsed:.2f}s -> {transcript.as_log_line()}')

        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
