set windows-shell := ["powershell", "-NoProfile", "-Command"]

_default:
  just --list

# Build the firmware for the connected Uno.
build:
  pio run -e uno

# Upload firmware to the board and open the serial monitor.
upload:
  pio run -t upload
  pio device monitor

# Run unit tests on the host (Mac/Linux/Windows).
test:
  pio test -e native

# Run unit tests on the connected Uno.
test-uno:
  pio test -e uno

# Regenerate compile_commands.json (clangd's project database).
gen-db:
  python3 scripts/gen_compile_commands.py
