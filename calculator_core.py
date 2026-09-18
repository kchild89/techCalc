"""Computation tools for NEON//CALC. Standard library only."""
import ast
import base64
import hashlib
import ipaddress
import math
import operator
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import quote, unquote


class CalculationError(ValueError):
    """A readable error suitable for displaying in the interface."""


def _bounded(value):
    if type(value) not in (int, float):
        raise CalculationError("Only real numbers are supported.")
    if isinstance(value, int) and value.bit_length() > 4096:
        raise CalculationError("Result exceeds the 4,096-bit calculation limit.")
    if isinstance(value, float) and not math.isfinite(value):
        raise CalculationError("Result is outside the finite number range.")
    return value


def _factorial(value):
    if type(value) is not int or not 0 <= value <= 500:
        raise CalculationError("fact() needs an integer between 0 and 500.")
    return math.factorial(value)


FUNCTIONS = {
    "sqrt": math.sqrt, "log": math.log, "ln": math.log,
    "log2": math.log2, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "abs": abs, "floor": math.floor, "ceil": math.ceil,
    "round": round, "fact": _factorial, "gcd": math.gcd,
    "lcm": math.lcm, "popcount": int.bit_count,
}
BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.BitAnd: operator.and_, ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Invert: operator.invert}


def evaluate(source, ans=0):
    """Evaluate an allowlisted arithmetic AST; never execute Python source."""
    source = source.strip()
    if not source:
        raise CalculationError("Enter an expression to begin.")
    if len(source) > 512:
        raise CalculationError("Keep expressions under 512 characters.")
    try:
        tree = ast.parse(source, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 160:
            raise CalculationError("This expression has too many operations.")

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                return _bounded(node.value)
            if isinstance(node, ast.Name):
                constants = {"pi": math.pi, "e": math.e, "tau": math.tau, "ans": ans}
                if node.id in constants:
                    return _bounded(constants[node.id])
                raise CalculationError("Unknown name: " + node.id)
            if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
                return _bounded(UNARY[type(node.op)](visit(node.operand)))
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                kind = type(node.op)
                if kind is ast.Pow:
                    if abs(right) > 4096:
                        raise CalculationError("Exponent must be between -4096 and 4096.")
                    if type(left) is int and type(right) is int and right > 0:
                        if max(0, abs(left).bit_length() - 1) * right > 4096:
                            raise CalculationError("Power exceeds the 4,096-bit limit.")
                    return _bounded(operator.pow(left, right))
                if kind in (ast.LShift, ast.RShift):
                    if type(left) is not int or type(right) is not int:
                        raise CalculationError("Bit shifts require integers.")
                    if not 0 <= right <= 4096:
                        raise CalculationError("Shift count must be between 0 and 4096.")
                    return _bounded(left << right if kind is ast.LShift else left >> right)
                if kind in BINARY:
                    return _bounded(BINARY[kind](left, right))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FUNCTIONS and not node.keywords and len(node.args) <= 3:
                    return _bounded(FUNCTIONS[node.func.id](*(visit(arg) for arg in node.args)))
            raise CalculationError("Use numbers, arithmetic operators, and supported functions.")

        return visit(tree.body)
    except CalculationError:
        raise
    except ZeroDivisionError:
        raise CalculationError("Cannot divide by zero.") from None
    except SyntaxError:
        raise CalculationError("Check the expression and matching parentheses.") from None
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise CalculationError("Invalid operation: " + str(exc)) from None


def format_number(value):
    if type(value) is int:
        return str(value)
    return format(value, ".14g")


def word_details(value, width):
    if type(value) is not int:
        raise CalculationError("The bit inspector needs an integer.")
    if width not in (8, 16, 32, 64):
        raise CalculationError("Choose an 8, 16, 32, or 64-bit word.")
    unsigned = value & ((1 << width) - 1)
    signed = unsigned - (1 << width) if unsigned & (1 << (width - 1)) else unsigned
    return {
        "unsigned": unsigned, "signed": signed,
        "binary": format(unsigned, "0" + str(width) + "b"),
        "hex": "0x" + format(unsigned, "0" + str(width // 4) + "X"),
        "octal": "0o" + format(unsigned, "o"),
        "ones": unsigned.bit_count(),
        "wrapped": value != unsigned,
    }


UNITS = {
    "bit": Decimal(1) / 8, "B": Decimal(1),
    "kB": Decimal(1000), "MB": Decimal(1000) ** 2,
    "GB": Decimal(1000) ** 3, "TB": Decimal(1000) ** 4,
    "KiB": Decimal(1024), "MiB": Decimal(1024) ** 2,
    "GiB": Decimal(1024) ** 3, "TiB": Decimal(1024) ** 4,
}


def convert_data(amount, source_unit, target_unit):
    if len(str(amount)) > 80:
        raise CalculationError("Enter a shorter amount.")
    try:
        with localcontext() as context:
            context.prec = 70
            value = Decimal(str(amount))
            if not value.is_finite() or value < 0 or value > Decimal("1e30"):
                raise CalculationError("Enter an amount between 0 and 1e30.")
            if value and value.adjusted() < -30:
                raise CalculationError("Smallest supported nonzero amount is 1e-30.")
            return value * UNITS[source_unit] / UNITS[target_unit]
    except (InvalidOperation, KeyError):
        raise CalculationError("Enter a valid amount and unit.") from None


CODECS = (
    "Text to Base64", "Base64 to text", "Text to hex", "Hex to text",
    "URL encode", "URL decode", "SHA-256", "SHA-1", "MD5",
)


def transform_text(source, mode):
    if len(source) > 65536:
        raise CalculationError("Input is limited to 65,536 characters.")
    try:
        raw = source.encode("utf-8")
        if mode == "Text to Base64":
            return base64.b64encode(raw).decode("ascii")
        if mode == "Base64 to text":
            return base64.b64decode("".join(source.split()), validate=True).decode("utf-8")
        if mode == "Text to hex":
            return raw.hex(" ")
        if mode == "Hex to text":
            return bytes.fromhex(source).decode("utf-8")
        if mode == "URL encode":
            return quote(source, safe="")
        if mode == "URL decode":
            return unquote(source, errors="strict")
        if mode in ("SHA-256", "SHA-1", "MD5"):
            return hashlib.new(mode.lower().replace("-", ""), raw).hexdigest()
        raise CalculationError("Choose a supported transformation.")
    except (ValueError, UnicodeError) as exc:
        raise CalculationError("Cannot decode this input: " + str(exc)) from None


def inspect_network(source):
    if len(source) > 128:
        raise CalculationError("Enter an IPv4 or IPv6 address with a CIDR prefix.")
    try:
        network = ipaddress.ip_network(source.strip(), strict=False)
    except ValueError:
        raise CalculationError("Use CIDR notation, such as 192.168.1.42/24 or 2001:db8::/64.") from None
    count = network.num_addresses
    if network.version == 4:
        first = network.network_address + (1 if count > 2 else 0)
        last = network.broadcast_address - (1 if count > 2 else 0)
        usable = count - 2 if count > 2 else count
    else:
        first = network.network_address + (1 if count > 2 else 0)
        last = network.broadcast_address
        usable = count - 1 if count > 2 else count
    return {
        "Network": str(network),
        "IP version": "IPv" + str(network.version),
        "Subnet mask": str(network.netmask),
        "Wildcard mask": str(network.hostmask),
        "First host": str(first),
        "Last host": str(last),
        "Broadcast" if network.version == 4 else "Last address": str(network.broadcast_address),
        "Total addresses": f"{count:,}",
        "Usable hosts": f"{usable:,}",
        "Prefix length": f"/{network.prefixlen}",
    }

