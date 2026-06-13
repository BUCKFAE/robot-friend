# robot_friend (Python)

Python companion app for the robot-friend firmware.

## Setup

```sh
uv sync --dev --extra yolo    # laptop: YOLO-on-CPU backend (torch/ultralytics)
just sync-pi                  # Pi: AI HAT backend via system picamera2/Hailo
```

## Run

```sh
uv run robot-friend     # --port for the MJPEG view (default 8081); see --help
```

The detection backend and camera are auto-selected from the host (Hailo + Pi
camera on the Pi, YOLO-on-CPU + webcam on a laptop). On the Pi it runs headless
and serves the annotated view as MJPEG; on a laptop it opens a local preview
window instead.

## Test

```sh
uv run pytest
```
