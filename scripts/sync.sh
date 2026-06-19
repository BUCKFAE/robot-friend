#!/usr/bin/env bash
# Fast dependency sync for this machine (auto-detects Pi vs dev). No apt/browser
# installs — that's `just setup`. Run after pulling code; used by `just pi run`.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if is_pi; then
  sync_pi
else
  sync_dev
fi
