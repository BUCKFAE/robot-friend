mod arduino
mod pi

_default:
  just --list

# Provision this machine end-to-end (auto-detects Raspberry Pi vs dev machine).
setup:
  scripts/setup.sh

# Fast dependency sync for this machine (auto-detects Pi vs dev).
sync:
  scripts/sync.sh

# Download the model assets listed at the top of download_data.py (idempotent).
download:
  uv run --all-extras src/robot_friend/scripts/download_data.py

# Run every test suite in order: firmware host tests, then Python unit tests.
test:
  just arduino::test
  uv run --all-extras pytest

# Browser-based visual + E2E suite (run `just setup` first for Playwright + Chromium).
test-visual:
  uv run --all-extras --group viz-test pytest -m visual

# Regenerate the dashboard screenshot gallery for visual review.
gallery:
  uv run --all-extras --group viz-test pytest tests/dashboard/visual/test_gallery.py -m visual

# Run person detection (serves the annotated camera view as MJPEG; see --help).
run *args:
  uv run robot-friend {{args}}

# Listen on the mic, transcribe, and print transcripts + matched keywords.
listen *args:
  uv run robot-friend-audio {{args}}

# Run the dashboard web UI. `--demo-scenario nominal` = fake data, no hardware.
dashboard *args:
  uv run robot-friend-dashboard {{args}}
