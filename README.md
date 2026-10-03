# NEON//HUB

A hacker-themed cybersecurity command station for Windows. The original
NEON//CALC tools are now part of a larger workspace with live intelligence,
a command reference, notes, saved calculations, and interactive CS labs.

## Launch

Double-click **dist\NeonCyberHub.exe**. The executable bundles Python and Tk;
the computer running it does not need a Python installation.

To run from source, use Python 3.10+ with Tkinter:

```powershell
python script.py
```

The application itself uses only the Python standard library.

```powershell
python script.py --offline
python script.py --data-dir "C:\path\to\separate-workspace-data"
```

The data-directory option works with the executable too. An optional
NEON_HUB_DATA_DIR environment variable provides the same override.

## Command station

- **Command center:** source freshness, cached vulnerability totals, zero-day
  headline count, latest articles, and quick access to the tools.
- **Threat intelligence:** searchable news and research, CISA KEV records,
  vendor/product/CVE filters, a software watchlist, article bookmarks, source
  health, original links, publication dates, and fetch timestamps.
- **Tool library:** 32 explained recipes across Nmap, Wireshark/TShark, curl,
  OpenSSL, dig, tcpdump, YARA, PowerShell, Sysinternals, and jq.
- **My workspace:** named workspaces with notes, calculation history, pinned
  expressions, variables, command favorites, article bookmarks, and watchlists.
- **Settings:** four accent colors, reduced motion, offline mode, automatic
  refresh preferences, and per-source status.

The library provides copyable commands, prerequisites, expected output,
flag explanations, and official documentation. Target and port parameters are
validated before a command can be copied. Commands are not executed by the hub.
Example file names such as capture.pcapng, rules.yar, and evidence.bin must be
replaced with your own files. Software referenced in the library is installed
separately; follow each tool's official installation guidance.

## Intelligence sources

The app fetches these public sources in background threads:

- [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog),
  with [CISA's official GitHub mirror](https://github.com/cisagov/kev-data) as a fallback.
- [BleepingComputer RSS](https://www.bleepingcomputer.com/feed/)
- [The Hacker News RSS](https://feeds.feedburner.com/TheHackersNews)
- [Cisco Talos research RSS](https://blog.talosintelligence.com/rss/)

Online mode refreshes stale data at startup. Automatic updates run about every
30 minutes while the app remains open. The Refresh button is limited to one
attempt per 30 seconds. Disable online feeds to work entirely from the cache.

A **zero-day report** tag means the publisher used zero-day wording in the
headline. It is not an independent verification of exploitation or patch
availability. **CISA KEV** means a vulnerability is listed as known exploited;
KEV inclusion does not by itself establish that exploitation was a zero-day.
The CISA date shown in the list is the date added to the catalog, not the original
disclosure date. CISA remediation due dates apply in their agency context.

Each feed retains its last successful results when a refresh fails. Fetch time
and source errors remain visible. RSS publishers choose the history exposed by
their feeds, so this is not a comprehensive news archive. The browser shows up
to 500 matching records at once; refine searches to find older CISA entries.
Bookmarks preserve a local snapshot when an article later leaves its feed.

Your notes, calculator expressions, and command targets are not sent to the
news providers. Only public feed URLs are requested. Opening a source launches
your default browser.

## Calculator and CS labs

- **Calculator:** allowlisted arithmetic parser, syntax coloring, matching
  parentheses, function hints, Tab completion, error locations, history and pins.
- **Bit inspector:** 8/16/32/64-bit words, clickable bits, signed/unsigned views,
  hexadecimal/octal/binary representations, AND/OR/XOR/NOT, and shifts.
- **IEEE-754 inspector:** sign, exponent, fraction, classification, raw hex, and
  the exact stored decimal value for binary32 and binary64. Supports negative
  zero, subnormal values, infinities, and NaN.
- **Graphing:** compare up to three functions of x, zoom with the wheel, drag to
  pan, fit the view, and export sampled values to CSV. Separate expressions with
  semicolons, for example sin(x); cos(x).
- **Algorithm playground:** compare log2(n), n, n log2(n), n^2, 2^n, and n! for
  inputs up to 100,000. Change the cost per operation to explore estimated
  runtimes. Very large counts use logarithms, avoiding enormous allocations.
- **Data units:** bits, bytes, decimal SI units and binary IEC units.
- **Codec lab:** Base64, hex, URL encoding/decoding, SHA-256, SHA-1 and MD5.
- **Subnet lab:** IPv4/IPv6 network boundaries, masks, address ranges, and counts.

Try these calculator expressions:

```text
page_size = 4096
page_size * 128
0xFF & 0b1010
(1 << 8) - 1
log2(1024)
gcd(48, 18)
popcount(0xBEEF)
fact(10)
```

Use ** for powers and ^ for XOR. Trigonometry uses radians. Constants include
pi, e, tau, and ans. Function buttons insert an opening parenthesis; supply the
arguments and closing parenthesis. Binary operations in the regular calculator
use Python integer semantics with a 4,096-bit resource limit. The bit inspector
wraps results to its selected word width.

Graphing uses finite samples and breaks at undefined samples. It is an
exploration tool, not a proof of continuity or an exact root finder. Binary32
inspection rounds the evaluated Python binary64 value to binary32. Complexity
curves model growth rather than benchmark actual code or hardware.

## Keyboard controls

| Shortcut | Action |
| --- | --- |
| Ctrl+K | Search pages, command recipes, and calculator functions |
| Ctrl+S | Save the current workspace |
| Ctrl+L | Open and select the calculator expression |
| Ctrl+1 through Ctrl+9 | Open the first nine sidebar pages |
| Tab in calculator | Complete a function or variable name |
| Enter | Calculate, inspect, compare, or plot on the active lab |
| Escape in calculator | Dismiss completion or clear the expression |
| Ctrl+Shift+C | Copy the latest calculator result |
| Ctrl+Enter in codec input | Transform text |

Double-click a calculation history item or a workspace pin to reuse it.
Double-click a news item to open its original source.

## Local storage and backups

By default, files are stored under **%LOCALAPPDATA%\NeonCyberHub**:

- workspaces.json: profiles, notes, variables, history, pins, preferences and saved items.
- news-cache.json: feed data and per-source refresh status.
- error.log: UI exception tracebacks, if a callback fails.

Notes and saved items are plain local JSON, not encrypted storage.
Workspaces save after edits with a short debounce and when the app closes.
A malformed workspace file is retained as a timestamped recovery file before
a fresh state is written. Save failures are displayed instead of silently
discarding edits.

Use **Export backup** to export the active workspace. To restore an exported
backup into a separate profile directory, close the app, copy the backup there
as workspaces.json, and launch with --data-dir pointing at that directory.
Keep the original file if restoring over an existing directory.

## Tests and Windows build

```powershell
python -B -m unittest -v
.\build_windows.ps1
```

The build script creates an isolated .venv-build environment, installs the
pinned PyInstaller build dependency, regenerates the original shield icon,
and produces dist\NeonCyberHub.exe. Build artifacts and virtual environments
are ignored by Git. The locally built executable is not code-signed.

Core tests cover expression validation, workspace recovery and isolation,
IEEE-754 edge cases, graph domains, growth models, RSS/Atom/CISA parsing,
source fallback and cache retention, and command parameter validation.

## Project layout

- script.py: launch options and packaged-app smoke checks
- hub_ui.py: shell, dashboard, and calculator integration
- intel.py / intel_ui.py: feed ingestion, cache, news browser and command library UI
- workspace_ui.py: persistence controls, personalization and command palette
- hub_core.py: workspace store and numerical models
- labs_ui.py: IEEE-754, graphing, and complexity screens
- calculator_core.py / calculator_ui.py: original calculator and CS tools
- tool_library.py: curated software descriptions and command recipes
- widgets.py: rich expression entry and tooltips
- assets_icon.py / assets/: original application icon and generation source


