"""Regression tests for arithmetic boundaries and computer science conversions."""
import unittest
from decimal import Decimal

from calculator_core import (
    CalculationError, convert_data, evaluate, inspect_network,
    transform_text, word_details,
)


class CalculatorTests(unittest.TestCase):
    def test_precedence_and_programmer_literals(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)
        self.assertEqual(evaluate("2 ** 3 ** 2"), 512)
        self.assertEqual(evaluate("0xFF & 0b1010"), 10)
        self.assertEqual(evaluate("(1 << 8) - 1"), 255)
        self.assertEqual(evaluate("0o755"), 493)
        self.assertEqual(evaluate("5 ^ 3"), 6)

    def test_functions_and_last_answer(self):
        self.assertEqual(evaluate("sqrt(81) + log2(1024)"), 19)
        self.assertEqual(evaluate("gcd(48, 18) + popcount(0xFF)"), 14)
        self.assertEqual(evaluate("fact(6)"), 720)
        self.assertEqual(evaluate("ans * 2", ans=21), 42)
        self.assertAlmostEqual(evaluate("sin(pi / 2)"), 1)

    def test_rejects_code_and_non_numbers(self):
        for source in (
            "__import__('os')", "(1).__class__", "[1, 2]", "True", "'abc'",
            "(lambda: 1)()", "sqrt(x=4)", "[x for x in range(10)]",
        ):
            with self.subTest(source=source), self.assertRaises(CalculationError):
                evaluate(source)

    def test_readable_errors_and_resource_bounds(self):
        for source in (
            "", "1 / 0", "sqrt(-1)", "2 ** 999999", "1 << -1", "1 << 9000",
            "2 ** 4096", "1e309", "fact(501)", "1 & 1.5",
            "9" * 513, "1+" * 81 + "1", "(-1) ** 0.5",
        ):
            with self.subTest(source=source), self.assertRaises(CalculationError):
                evaluate(source)
        self.assertEqual(evaluate("1 << 4095").bit_length(), 4096)


class ProgrammerTests(unittest.TestCase):
    def test_word_wrapping_and_twos_complement(self):
        value = word_details(-1, 8)
        self.assertEqual(value["unsigned"], 255)
        self.assertEqual(value["signed"], -1)
        self.assertEqual(value["binary"], "11111111")
        self.assertEqual(value["hex"], "0xFF")
        self.assertEqual(value["ones"], 8)
        self.assertEqual(word_details(256, 8)["unsigned"], 0)
        self.assertEqual(word_details(1 << 63, 64)["signed"], -(1 << 63))
        with self.assertRaises(CalculationError):
            word_details(1.5, 16)

    def test_decimal_binary_and_bit_units(self):
        self.assertEqual(convert_data("1", "GiB", "B"), Decimal(1073741824))
        self.assertEqual(convert_data("1", "GB", "MB"), Decimal(1000))
        self.assertEqual(convert_data("1", "GiB", "MB"), Decimal("1073.741824"))
        self.assertEqual(convert_data("8", "bit", "B"), Decimal(1))
        self.assertEqual(convert_data("0.5", "KiB", "B"), Decimal(512))
        self.assertEqual(convert_data("0", "B", "TiB"), 0)

    def test_invalid_data_amounts(self):
        for amount in ("-1", "NaN", "Infinity", "oops", "1e31", "1e-100000"):
            with self.subTest(amount=amount), self.assertRaises(CalculationError):
                convert_data(amount, "B", "MB")

    def test_codec_roundtrips_unicode_and_whitespace(self):
        source = "Hello, λ 🌍\n  exact whitespace  "
        for encoder, decoder in (
            ("Text to Base64", "Base64 to text"),
            ("Text to hex", "Hex to text"),
            ("URL encode", "URL decode"),
        ):
            with self.subTest(encoder=encoder):
                self.assertEqual(transform_text(transform_text(source, encoder), decoder), source)
        self.assertEqual(transform_text("a+b", "URL decode"), "a+b")
        self.assertEqual(transform_text("", "Text to Base64"), "")

    def test_hash_and_invalid_encoding(self):
        self.assertEqual(transform_text("abc", "SHA-256"),
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        for source, mode in (("%%%", "Base64 to text"), ("gg", "Hex to text"), ("ff", "Hex to text")):
            with self.subTest(mode=mode), self.assertRaises(CalculationError):
                transform_text(source, mode)


class NetworkTests(unittest.TestCase):
    def test_ipv4_network_normalization(self):
        report = inspect_network("192.168.1.42/24")
        self.assertEqual(report["Network"], "192.168.1.0/24")
        self.assertEqual(report["Subnet mask"], "255.255.255.0")
        self.assertEqual(report["First host"], "192.168.1.1")
        self.assertEqual(report["Last host"], "192.168.1.254")
        self.assertEqual(report["Broadcast"], "192.168.1.255")
        self.assertEqual(report["Usable hosts"], "254")

    def test_point_to_point_and_single_host(self):
        self.assertEqual(inspect_network("10.0.0.0/31")["Usable hosts"], "2")
        self.assertEqual(inspect_network("10.0.0.1/32")["Usable hosts"], "1")
        self.assertEqual(inspect_network("2001:db8::/127")["Usable hosts"], "2")
        self.assertEqual(inspect_network("2001:db8::1/128")["First host"], "2001:db8::1")

    def test_ipv6_does_not_enumerate_large_networks(self):
        report = inspect_network("2001:db8::123/64")
        self.assertEqual(report["Network"], "2001:db8::/64")
        self.assertEqual(report["First host"], "2001:db8::1")
        self.assertEqual(report["Total addresses"], "18,446,744,073,709,551,616")
        self.assertNotIn("Broadcast", report)
        with self.assertRaises(CalculationError):
            inspect_network("invalid/99")


if __name__ == "__main__":
    unittest.main()

