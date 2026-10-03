"""Local workspace persistence and numerical models for NEON//HUB."""
import copy
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

from calculator_core import CalculationError, FUNCTIONS, _bounded, evaluate

ACCENTS = {"Neon green": "#BAFF69", "Ice cyan": "#66D9EF", "Amber": "#FFD08A", "Lilac": "#C7ABFF"}
FUNCTION_HINTS = {
    "sqrt": "sqrt(x) — square root; x >= 0", "log": "log(x, base=e) — logarithm",
    "ln": "ln(x) — natural logarithm", "log2": "log2(x) — logarithm base 2",
    "log10": "log10(x) — logarithm base 10", "sin": "sin(x) — sine, radians",
    "cos": "cos(x) — cosine, radians", "tan": "tan(x) — tangent, radians",
    "abs": "abs(x) — magnitude", "floor": "floor(x) — round toward negative infinity",
    "ceil": "ceil(x) — round toward positive infinity", "round": "round(x, digits=0) — rounding",
    "fact": "fact(n) — factorial, integer 0..500", "gcd": "gcd(a, b) — greatest common divisor",
    "lcm": "lcm(a, b) — least common multiple", "popcount": "popcount(n) — count set bits",
}
RESERVED = set(FUNCTIONS) | {"ans", "pi", "e", "tau"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_directory():
    override = os.environ.get("NEON_HUB_DATA_DIR")
    if override:
        return Path(override).expanduser()
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return root / "NeonCyberHub"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.stem + "-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=True, allow_nan=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def new_workspace():
    return {"history": [], "variables": {}, "pins": [], "favorites": [],
            "bookmarks": {}, "notes": "", "watchlist": ["Windows", "Chrome", "OpenSSL", "Cisco"],
            "ans": 0, "expression": "2 ** 10"}


class WorkspaceStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else data_directory()
        self.path = self.directory / "workspaces.json"
        self.warning = ""
        self.needs_backup = False
        self.state = {
            "version": 2, "active": "Main", "workspaces": {"Main": new_workspace()},
            "settings": {"accent": "Neon green", "reduced_motion": False,
                         "online_news": True, "auto_refresh": True},
        }
        self.load()

    @property
    def workspace(self):
        return self.state["workspaces"][self.state["active"]]

    def load(self):
        if not self.path.exists():
            return
        try:
            if self.path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Workspace file is too large.")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("version") != 2:
                raise ValueError("Unsupported workspace format.")
            if not isinstance(raw.get("workspaces"), dict) or not raw["workspaces"]:
                raise ValueError("No valid workspace found.")
            workspaces = {}
            for name, entry in list(raw["workspaces"].items())[:20]:
                if not isinstance(name, str) or not 1 <= len(name) <= 64 or not isinstance(entry, dict):
                    continue
                clean = new_workspace()
                clean["notes"] = str(entry.get("notes", ""))[:200000]
                clean["expression"] = str(entry.get("expression", ""))[:512]
                clean["history"] = [
                    [str(item[0])[:512], str(item[1])[:1500]]
                    for item in entry.get("history", [])[:100]
                    if isinstance(item, (list, tuple)) and len(item) == 2
                ]
                clean["pins"] = [
                    {"expression": str(item["expression"])[:512], "result": str(item["result"])[:1500]}
                    for item in entry.get("pins", [])[:100]
                    if isinstance(item, dict) and "expression" in item and "result" in item
                ]
                clean["watchlist"] = [str(item)[:64] for item in entry.get("watchlist", [])[:40] if str(item).strip()]
                clean["favorites"] = [str(item)[:100] for item in entry.get("favorites", [])[:100]]
                bookmarks = entry.get("bookmarks", {})
                clean["bookmarks"] = {str(key): item for key, item in list(bookmarks.items())[:200]
                                      if isinstance(item, dict) and isinstance(item.get("title"), str)}
                for key, value in list(entry.get("variables", {}).items())[:64]:
                    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", key) and key not in RESERVED:
                        clean["variables"][key] = _bounded(value)
                clean["ans"] = _bounded(entry.get("ans", 0))
                workspaces[name] = clean
            if not workspaces:
                raise ValueError("No valid workspace found.")
            self.state["workspaces"] = workspaces
            self.state["active"] = raw.get("active") if raw.get("active") in workspaces else next(iter(workspaces))
            settings = raw.get("settings", {})
            if settings.get("accent") in ACCENTS:
                self.state["settings"]["accent"] = settings["accent"]
            for key in ("reduced_motion", "online_news", "auto_refresh"):
                if type(settings.get(key)) is bool:
                    self.state["settings"][key] = settings[key]
        except (ValueError, TypeError, AttributeError, KeyError, OSError, CalculationError) as exc:
            self.warning = "Could not load workspace: " + str(exc)
            self.needs_backup = True

    def save(self):
        if self.needs_backup and self.path.exists():
            backup = self.path.with_name("workspaces.recovery-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
            os.replace(self.path, backup)
            self.needs_backup = False
        atomic_json(self.path, self.state)

    def create(self, name):
        name = name.strip()
        if not name or len(name) > 64:
            raise ValueError("Use a workspace name between 1 and 64 characters.")
        if name in self.state["workspaces"]:
            raise ValueError("That workspace already exists.")
        if len(self.state["workspaces"]) >= 20:
            raise ValueError("Up to 20 workspaces are supported.")
        previous = self.state["active"]
        self.state["workspaces"][name] = new_workspace()
        self.state["active"] = name
        try:
            self.save()
        except OSError:
            self.state["active"] = previous
            self.state["workspaces"].pop(name, None)
            raise


def evaluate_statement(source, ans, variables):
    match = re.fullmatch(r"\s*([A-Za-z][A-Za-z0-9_]{0,31})\s*=(?!=)\s*(.+)", source, re.S)
    if match:
        name, expression = match.groups()
        if name in RESERVED:
            raise CalculationError("That name is reserved for a function or constant.", 0)
        if name not in variables and len(variables) >= 64:
            raise CalculationError("A workspace supports up to 64 variables.")
        try:
            value = evaluate(expression, ans, variables)
        except CalculationError as exc:
            if exc.position is not None:
                exc.position += match.start(2)
            raise
        return value, name
    return evaluate(source, ans, variables), None


def float_details(source, width=64, variables=None):
    if width not in (32, 64):
        raise CalculationError("Choose IEEE-754 binary32 or binary64.")
    source = source.strip()
    if len(source) > 512:
        raise CalculationError("Keep float inputs under 512 characters.")
    try:
        try:
            value = float(source)
        except ValueError:
            value = float(evaluate(source, variables=variables or {}))
        code = ">f" if width == 32 else ">d"
        packed = struct.pack(code, value)
        value = struct.unpack(code, packed)[0]
    except (ValueError, OverflowError, struct.error):
        raise CalculationError("Value cannot be represented at this precision.") from None
    bits = format(int.from_bytes(packed, "big"), f"0{width}b")
    exponent_bits = 8 if width == 32 else 11
    fraction_bits = width - exponent_bits - 1
    exponent = int(bits[1:1 + exponent_bits], 2)
    fraction = int(bits[1 + exponent_bits:], 2)
    bias = (1 << (exponent_bits - 1)) - 1
    if exponent == (1 << exponent_bits) - 1:
        classification = "NaN" if fraction else "Infinity"
        exponent_value = "special"
    elif exponent == 0:
        classification = "Subnormal" if fraction else "Signed zero"
        exponent_value = str(1 - bias)
    else:
        classification = "Normal"
        exponent_value = str(exponent - bias)
    return {"bits": bits, "sign": bits[0], "exponent_bits": bits[1:1 + exponent_bits],
            "fraction_bits": bits[1 + exponent_bits:], "exponent": exponent,
            "unbiased": exponent_value, "bias": bias, "classification": classification,
            "hex": "0x" + packed.hex().upper(), "value": repr(value),
            "exact": str(Decimal.from_float(value)), "float_hex": value.hex(),
            "width": width, "fraction_width": fraction_bits}


COMPLEXITIES = ("log2(n)", "n", "n log2(n)", "n^2", "2^n", "n!")
CURVE_COLORS = ("#66D9EF", "#BAFF69", "#C7ABFF", "#FFD08A", "#FF7F8F", "#6EE7BA")


def growth_log10(name, n):
    n = max(1, float(n))
    if name == "log2(n)":
        return math.log10(max(math.log2(n), 1))
    if name == "n":
        return math.log10(n)
    if name == "n log2(n)":
        return math.log10(n) + math.log10(max(math.log2(n), 1))
    if name == "n^2":
        return 2 * math.log10(n)
    if name == "2^n":
        return n * math.log10(2)
    if name == "n!":
        return math.lgamma(n + 1) / math.log(10)
    raise ValueError("Unknown growth model.")


def scientific_from_log(log_value):
    if log_value < 7:
        return f"{10 ** log_value:,.5g}"
    exponent = math.floor(log_value)
    return f"{10 ** (log_value - exponent):.4g}e+{exponent:,}"


def complexity_estimate(name, n, ns_per_operation):
    if not 1 <= n <= 100000:
        raise CalculationError("Choose n between 1 and 100,000.")
    if not math.isfinite(ns_per_operation) or not 1e-9 <= ns_per_operation <= 1e12:
        raise CalculationError("Operation cost must be between 1e-9 and 1e12 nanoseconds.")
    if n == 1 and name in ("log2(n)", "n log2(n)"):
        return "0", "0 s"
    operations = growth_log10(name, n)
    seconds = operations + math.log10(ns_per_operation) - 9
    if seconds < -3:
        duration = f"{10 ** (seconds + 6):.4g} us"
    elif seconds < 0:
        duration = f"{10 ** (seconds + 3):.4g} ms"
    elif seconds < math.log10(60):
        duration = f"{10 ** seconds:.4g} s"
    elif seconds < math.log10(3600):
        duration = f"{10 ** seconds / 60:.4g} min"
    elif seconds < math.log10(86400):
        duration = f"{10 ** seconds / 3600:.4g} h"
    elif seconds < math.log10(31557600):
        duration = f"{10 ** seconds / 86400:.4g} days"
    else:
        duration = scientific_from_log(seconds - math.log10(31557600)) + " years"
    return scientific_from_log(operations), duration


def sample_graph(expression, x_min, x_max, variables=None, samples=360):
    if not all(math.isfinite(value) for value in (x_min, x_max)) or not -1e6 <= x_min < x_max <= 1e6:
        raise CalculationError("Use a finite x range between -1,000,000 and 1,000,000.")
    if not 10 <= samples <= 1000:
        raise CalculationError("Choose 10..1,000 graph samples.")
    points = []
    context = dict(variables or {})
    for index in range(samples + 1):
        x = x_min + (x_max - x_min) * index / samples
        context["x"] = x
        try:
            y = float(evaluate(expression, variables=context))
            points.append((x, y if math.isfinite(y) and abs(y) < 1e100 else None))
        except (CalculationError, OverflowError):
            points.append((x, None))
    if all(y is None for _, y in points):
        raise CalculationError("No finite points: check the expression, variables, and x range.")
    return points

