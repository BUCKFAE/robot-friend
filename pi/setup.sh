#!/usr/bin/env bash
# Provision a Raspberry Pi (64-bit, Bookworm or newer) for robot-friend.
# Idempotent: safe to re-run after a partial install or on a fresh SD card.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOT_CONFIG=/boot/firmware/config.txt
REBOOT_NEEDED=0

info() { printf '\n==> %s\n' "$*"; }

if [ "$(uname -m)" != aarch64 ]; then
  echo "warning: $(uname -m) is not arm64 — this script is meant for a Raspberry Pi 5" >&2
fi

info "Updating system packages"
sudo apt update
sudo apt full-upgrade -y

info "Installing apt packages (Hailo driver/runtime, camera stack)"
# hailo-all = kernel driver, firmware, HailoRT and the Tappas postprocessing,
# including precompiled models in /usr/share/hailo-models/. python3-picamera2
# provides the camera + Hailo Python bindings (apt-only, not on PyPI).
# Since Trixie the driver is built via dkms, which MUST be present before
# hailo-all installs or the driver silently never gets built.
dpkg -s hailo-all > /dev/null 2>&1 || REBOOT_NEEDED=1
sudo apt install -y dkms
sudo apt install -y git curl hailo-all python3-picamera2 rpicam-apps

info "Installing util apt packages"
sudo apt install -y btop nvtop

# Self-heal: if hailo-all got installed before dkms, the driver was never
# registered/built — reinstalling the driver package re-runs the dkms build.
if ! sudo dkms status 2> /dev/null | grep -qi hailo; then
  echo "Hailo driver was never built — rebuilding via dkms"
  sudo apt reinstall -y hailort-pcie-driver
fi
lsmod | grep -q hailo_pci || sudo modprobe hailo_pci || REBOOT_NEEDED=1

info "Enabling PCIe Gen 3 (the AI HAT+ runs at reduced speed on Gen 2)"
if ! grep -q '^dtparam=pciex1_gen=3' "$BOOT_CONFIG"; then
  echo 'dtparam=pciex1_gen=3' | sudo tee -a "$BOOT_CONFIG" > /dev/null
  REBOOT_NEEDED=1
fi

info "Installing uv and just"
export PATH="$HOME/.local/bin:$PATH"
command -v uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v just > /dev/null || \
  curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$HOME/.local/bin"

info "Setting up the Python environment"
cd "$REPO_DIR"
just python sync-pi
if ! (cd python && UV_PYTHON=/usr/bin/python3 uv run --no-sync python -c 'import picamera2'); then
  echo "error: the venv cannot import picamera2 — is python3-picamera2 installed?" >&2
  exit 1
fi

if [ "$REBOOT_NEEDED" = 1 ]; then
  info "Done — reboot now (sudo reboot), then run 'just pi check'"
else
  info "Done — run 'just pi check' to verify the AI HAT and camera"
fi
