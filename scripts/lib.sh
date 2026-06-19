#!/usr/bin/env bash
# Shared helpers for setup.sh / sync.sh.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info() { printf '\n==> %s\n' "$*"; }

# True on a Raspberry Pi. The Pi's firmware publishes a device-tree model string
# that is absent on dev machines (mirrors robot_friend.utils.get_current_host).
is_pi() { grep -qi 'raspberry pi' /proc/device-tree/model 2> /dev/null; }

# Dev machine: every backend extra (browser-free; the visual suite is set up by setup.sh).
sync_dev() {
  cd "$REPO_ROOT"
  uv sync --all-extras --dev
}

# Pi: a venv built from the SYSTEM interpreter with system-site-packages, so it can
# see the apt-installed picamera2/Hailo bindings (a uv-managed Python cannot). Image
# inference runs on the AI HAT, so torch/ultralytics are skipped.
sync_pi() {
  cd "$REPO_ROOT"
  { grep -qs '^home = /usr/bin' .venv/pyvenv.cfg && grep -qsi 'include-system-site-packages = true' .venv/pyvenv.cfg; } \
    || { rm -rf .venv && uv venv --system-site-packages --python /usr/bin/python3; }
  UV_PYTHON=/usr/bin/python3 uv sync --dev --extra audio --extra dashboard
}
