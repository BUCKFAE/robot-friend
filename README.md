# Robot Friend

The repo is split into three top-level modules:

- `arduino/` — PlatformIO firmware (sketch, libs, tests, clangd setup).
- `python/` — host-side Python package, managed with `uv`.
- `pi/` — Raspberry Pi provisioning (setup script, systemd service).

The top-level `justfile` exposes them as [just modules](https://just.systems/man/en/modules.html).

## Getting Started

Prerequisites: [PlatformIO Core](https://docs.platformio.org/page/core/installation/index.html),
[uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), Python 3.12+.

```sh
just                       # list all recipes
just arduino test          # run host tests for the firmware
just arduino test-uno      # run tests on a connected Uno
just arduino build         # compile firmware for the Uno
just arduino upload        # flash the Uno + open serial monitor

just python sync           # install / sync Python deps
just python test           # run the Python test suite
just python run            # invoke the robot-friend CLI
```

Each subdirectory has its own `justfile` — you can also `cd arduino && just test`.

## Raspberry Pi setup

Flash Raspberry Pi OS (64-bit, Bookworm or newer) with the
[Raspberry Pi Imager](https://www.raspberrypi.com/software/) — set hostname,
user, wifi and enable SSH in the Imager's customization dialog. Then add an
ssh alias for the Pi to `~/.ssh/config` on your dev machine and `ssh-copy-id` your key

```
Host finch-lab
    HostName <pi-ip>
    User finch
```

### Camera over ssh

The Pi runs headless and serves video over the network; the live view (ffplay)
opens on your dev machine:

```sh
just pi::run                # detect on the AI HAT, serve the annotated MJPEG view + open it
just pi::connect            # view the MJPEG stream served by a running `just pi::run`
just pi::stream             # raw camera, H.264 over TCP, no robot-friend code + open it
```

### Arduino layout

- `arduino/src/main.cpp` — Arduino sketch.
- `arduino/lib/<Name>/` — testable libraries; built for both host and Uno.
- `arduino/test/test_<name>/` — unit tests, auto-discovered by PlatformIO.

`arduino/compile_commands.json` (clangd's project database) is regenerated
automatically by every `just arduino` recipe.

### Using Obsidian

Install [Obsidian](https://obsidian.md/) and open the `FinchObsidian/` folder as a vault for the project notes.

### Using VSCode

Install the [PlatformIO IDE](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide)
extension and open the `arduino/` folder. The `just` recipes and
`scripts/gen_compile_commands.py` are not needed.
