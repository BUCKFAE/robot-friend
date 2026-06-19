# Repo Cleanup & Restructure — Implementation Plan

> Status: **Proposed — awaiting go-ahead.** Decision date: 2026-06-19.
> Self-contained handoff spec (survives a context compaction). Covers the nine
> cleanup asks plus fixes found during reconnaissance.

---

## 0. Decisions (locked)

Resolved with the user up front (the subjective / high-blast-radius ones):

| # | Decision | Choice |
|---|---|---|
| D1 | image/speech detector naming | **Finish in-place**: snake_case the backend files, parallel factories (`ImageDetectorFactory` + `AudioDetectorFactory`). No new parent package. |
| D2 | `speech/` → `audio/` | **Rename** the package to `audio/`; the inner mic-capture submodule `speech/audio/` → `audio/capture/`. |
| D3 | repo layout | **Dissolve `python/` into the repo root** so editors/uv auto-detect the venv. |
| D4 | `just test` / CI scope | `just test` = **arduino + python unit, in order**; browser suite stays behind `just test-visual`; CI = arduino + python unit + a **separate (optional) visual job**. |

### Audio rename boundary (derived from D1+D2)

`audio/` is the **modality + ASR abstraction** (parallels `image/` / `ImageDetector`).
The **ASR result/content types stay speech-named** (they parallel image keeping
`DetectedObject`, not `ImageObject`):

- **Renamed → Audio\*:** the package, the abstraction, the factory, the backends,
  the dashboard source, the tests, the extra, the entrypoint.
- **Kept (speech domain):** `Transcript`, `Language`, `SpeechKeyword`,
  `DetectedSpeechKeyword`, `SpeechKeywordConfig`, `transcript.py`,
  `keywords/`, the dashboard `TranscriptPanel`.

### Open confirmations (will proceed with the recommended unless told otherwise)

- **C1** — rename the user-facing extra `speech` → `audio` (`--extra audio`). *Recommended: yes* (consistency).
- **C2** — rename the entrypoint `robot-friend-speech` → `robot-friend-audio`. *Recommended: yes* (consistency); `just listen` is unchanged either way.

---

## 1. Goals (maps the nine asks)

1. `pyproject.toml` + venv at repo root → editors/uv pick it up. *(Phase A)*
2. Two setup modes only, **auto-detected** (no `--dev`/`--pi` flags). *(Phase E)*
3. Naming: `diagnostics` → `dashboard` everywhere; unify image/audio detector naming. *(Phases B, C)*
4. More recipes; `just setup` provisions everything (auto-detect); logic in a script. *(Phase E)*
5. One idempotent data-download script driven by editable lists at the top. *(Phase D)*
6. `just test` runs all suites in order. *(Phase E)*
7. Implementation-plans get date prefixes. *(Phase H)*
8. Google-style docstrings everywhere. *(Phase F)*
9. Trim long/obvious comments per CLAUDE.md. *(Phase G)*

Plus: update docs (Phase I), CI (Phase J), CLAUDE.md (Phase K).

---

## 2. Reconnaissance findings

- The `diagnostics → dashboard` rename is **half-done**: the src package is already
  `dashboard/`, but `tests/diagnostics/`, the `diagnostics` extra, the
  `robot-friend-diagnostics` script, env vars `DIAGNOSTICS_HOST/PORT`, URL paths
  `/diagnostics/static` + `/diagnostics/video`, and many docstrings/strings still say
  "diagnostics". (~79 hits / 16 files.)
- **Stale dir:** `src/robot_friend/diagnostics/` exists with only `__pycache__` (untracked); delete it.
- **Download-script bugs** (fix during consolidation): `download_whisper.py` writes into the
  **yolo** dir (`get_yolo_model_dir()`); `download_vosk.py` + `download_whisper.py` import `sys`
  but never parse the args the justfile passes; all three are **destructive** (`clean_setup_dir`)
  → not idempotent.
- **Docstrings:** only `clean_setup_dir.py` and `get_current_host.py` use reST (`:param:`/`:return:`).
  The rest of the gap is dataclasses/ABCs missing `Attributes:`/`Args:`/`Returns:` (e.g.
  `detection.py`, `transcript.py`, `keyword.py`, `coordinate.py`, `image_detector.py`,
  `speech_detector.py`, `speech_detection_model.py`, `vad_segmenter.py`).
- **Tests are hardware/model-free:** `vosk`/`nicegui`/`hailo` are imported lazily, so the 35
  unit tests collect and pass with base deps + the `yolo` extra (why CI is green). The visual
  suite self-ignores when Playwright is absent.

---

## 3. Phased execution

Each phase ends with `uv run pytest` (35 green) before moving on. Renames use
`git mv` to preserve history; import rewrites are mechanical + verified by import.

### Phase A — Repo layout → root (do first; everything else lands in final paths)

`git mv` from `python/` to repo root: `pyproject.toml`, `uv.lock`, `.python-version`,
`README.md` (merge into root README, see Phase I), `src/`, `tests/`, `data/`.
Then rewire:

- **Root `justfile`** — absorb the old `python/justfile` recipes (run at root, no `cd python`),
  keep `mod arduino` + `mod pi`, drop `mod python`.
- **`pi/justfile`** — `just python::sync-pi` → `just sync`; `cd {{remote_dir}}/python` → `cd {{remote_dir}}`; rsync `--exclude=/python/data` → `--exclude=/data`.
- **`pi/setup.sh`** logic → `scripts/setup.sh` (Phase E); `REPO_DIR` is now the repo root.
- **`.github/workflows/ci.yml`** — python job `working-directory: python` → remove (root).
- **`.gitignore`** — `python/python.iml` → `*.iml` (or root path); confirm `.venv/`, `__pycache__/` still match.
- **`data/.gitignore`** unchanged (already `models/` + `logs/`).
- `pyproject` internals unchanged: `packages = ["src/robot_friend"]`, `testpaths = ["tests"]` still resolve.
- Recreate venv at root: `rm -rf python/.venv` (gone with move), `uv sync`.

**Verify:** `uv run pytest` green from root; `just --list` works.

### Phase B — Finish `diagnostics` → `dashboard`

- `git mv tests/diagnostics tests/dashboard`.
- `src/robot_friend/dashboard/diagnostics_scenario.py` → `dashboard_scenario.py`;
  `DiagnosticsDemoScenario` → `DashboardDemoScenario` (+ its docstring).
- pyproject: extra `diagnostics` → `dashboard`; script `robot-friend-diagnostics` → `robot-friend-dashboard`.
- Env vars `DIAGNOSTICS_HOST/PORT` → `DASHBOARD_HOST/PORT` (`dashboard/main.py`, `tests/dashboard/visual/conftest.py`).
- URL paths `/diagnostics/static` → `/dashboard/static`, `/diagnostics/video` → `/dashboard/video`
  (`grid.py`, `dashboard_video_streams.py`, static HTML).
- Strings/docstrings: `__init__.py`, `sources/logs.py` (incl. fake-log strings `robot_friend.diagnostics`),
  `sources/speech.py`, `main.py` (titles "Finch Diagnostics" → "Finch Dashboard"), `pyproject` comments,
  `YOLODetector.py:20`, test docstrings/conftest.
- Delete the stale `src/robot_friend/diagnostics/` dir.
- `dashboard/README.md` rewritten (Phase I).

**Verify:** `uv run pytest`; `uv run robot-friend-dashboard --demo-scenario nominal` boots.

### Phase C — image / audio detector naming

**image/** (factory + file casing):
- `detection_factory.py` → `image_detector_factory.py`; `DetectionFactory` → `ImageDetectorFactory`;
  `get_detector()` → `get_image_detector()`.
- `backends/hailo/HailoDetector.py` → `hailo_detector.py`; `backends/ultralytics/YOLODetector.py` → `yolo_detector.py`
  (classes `HailoImageDetector` / `YoloImageDetector` kept; `YOLOModel` enum kept).
- Remove the `# TODO: Unify naming for images / speech` in `image_detector.py`.
- `main.py` import + call updated.

**speech/ → audio/**:
- `git mv speech audio`; `git mv audio/audio audio/capture`.
- `audio/speech_detector.py` → `audio_detector.py` (`SpeechDetector` → `AudioDetector`, `transcribe()` kept).
- `audio/speech_detector_factory.py` → `audio_detector_factory.py` (`SpeechDetectorFactory` → `AudioDetectorFactory`, `get_speech_detector()` → `get_audio_detector()`).
- `audio/speech_detection_model.py` → `audio_model.py` (`SpeechDetectionModel` → `AudioModel`).
- `audio/speech_testing.py` → `audio_testing.py`.
- `audio/backends/vosk/vosk_speech_detector.py` → `vosk_audio_detector.py` (`VoskSpeechDetector` → `VoskAudioDetector`).
- `audio/backends/faster_whisper/WhisperTranscriber.py` → `whisper_audio_detector.py` (`WhisperSpeechDetector` → `WhisperAudioDetector`; `WhisperModel` enum kept).
- **Kept:** `audio/transcript.py`, `audio/keywords/` and their `Speech*`/`Transcript` types.
- `dashboard/sources/speech.py` → `audio.py`; `SpeechSource` → `AudioSource`; channel `"speech.transcript"` → `"audio.transcript"`.
- `tests/speech/` → `tests/audio/` (mirror: `audio/capture/`, `audio/backends/...`, `audio/keywords/`).
- pyproject: extra `speech` → `audio` (C1); script `robot-friend-speech` → `robot-friend-audio` → `audio_testing:main` (C2).
- justfile: `--extra speech` → `--extra audio`; `listen` runs `robot-friend-audio`.
- Imports in `main.py`, `dashboard/*`, `scripts/download_data.py` updated.

**Verify:** `uv run pytest`; `uv run robot-friend-audio` import-boots.

### Phase D — One data-download script

New `src/robot_friend/scripts/download_data.py`; delete `download_models.py`, `download_vosk.py`,
`download_whisper.py`. Three editable lists at top:

```python
YOLO_MODELS   = [YOLOModel.YOLO_V8N]
VOSK_MODELS   = [VoskModel.VOSK_SMALL_EN_US_015, VoskModel.VOSK_SMALL_DE_015]
WHISPER_MODELS = [WhisperModel.SMALL]   # add sizes as needed
```

- For-loop per list; **idempotent** (skip if target dir/file already exists — no `clean_setup_dir`).
- Fix the whisper dir bug → `get_whisper_model_dir()`.
- No argparse (edit the lists). Shared helpers for "skip-if-present" + `finch_logger` progress.
- justfile: single `download` recipe (no args), drop the three `download-*` recipes.

**Verify:** dry import + `just download` skips existing vosk/yolo, fetches whisper into `data/models/whisper/`.

### Phase E — Setup script + recipes (asks #2, #4, #6)

`scripts/` (repo root):
- `scripts/lib.sh` — sourced helper with `is_pi()` (mirrors `is_pi_host`: `uname -m` + `/proc/device-tree/model`).
- `scripts/setup.sh` — **full provision, auto-detect.** Pi branch = current `pi/setup.sh` body (apt, dkms/Hailo,
  PCIe Gen3, uv+just, venv sync, picamera2 check). Dev branch = `uv sync --all-extras --dev --group viz-test`
  + `uv run playwright install chromium` ("all the things").
- `scripts/sync.sh` — **fast dep sync, auto-detect** (no apt/browser). Pi = system-interpreter
  `--system-site-packages` venv + `uv sync --extra audio`. Dev = `uv sync --all-extras --dev`.
- Delete `pi/setup.sh`; `pi/justfile setup` ssh-runs `scripts/setup.sh`; `pi/justfile run` uses `just sync`.

Root recipes: `setup` → `scripts/setup.sh`; `sync` → `scripts/sync.sh`; `download`;
`test` (→ `just arduino::test` then `uv run pytest`, in order); `test-visual`; `gallery`;
`run`/`listen`/`dashboard`. No user-facing flags.

**Verify:** `just setup` (dev) green end-to-end; `just test` runs arduino then python.

### Phase F — Google-style docstrings (ask #8)

Convert reST → Google in `clean_setup_dir.py`, `get_current_host.py`. Add `Attributes:` to dataclasses
(`detection.py`, `transcript.py`, `keyword.py`, `coordinate.py`) and class/`Returns:` docstrings to ABCs &
non-trivial methods (`image_detector.py`, `audio_detector.py`, `audio_model.py`, `vad_segmenter.py`,
`vosk_audio_detector.transcribe`). Skip obvious getters/setters.

### Phase G — Trim comments (ask #9)

Remove obvious one-liners (`# Run the Python test suite`, `# Sync the repo to the Pi`,
`Setting up the Python environment`, etc.) and inline CLI examples in recipes. **Keep** non-obvious WHY
(the system-site-packages rationale, PCIe-Gen3 note, dkms self-heal) but condensed. Trim verbose pyproject
extra comments to one line each.

### Phase H — Date-prefix plans (ask #7)

- `diagnostics-dashboard.md` → `2026-06-18-dashboard.md`; `diagnostics-testing.md` → `2026-06-18-dashboard-testing.md`
  (git creation date = 2026-06-18). This file is already `2026-06-19-…`.
- Update `[[diagnostics-testing]]` cross-link, the `pyproject.toml` comment referencing the testing-plan path,
  and `diagnostics → dashboard` wording inside the two plans.
- Update the auto-memory pointers that name these files.

### Phase I — Docs

- Root `README.md`: drop the three-module split / `python/` paths; document root layout, `just setup`/`sync`/`test`/`download`, new names.
- Merge `python/README.md` content into root (then it's gone with the move) or keep a short root section.
- `dashboard/README.md`: real description.

### Phase J — CI

Mirror `just test`: keep the `arduino` job; python job loses `working-directory: python`, runs
`uv sync --all-extras --dev` + `uv run pytest`. Add a separate **`visual`** job:
`uv sync --all-extras --group viz-test` + `playwright install chromium` + `uv run pytest -m visual`.

### Phase K — CLAUDE.md

Append project-orientation notes (root layout, the two setup modes, naming conventions
image/audio + dashboard, where the download lists live, how to run tests). Preserve the user's existing rules.

---

## 4. Risks & mitigations

- **Import breakage during renames** → mechanical rewrites, `uv run pytest` after every phase, grep for stale paths.
- **Lost git history on moves** → use `git mv`.
- **Pi provisioning untestable here** → keep the proven `pi/setup.sh` body verbatim in the Pi branch; only restructure the dispatch.
- **Editor/uv confusion mid-move** → recreate `.venv` at root once, after Phase A.
- **External-facing renames (C1/C2, recipe names)** → documented in README + CLAUDE.md so the team isn't surprised.

## 5. Verification checklist

- [ ] `uv run pytest` → 35 passed, from repo root.
- [ ] `uv run pytest -m visual` (after `just setup`) → green.
- [ ] `pio test -e native` (arduino) → green.
- [ ] `just setup`, `just sync`, `just test`, `just download`, `just dashboard`, `just run`, `just listen` resolve & run.
- [ ] `grep -ri diagnostics` → only intentional history; `grep -rn "robot_friend.speech"` → none.
- [ ] CI green (arduino + python + visual jobs).
- [ ] No stale `python/` dir; venv at root auto-detected.
