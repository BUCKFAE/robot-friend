#!/usr/bin/env python3
"""Write compile_commands.json so clangd (and therefore nvim) can parse the project.

PlatformIO's built-in `pio run -t compiledb` only covers files that the
firmware build touches: src/ and lib/. Test files under test/ are built
by `pio test`, which doesn't write a database, so clangd would otherwise
show every test as red.

This script runs compiledb for the uno env, then appends one fake entry
per test file as if the host compiler had built it. The test entries use
g++/clang++ instead of avr-g++ so STL headers resolve normally.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "compile_commands.json"
UNO_ENV = "uno"
NATIVE_ENV = "native"
LIB_DIR = ROOT / "lib"
TEST_DIR = ROOT / "test"
INCLUDE_DIR = ROOT / "include"
UNITY_INC = ROOT / ".pio" / "libdeps" / NATIVE_ENV / "Unity" / "src"
UNITY_CFG = ROOT / ".pio" / "build" / NATIVE_ENV / "unity_config"


def fatal(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def watch_paths() -> list[Path]:
    """Paths whose mtime invalidates compile_commands.json."""
    out = [ROOT / "platformio.ini"]
    # Directory mtimes change when files are added/removed inside them, so
    # watching each lib/<Name>/ and test/test_<name>/ catches new sources
    # without scanning every file.
    for parent in (LIB_DIR, TEST_DIR):
        if parent.exists():
            out.append(parent)
            out += [p for p in parent.iterdir() if p.is_dir()]
    return out


def is_stale() -> bool:
    if not DB.exists():
        return True
    db_mtime = DB.stat().st_mtime
    return any(p.exists() and p.stat().st_mtime > db_mtime
               for p in watch_paths())


def find_pio() -> str:
    pio = shutil.which("pio") or shutil.which("platformio")
    if not pio:
        fatal(
            "pio not found in PATH — install PlatformIO Core "
            "(https://docs.platformio.org/page/core/installation/index.html)"
        )
    return pio


def find_host_cxx() -> str:
    """Return a host C++ compiler clangd can probe for system headers."""
    for name in ("clang++", "g++", "c++"):
        path = shutil.which(name)
        if path:
            return path
    fatal("no host C++ compiler (clang++/g++/c++) found in PATH")


def fetch_unity(pio: str) -> None:
    """Ensure .pio/libdeps/<NATIVE_ENV>/Unity/ exists so tests resolve unity.h."""
    if (UNITY_INC / "unity.h").exists():
        return
    print(f"  fetching Unity for env={NATIVE_ENV}...")
    subprocess.run(
        [pio, "test", "-e", NATIVE_ENV,
         "--without-testing", "--without-uploading"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if not (UNITY_INC / "unity.h").exists():
        fatal(
            f"could not locate Unity at {UNITY_INC} — try running "
            f"`pio test -e {NATIVE_ENV}` once manually"
        )


def gen_uno_db(pio: str) -> list[dict]:
    print(f"  running `pio run -t compiledb -e {UNO_ENV}`...")
    p = subprocess.run(
        [pio, "run", "-t", "compiledb", "-e", UNO_ENV],
        cwd=ROOT, text=True, capture_output=True,
    )
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        fatal(f"`pio run -t compiledb -e {UNO_ENV}` failed")
    if not DB.exists():
        fatal(f"{DB.name} was not produced by pio")
    return json.loads(DB.read_text())


def project_lib_includes() -> list[Path]:
    """Every lib/<Name>/ — PlatformIO adds each automatically at build time."""
    if not LIB_DIR.exists():
        return []
    return sorted(p for p in LIB_DIR.iterdir() if p.is_dir())


def test_files() -> list[Path]:
    """Every .c/.cc/.cpp/.cxx under test/test_*/."""
    if not TEST_DIR.exists():
        return []
    out: list[Path] = []
    for tdir in sorted(TEST_DIR.iterdir()):
        if tdir.is_dir() and tdir.name.startswith("test_"):
            out += sorted(
                p for p in tdir.iterdir()
                if p.is_file() and p.suffix in (".c", ".cc", ".cpp", ".cxx")
            )
    return out


def native_test_entry(cxx: str, src: Path, includes: list[Path]) -> dict:
    """Build a compile_commands entry as if the host compiler built this test."""
    rel = src.relative_to(ROOT)
    out = f".pio/build/test_clangd/{src.parent.name}/{src.stem}.o"
    # Do NOT pass -DUNITY_INCLUDE_CONFIG_H: at PlatformIO test time that
    # macro is defined and unity_config.h is generated under
    # .pio/build/<env>/unity_config/, but for clangd's parse we just want
    # unity.h to skip the optional include.
    parts = [cxx, "-c", "-std=gnu++17", "-Wall", "-Wextra"]
    for inc in includes:
        try:
            parts.append("-I" + str(inc.relative_to(ROOT)))
        except ValueError:
            parts.append("-I" + str(inc))
    parts += ["-o", out, str(rel)]
    return {
        "directory": str(ROOT),
        "command": shlex.join(parts),
        "file": str(rel),
        "output": out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-deps", action="store_true",
        help="don't try to fetch Unity (use existing .pio/libdeps)",
    )
    parser.add_argument(
        "-f", "--force", action="store_true",
        help="regenerate even if compile_commands.json looks up to date",
    )
    args = parser.parse_args()

    if not args.force and not is_stale():
        print("compile_commands.json is up to date — nothing to do "
              "(pass --force to regenerate anyway)")
        return 0

    pio = find_pio()
    cxx = find_host_cxx()

    if not args.skip_deps:
        fetch_unity(pio)

    db = gen_uno_db(pio)

    tests = test_files()
    n_tests = 0
    if tests:
        includes = []
        if UNITY_INC.exists():
            includes.append(UNITY_INC)
        if UNITY_CFG.exists():
            includes.append(UNITY_CFG)
        if INCLUDE_DIR.exists():
            includes.append(INCLUDE_DIR)
        includes += project_lib_includes()
        # Each test directory itself, in case tests share local headers.
        seen: set[Path] = set()
        for t in tests:
            if t.parent not in seen:
                includes.append(t.parent)
                seen.add(t.parent)

        for t in tests:
            db.append(native_test_entry(cxx, t, includes))
            n_tests += 1

    DB.write_text(json.dumps(db, indent=2) + "\n")
    print(
        f"wrote {len(db)} entries to {DB.relative_to(ROOT)} "
        f"({n_tests} synthesized for test/)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
