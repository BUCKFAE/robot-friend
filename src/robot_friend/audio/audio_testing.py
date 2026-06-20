"""The ``robot-friend-audio`` (``just listen``) entrypoint: print transcripts + keywords.

A thin CLI over the shared :func:`iter_transcripts` loop used by the robot's audio thread.
"""
from robot_friend.audio.transcribe_loop import iter_transcripts
from robot_friend.exceptions.missing_hardware_exception import MissingSoundDeviceException
from robot_friend.utils.finch_logger import finch_logger


def main() -> None:
    finch_logger.info("Listening (Ctrl-C to stop)")
    try:
        for transcript in iter_transcripts(threshold=0.005, interactive=True, debug=True):
            finch_logger.info("transcript: %s", transcript.as_log_line())
    except MissingSoundDeviceException as exc:
        # The Pi may have no mic yet; fail clearly rather than crashing on PortAudio.
        finch_logger.error("No microphone available: %s", exc)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
