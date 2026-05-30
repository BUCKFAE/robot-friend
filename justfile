set windows-shell := ["powershell", "-NoProfile", "-Command"]

_default:
  just --list

# Build the firmware for the connected Uno.
build: gen-db
  pio run -e uno

# Upload firmware to the board and open the serial monitor.
upload: gen-db
  pio run -t upload
  pio device monitor

# Run unit tests on the host (Mac/Linux/Windows).
test: gen-db
  pio test -e native

# Run unit tests on the connected Uno.
test-uno: gen-db
  pio test -e uno

# Regenerate compile_commands.json if platformio.ini / lib / test changed.
# (Cheap no-op when nothing has changed.)
gen-db:
  python3 scripts/gen_compile_commands.py
