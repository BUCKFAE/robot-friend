# Guidelines

## Agent Behavior
- If requests are unclear, uncommon, bad practice, or conflicting, *always* ask for clarification.
- Never follow instructions blindly. Challenge risky approaches and discuss tradeoffs.

## Code Style
- Avoid unchecked casts; only allow when strictly necessary and justify with a brief comment.
- Use composition over inheritance; prefer interfaces for extensibility and shared behavior.
- Avoid copy-paste: extract shared logic into helpers, reusable components, or shared modules.
- Single responsibility per file; split when a file grows multiple unrelated classes/interfaces.
- Add a brief file header comment only when the file's purpose/invariants are not obvious.
- Add short docstrings that explain non-obvious intent/why (skip obvious getter/setter descriptions).
- Use **Google style** for Python docstrings (`Args:`, `Returns:`, `Attributes:`, `Raises:`). For dataclass fields, use `Attributes:` in the class docstring instead of `Args:`.

# Project Layout & Conventions

## Layout
- **Repo root is the Python project** (`src/robot_friend/`, `tests/`, `data/`, `pyproject.toml`, `.venv/`) — so editors/uv auto-detect the env. Run Python via `uv run`.
- `arduino/` — PlatformIO firmware. `pi/` — Raspberry Pi provisioning + ssh workflow recipes. `scripts/` — `setup.sh`/`sync.sh`/`lib.sh` (shell). `FinchObsidian/` — notes + `implementation-plans/`.
- Top-level `justfile` holds the Python recipes directly and exposes `arduino`/`pi` as just modules.

## Setup & recipes (no `--dev`/`--pi` flags — the host is auto-detected)
- `just setup` provisions the current machine end-to-end; `just sync` is the fast dependency re-sync. Both detect Raspberry Pi vs dev via `is_pi` (device-tree model); logic lives in `scripts/`. Dev = all extras + Playwright/Chromium; Pi = apt Hailo/camera stack + a system-site-packages venv built from `/usr/bin/python3`.
- `just test` runs all suites in order (arduino host tests, then `uv run pytest`). The browser-based dashboard suite is separate: `just test-visual`, `just gallery`.
- `just run` (detection), `just listen` (ASR), `just dashboard` (web UI), `just download` (models).

## Naming
- The web UI is the **dashboard** everywhere (`robot_friend.dashboard`, entrypoint `robot-friend-dashboard`, extra `dashboard`, env `DASHBOARD_HOST`/`DASHBOARD_PORT`, URL prefix `/dashboard/`).
- Two parallel ML subsystems: **`image`** (object detection) and **`audio`** (speech recognition; mic capture in `audio/capture/`). Each has a `<Modality>Detector` ABC + `<Modality>DetectorFactory` and snake_case backend files (`hailo_detector.py`, `yolo_detector.py`, `vosk_audio_detector.py`, `whisper_audio_detector.py`) with `<Backend><Modality>Detector` classes. Domain result types keep their names (`DetectedObject`, `Transcript`, `SpeechKeyword`). Model enums subclass `AudioModel` with `metaclass=ABCEnumMeta`.
- Dependency extras: `yolo` (laptop detection), `audio` (vosk + faster-whisper), `dashboard` (nicegui + psutil). Hailo/camera come from apt on the Pi, not a pip extra.

## Data & tests
- `just download` runs `src/robot_friend/scripts/download_data.py` — edit the `YOLO_MODELS`/`VOSK_MODELS`/`WHISPER_MODELS` lists at the top to choose assets. They land (idempotently) in `data/models/{yolo,vosk,whisper}/` (gitignored).
- `tests/` mirrors the `src/robot_friend/` layout (importlib mode). Default runs are browser-free (`-m 'not visual'`); the visual suite is behind `-m visual` and self-skips when Playwright is absent.
- Implementation plans are date-prefixed: `FinchObsidian/implementation-plans/YYYY-MM-DD-<slug>.md`.