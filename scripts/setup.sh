#!/usr/bin/env bash
# Provision this machine for robot-friend, end to end. Auto-detects a Raspberry Pi
# (full system setup) vs a dev machine (uv env with every extra + the visual suite).
# Idempotent: safe to re-run.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

setup_dev() {
  info "Dev machine: syncing all extras + dev + visual-test deps"
  sync_dev
  uv sync --all-extras --dev --group viz-test
  info "Installing Playwright Chromium for the visual suite"
  uv run --group viz-test playwright install chromium
  info "Done — try 'just test' or 'just run'"
}

setup_pi() {
  local boot_config=/boot/firmware/config.txt reboot_needed=0

  info "Updating system packages"
  sudo apt update
  sudo apt full-upgrade -y

  # dkms MUST be present before hailo-all, or (since Trixie) the driver never builds.
  info "Installing apt packages (Hailo stack, camera stack, audio, utils)"
  dpkg -s hailo-all > /dev/null 2>&1 || reboot_needed=1
  sudo apt install -y dkms
  # libportaudio2: PortAudio runtime that the `sounddevice` wheel dlopens at import
  # (mic capture / dashboard audio source); the pip wheel ships no bundled library.
  sudo apt install -y git curl hailo-all python3-picamera2 rpicam-apps libportaudio2 i2c-tools btop nvtop tmux vim neovim

  # Self-heal: if hailo-all installed before dkms, re-running the driver package builds it.
  if ! sudo dkms status 2> /dev/null | grep -qi hailo; then
    sudo apt reinstall -y hailort-pcie-driver
  fi
  lsmod | grep -q hailo_pci || sudo modprobe hailo_pci || reboot_needed=1

  # The AI HAT+ runs at reduced speed on PCIe Gen 2.
  info "Enabling PCIe Gen 3"
  if ! grep -q '^dtparam=pciex1_gen=3' "$boot_config"; then
    echo 'dtparam=pciex1_gen=3' | sudo tee -a "$boot_config" > /dev/null
    reboot_needed=1
  fi

  info "Enabling I2C"
    if ! grep -q '^dtparam=i2c_arm=on' "$boot_config"; then
      echo 'dtparam=i2c_arm=on' | sudo tee -a "$boot_config" > /dev/null
      reboot_needed=1
    fi
    # i2c-dev exposes the /dev/i2c-* char devices that userspace (smbus, i2cdetect) needs.
    grep -qx 'i2c-dev' /etc/modules || echo 'i2c-dev' | sudo tee -a /etc/modules > /dev/null
    lsmod | grep -q '^i2c_dev' || sudo modprobe i2c-dev

  info "Installing uv and just"
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  command -v just > /dev/null \
    || curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$HOME/.local/bin"

  info "Setting up the Python environment"
  sync_pi
  if ! (cd "$REPO_ROOT" && UV_PYTHON=/usr/bin/python3 uv run --no-sync python -c 'import picamera2'); then
    echo "error: the venv cannot import picamera2 — is python3-picamera2 installed?" >&2
    exit 1
  fi

  if [ "$reboot_needed" = 1 ]; then
    info "Done — reboot now (sudo reboot), then run 'just pi check'"
  else
    info "Done — run 'just pi check' to verify the AI HAT and camera"
  fi
}

if is_pi; then
  setup_pi
else
  setup_dev
fi
