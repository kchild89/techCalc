# NEON//HUB

A hacker-themed cybersecurity command station for Windows and macOS:
live security news, CISA vulnerability tracking, an explained command library,
saved workspaces, and interactive calculator/CS labs.

## Run

Requires **Python 3.10+ with Tkinter** for source launches. The app has no
third-party runtime dependencies.

```sh
# macOS
python3 script.py

# Windows
python script.py
```

Use `--offline` to disable news requests or `--data-dir PATH` for a separate
workspace. Launchers work from any current directory.

On macOS, use a current [python.org installer](https://www.python.org/downloads/macos/),
which [includes Tk](https://www.python.org/download/mac/tcltk/).
See the [macOS guide](docs/macos.md) for installation, app bundles, and troubleshooting.

Already built on Windows? Open **dist/NeonCyberHub.exe**.
Packaged desktop apps include Python and Tk; end users do not need Python.

## Build a desktop app

Build on the operating system you are targeting:

```sh
# macOS -> dist/NeonCyberHub.app
bash scripts/build_macos.sh
```

```powershell
# Windows -> dist/NeonCyberHub.exe
.\scripts\build_windows.ps1
```

Each script creates an isolated `.venv-build`, installs pinned PyInstaller
build tooling, and generates platform icons. The original
`build_windows.ps1` launcher still works.
[PyInstaller requires a separate build on each OS](https://www.pyinstaller.org/en/stable/usage.html);
a Windows build cannot produce the Mac app.

## Project layout

```text
agentApp/
├── src/neon_hub/
│   ├── app.py                 # CLI and application entry point
│   ├── __main__.py            # python -m neon_hub
│   ├── platform_support.py    # OS paths, fonts, shortcuts, wheel input
│   ├── core/                  # Calculator, persistence, numerical models
│   ├── services/              # News fetching, parsing, cache
│   ├── reference/             # Software descriptions and command recipes
│   └── ui/                    # Tk screens, reusable widgets, icon drawing
├── tests/                     # Unit and regression tests
├── scripts/                   # Native builds, icons, GUI smoke checks
├── docs/                      # User, Mac, and development guides
├── assets/                    # Original application artwork
├── .github/workflows/         # Windows and macOS CI builds
├── pyproject.toml             # Package metadata and neon-hub entry point
├── script.py                  # Compatible source launcher
├── build/                     # Generated intermediate files (ignored)
└── dist/                      # Generated distributables (ignored)
```

User data is stored outside the project. Existing Windows workspaces keep
their original location; no migration is needed.

| OS | Default data directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\NeonCyberHub` |
| macOS | `~/Library/Application Support/NeonCyberHub` |
| Linux source launch | `$XDG_DATA_HOME/NeonCyberHub`, or `~/.local/share/NeonCyberHub` |

## Development

Create and activate a virtual environment, then install the package:

```sh
python -m pip install -e .
python -m neon_hub
python -B -m unittest discover -s tests -v
python scripts/smoke_test.py
```

Use `python3` on macOS if `python` is unavailable. Installing the package
also provides a `neon-hub` GUI command. See
[development and architecture](docs/development.md) for setup and release checks.

## Guides

- [Using the hub](docs/user-guide.md): features, feeds, shortcuts, data, backups.
- [Running and building on macOS](docs/macos.md).
- [Development and architecture](docs/development.md).

The software library provides copyable, explained commands; it does not execute
them. Zero-day tags reflect publisher headlines. CISA KEV entries are tracked
separately as known-exploited vulnerabilities.
