# Robot Friend

## Getting Started

Prerequisites: [PlatformIO Core](https://docs.platformio.org/page/core/installation/index.html), [just](https://github.com/casey/just), Python 3.

```sh
just test       # run host tests
just test-uno   # run tests on a connected Uno
just build      # compile firmware for the Uno
just upload     # flash the Uno + open serial monitor
```

Project layout:

- `src/main.cpp` — Arduino sketch.
- `lib/<Name>/` — testable libraries; built for both host and Uno.
- `test/test_<name>/` — unit tests, auto-discovered by PlatformIO.

`compile_commands.json` (clangd's project database) is regenerated
automatically by every `just` recipe.

### Using VSCode

Install the [PlatformIO IDE](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide)
extension and open the project folder. The `just` recipes and
`scripts/gen_compile_commands.py` are not needed.

