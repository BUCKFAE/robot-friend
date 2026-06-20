import argparse
import json
import threading
import time

import cv2

from robot_friend.camera import open_camera
from robot_friend.control import RobotControls
from robot_friend.exceptions.missing_hardware_exception import (
    MissingSoundDeviceException,
)
from robot_friend.image.image_detector_factory import ImageDetectorFactory
from robot_friend.robot_server import RobotServer
from robot_friend.servo.servo_controller import ServoController
from robot_friend.telemetry.store import TelemetryStore
from robot_friend.utils.finch_logger import finch_logger
from robot_friend.utils.get_current_host import is_pi_host
from robot_friend.utils.log_buffer import LogStream, logs_since_json, setup_logging

# Catppuccin green, matching the dashboard's annotated overlay.
_BGR_GREEN = (161, 227, 166)


def _run_audio(
    store: TelemetryStore,
    controls: RobotControls,
    stop_event: threading.Event,
    wakeup: threading.Event,
) -> None:
    """Transcribe speech into the telemetry store on a background thread.

    Best-effort and fully optional: with no audio backend or microphone the robot just
    runs vision-only — audio never blocks or breaks detection. Restarts on the new device
    when the sound selection changes (the dashboard can switch it via ``POST /control``).
    The ASR import is deferred so the detection process needn't pull the backend at all
    when audio is unavailable.
    """
    try:
        from robot_friend.audio.transcribe_loop import iter_transcripts
    except ImportError as exc:
        finch_logger.warning("audio backend unavailable; running vision-only: %s", exc)
        return

    controls.on_sound_device_changed(lambda _device: wakeup.set())
    no_mic_logged = False
    while not stop_event.is_set():
        wakeup.clear()  # a device change (or shutdown) sets this to break the loop below
        device = controls.sound_device
        try:
            for transcript in iter_transcripts(device=device, stop_event=wakeup):
                no_mic_logged = False
                store.set_transcript(transcript)
        except MissingSoundDeviceException as exc:
            if not no_mic_logged:
                finch_logger.warning(
                    "no microphone; running vision-only (will retry): %s", exc
                )
                no_mic_logged = True
            wakeup.wait(2.0)
        except Exception:
            finch_logger.exception("audio loop failed; retrying")
            wakeup.wait(2.0)


def _run_vision(
    detector,
    store: TelemetryStore,
    server: RobotServer,
    controls: RobotControls,
    stop_event: threading.Event,
) -> None:
    """Read the camera, detect, and publish raw/annotated frames + telemetry.

    Re-opens the camera when the selected index changes, so the dashboard can switch
    cameras via ``POST /control`` (a no-op on the single-camera Pi, but useful on dev).
    """
    headless = is_pi_host() or True
    active_index: int | None = None
    camera = None
    last = time.monotonic()
    try:
        while not stop_event.is_set():
            wanted_index = controls.camera_index
            if camera is None or wanted_index != active_index:
                if camera is not None:
                    camera.close()
                active_index = wanted_index
                try:
                    camera = open_camera(active_index)
                except Exception as exc:
                    finch_logger.warning(
                        "could not open camera %s: %s", active_index, exc
                    )
                    camera = None
                    time.sleep(1.0)
                    continue
                finch_logger.info(
                    "Running: %s + camera %s", type(detector).__name__, active_index
                )
                last = time.monotonic()

            frame = camera.read()
            if frame is None:
                finch_logger.warning("camera %s returned no frame", active_index)
                camera.close()
                camera = None
                time.sleep(0.5)
                continue

            started = time.monotonic()
            boxes = detector.detect(frame)
            detect_ms = (time.monotonic() - started) * 1000

            now = time.monotonic()
            fps = 1.0 / (now - last) if now > last else 0.0
            last = now

            server.publish("raw", frame)
            annotated = frame.copy()
            for b in boxes:
                cv2.rectangle(
                    annotated,
                    (b.bounding_box.x1, b.bounding_box.y1),
                    (b.bounding_box.x2, b.bounding_box.y2),
                    _BGR_GREEN,
                    2,
                )
            server.publish("annotated", annotated)
            store.set_vision(list(boxes), round(fps, 1), round(detect_ms, 1))

            if not headless:
                cv2.imshow("presence", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if camera is not None:
            camera.close()
        if not headless:
            cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="robot-friend person detection")
    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        default=8081,
        help="Port to serve MJPEG video + JSON telemetry on",
    )
    args = parser.parse_args()

    detector = ImageDetectorFactory.get_image_detector()
    store = TelemetryStore()
    controls = RobotControls()
    # Best-effort: the factory always returns a working driver (the in-memory fake when no
    # PCA9685 is wired), so this never blocks startup whether or not servos are attached.
    servos = ServoController.from_factory()

    # Capture the robot's own logging so the dashboard can show it (the robot serves it;
    # it doesn't push). Harmless when nobody attaches — just a bounded ring buffer.
    log_stream = LogStream()
    setup_logging(log_stream)

    # The robot owns its hardware and always serves; the dashboard is an optional viewer
    # that attaches (proxies video, polls telemetry/logs/devices, posts control). Nothing
    # here depends on a dashboard: endpoints are inert until someone calls them.
    server = RobotServer(args.port)
    server.on_get("/telemetry.json", lambda _query: store.to_json())
    server.on_get(
        "/logs.json",
        lambda query: logs_since_json(log_stream, int(query.get("since", "0"))),
    )
    server.on_get(
        "/devices.json", lambda _query: json.dumps(controls.devices_payload()).encode()
    )
    server.on_post("/control", lambda body: controls.apply(body))
    server.on_get(
        "/servos.json", lambda _query: json.dumps(servos.snapshot()).encode()
    )
    server.on_post("/servo", lambda body: servos.apply(body))
    finch_logger.info(
        "serving on http://0.0.0.0:%s/ "
        "(video, telemetry, logs, devices, servos, POST /control, POST /servo)",
        args.port,
    )

    # Speech runs alongside vision on its own thread, feeding the same telemetry store.
    stop = threading.Event()
    audio_wakeup = threading.Event()
    threading.Thread(
        target=_run_audio,
        args=(store, controls, stop, audio_wakeup),
        daemon=True,
        name="audio",
    ).start()

    try:
        _run_vision(detector, store, server, controls, stop)
    finally:
        stop.set()
        audio_wakeup.set()  # unblock the audio loop so it exits


if __name__ == "__main__":
    main()
