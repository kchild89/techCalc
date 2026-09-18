# NEON//CALC

A hacker-themed desktop calculator and computer science toolkit. Dark panels,
neon green accents, keyboard controls, and a live bit register. Everything runs
locally using Python's standard library.

## Run

From this folder:

```powershell
python script.py
```

Python 3.10+ with Tkinter is required. No pip packages are needed. The standard
Windows Python installation includes Tkinter.

## Tools

- **Calculator:** arithmetic, scientific functions, hex/binary/octal literals,
  bitwise operators, shifts, session history, and the previous result (`ans`).
- **Bit inspector:** 8/16/32/64-bit words, clickable bits, two's complement,
  signed/unsigned views, AND/OR/XOR/NOT and left/right shifts.
- **Data units:** bits, bytes, SI units (kB–TB), and binary units (KiB–TiB).
- **Codec lab:** UTF-8/Base64/hex conversions, URL percent encoding, and
  SHA-256/SHA-1/MD5 checksums. Whitespace is preserved.
- **Subnet lab:** IPv4/IPv6 CIDR normalization, masks, address ranges and host
  counts, including /31, /32, /127 and /128.

## Examples

```text
(1 << 8) - 1
0xFF & 0b1010
log2(1024)
gcd(48, 18)
popcount(0xBEEF)
fact(10)
```

Use `**` for powers and `^` for XOR. Trigonometry uses radians.
Supported functions: sqrt, log, ln, log2, log10, sin, cos, tan, abs, floor,
ceil, round, fact, gcd, lcm, popcount. Constants: pi, e, tau, ans.

Bit operations wrap to the selected word width. Signed right shifts preserve
the sign bit. The regular calculator uses unbounded-width integer semantics,
with a 4,096-bit resource limit, and standard Python floating-point arithmetic.
Fractional data-unit results display 12 significant digits; copying uses the
full conversion value (up to 70 digits of precision).

URL decoding uses percent-decoding, preserving literal plus signs.
Hashes are one-way; SHA-1 and MD5 are provided for compatibility checksums.
History stays in memory and resets when the application closes.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl+1 through Ctrl+5 | Switch tools |
| Ctrl+L | Select the calculator expression |
| Enter | Calculate, inspect bits, or map a network |
| Escape | Clear the calculator |
| Ctrl+Shift+C | Copy the latest calculator result |
| Ctrl+Enter in codec input | Transform text |

Double-click a history entry to recall it. Select an expression before typing
to replace it. Function buttons insert a function opening; supply its arguments
and closing parenthesis.

## Tests

```powershell
python -B -m unittest -v
```

Arithmetic is parsed with an allowlisted AST interpreter. Python code is never
evaluated. No requests leave the computer and no additional packages are needed.

