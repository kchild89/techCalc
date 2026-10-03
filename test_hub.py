"""Regression tests for persistence, feed parsing, command references, and CS labs."""
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from calculator_core import CalculationError, evaluate
from hub_core import WorkspaceStore, complexity_estimate, evaluate_statement, float_details, sample_graph
from intel import (NewsCache, SOURCES, MAX_RESPONSE, filter_items, normalized_date, parse_kev,
                   parse_rss, plain_text, safe_url, fetch_source)
from tool_library import RECIPES, RECIPE_BY_ID, build_command, search_recipes

RSS = b"""<rss version="2.0"><channel>
<item><title>Vendor patches a zero-day CVE-2026-12345</title><link>https://example.com/advisory</link>
<description>&lt;p&gt;Update Windows &amp;amp; browsers.&lt;/p&gt;&lt;script&gt;ignored&lt;/script&gt;</description>
<pubDate>Fri, 02 Oct 2026 08:00:00 -0600</pubDate></item>
<item><title>Routine update</title><link>javascript:alert(1)</link></item>
<item><title>Undated research</title><link>https://example.com/research</link></item>
</channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Research note</title>
<link rel="self" href="https://example.com/feed"/><link rel="alternate" href="https://example.com/article"/>
<updated>2026-10-01T19:30:00Z</updated><summary>Study of a parser.</summary></entry></feed>"""
KEV = json.dumps({"catalogVersion": "2026.10.02", "vulnerabilities": [{
    "cveID": "CVE-2026-12345", "vendorProject": "Example", "product": "Browser",
    "vulnerabilityName": "Memory corruption", "dateAdded": "2026-10-02",
    "shortDescription": "A vulnerable parser is exploited.",
    "requiredAction": "Apply the vendor update.", "dueDate": "2026-10-23",
    "knownRansomwareCampaignUse": "Unknown",
    "notes": "Advisory: https://example.com/advisory; reference."
}]}).encode()


class WorkspaceTests(unittest.TestCase):
    def test_persistent_workspaces_do_not_mix_data(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(directory)
            store.workspace.update(notes="main notes", variables={"page_size": 4096}, ans=42)
            store.save()
            store.create("Lab")
            store.workspace["notes"] = "lab notes"
            store.save()
            restored = WorkspaceStore(directory)
            self.assertEqual(restored.state["active"], "Lab")
            self.assertEqual(restored.workspace["notes"], "lab notes")
            self.assertEqual(restored.state["workspaces"]["Main"]["variables"]["page_size"], 4096)

    def test_corrupt_state_is_preserved_for_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspaces.json"
            path.write_text("{broken", encoding="utf-8")
            store = WorkspaceStore(directory)
            self.assertTrue(store.warning)
            store.save()
            backups = list(Path(directory).glob("workspaces.recovery-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "{broken")
            self.assertEqual(json.loads(path.read_text())["version"], 2)

    def test_duplicate_workspace_and_invalid_name(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(directory)
            for name in ("", "Main", "x" * 65):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    store.create(name)

    def test_named_variable_assignment_and_reserved_names(self):
        variables = {"page_size": 4096}
        value, name = evaluate_statement("pages = page_size * 3", 0, variables)
        self.assertEqual((value, name), (12288, "pages"))
        self.assertNotIn("pages", variables)
        self.assertEqual(evaluate("page_size + ans", 10, variables), 4106)
        self.assertEqual(evaluate("pi", variables={"pi": 999}), math.pi)
        with self.assertRaises(CalculationError):
            evaluate_statement("sqrt = 12", 0, variables)

    def test_expression_error_location(self):
        with self.assertRaises(CalculationError) as caught:
            evaluate("4 + missing")
        self.assertEqual(caught.exception.position, 4)
        with self.assertRaises(CalculationError) as caught:
            evaluate_statement("answer = missing", 0, {})
        self.assertEqual(caught.exception.position, 9)


    def test_failed_workspace_creation_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkspaceStore(directory)
            with patch.object(store, "save", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    store.create("Lab")
            self.assertEqual(store.state["active"], "Main")
            self.assertNotIn("Lab", store.state["workspaces"])

    def test_leading_space_error_offset(self):
        with self.assertRaises(CalculationError) as caught:
            evaluate("   unknown")
        self.assertEqual(caught.exception.position, 3)


class NumericLabTests(unittest.TestCase):
    def test_float_negative_zero_and_normal(self):
        negative = float_details("-0.0", 64)
        self.assertEqual(negative["hex"], "0x8000000000000000")
        self.assertEqual(negative["classification"], "Signed zero")
        self.assertEqual(float_details("1", 32)["hex"], "0x3F800000")
        self.assertEqual(float_details("1", 64)["unbiased"], "0")

    def test_float_rounding_and_special_values(self):
        details = float_details("0.1 + 0.2")
        self.assertEqual(details["value"], "0.30000000000000004")
        self.assertGreater(len(details["exact"]), 20)
        self.assertEqual(float_details("1e-40", 32)["classification"], "Subnormal")
        self.assertEqual(float_details("nan")["classification"], "NaN")
        self.assertEqual(float_details("-inf")["classification"], "Infinity")
        with self.assertRaises(CalculationError):
            float_details("1e100", 32)

    def test_graph_domain_gaps_and_variables(self):
        points = sample_graph("1/x", -1, 1, samples=10)
        self.assertIsNone(points[5][1])
        self.assertEqual(sample_graph("factor*x", 0, 2, {"factor": 3}, samples=10)[-1], (2.0, 6.0))
        with self.assertRaises(CalculationError):
            sample_graph("missing(x)", -1, 1)
        with self.assertRaises(CalculationError):
            sample_graph("x", float("nan"), 1)

    def test_growth_models_and_bounded_huge_counts(self):
        self.assertEqual(complexity_estimate("log2(n)", 1, 1), ("0", "0 s"))
        self.assertEqual(complexity_estimate("n log2(n)", 1, 1), ("0", "0 s"))
        count, duration = complexity_estimate("n^2", 1000, 1)
        self.assertEqual(float(count.replace(",", "")), 1000000)
        self.assertEqual(duration, "1 ms")
        count, duration = complexity_estimate("n!", 100000, 1)
        self.assertIn("e+", count)
        self.assertIn("years", duration)
        for n, cost in ((0, 1), (100001, 1), (5, 0), (5, float("nan"))):
            with self.subTest(n=n, cost=cost), self.assertRaises(CalculationError):
                complexity_estimate("n", n, cost)


class IntelligenceTests(unittest.TestCase):
    def test_rss_metadata_and_zero_day_tag(self):
        items = parse_rss(RSS, SOURCES[1])
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["zero_day"])
        self.assertEqual(items[0]["cves"], ["CVE-2026-12345"])
        self.assertEqual(items[0]["published"], "2026-10-02T14:00:00+00:00")
        self.assertNotIn("ignored", items[0]["summary"])
        self.assertEqual(items[1]["published"], "")

    def test_atom_alternate_link(self):
        items = parse_rss(ATOM, SOURCES[3])
        self.assertEqual(items[0]["url"], "https://example.com/article")
        self.assertEqual(items[0]["published"], "2026-10-01T19:30:00+00:00")

    def test_kev_is_not_automatically_zero_day(self):
        item = parse_kev(KEV, SOURCES[0])[0]
        self.assertFalse(item["zero_day"])
        self.assertEqual(item["kind"], "kev")
        self.assertEqual(item["action"], "Apply the vendor update.")
        self.assertEqual(item["references"], ["https://example.com/advisory"])
        self.assertEqual(item["published"][:10], "2026-10-02")

    def test_rejects_unsafe_links_xml_and_oversized_data(self):
        for url in ("javascript:alert(1)", "file:///C:/secret", "https://user:pass@example.com", "https://example.com\nbad"):
            self.assertEqual(safe_url(url), "")
        for data in (b'<!DOCTYPE x [<!ENTITY y "test">]><rss/>', b"x" * (MAX_RESPONSE + 1), b"<rss><channel/></rss>"):
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                parse_rss(data, SOURCES[1])

    def test_plain_text_and_invalid_dates(self):
        self.assertEqual(plain_text("<b>Hello</b><script>bad()</script> world"), "Hello world")
        self.assertEqual(normalized_date("not a date"), "")
        self.assertEqual(normalized_date("2026-10-02"), "2026-10-02T00:00:00+00:00")

    def test_search_categories_and_watchlists(self):
        news = parse_rss(RSS, SOURCES[1])
        kev = parse_kev(KEV, SOURCES[0])
        items = news + kev
        self.assertEqual(len(filter_items(items, category="Zero-day reports")), 1)
        self.assertEqual(len(filter_items(items, category="Known exploited (CISA)")), 1)
        self.assertEqual(len(filter_items(items, category="Watchlist", watchlist=["browser"])), 2)
        self.assertEqual(len(filter_items(items, category="Watchlist", watchlist=[])), 0)
        self.assertEqual(len(filter_items(items, category="Bookmarked", bookmark_ids=[news[0]["id"]])), 1)
        self.assertEqual(len(filter_items(items, query="CVE-2026-12345")), 2)

    def test_cache_retains_last_success_when_refresh_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = NewsCache(Path(directory))
            items = parse_rss(RSS, SOURCES[1])
            cache.accept("bleeping", {"items": items, "fetched": "2026-10-02T14:00:00+00:00", "error": ""})
            cache.accept("bleeping", {"error": "offline", "attempted": "2026-10-03T14:00:00+00:00"})
            cache.save()
            restored = NewsCache(Path(directory))
            self.assertEqual(len(restored.items), 2)
            self.assertEqual(restored.sources["bleeping"]["fetched"], "2026-10-02T14:00:00+00:00")
            self.assertEqual(restored.sources["bleeping"]["error"], "offline")

    def test_official_kev_fallback(self):
        class Response:
            url = SOURCES[0]["fallback"]
            headers = {}
            def read(self, size):
                return KEV
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("intel.urllib.request.urlopen", side_effect=[OSError("unreachable"), Response()]) as request:
            result = fetch_source(SOURCES[0])
            self.assertEqual(request.call_count, 2)
            self.assertEqual(result["endpoint"], SOURCES[0]["fallback"])
            self.assertEqual(len(result["items"]), 1)


class CommandReferenceTests(unittest.TestCase):
    def test_every_recipe_builds_and_has_source(self):
        self.assertEqual(len({entry["id"] for entry in RECIPES}), len(RECIPES))
        for entry in RECIPES:
            with self.subTest(recipe=entry["id"]):
                self.assertTrue(build_command(entry))
                self.assertTrue(entry["docs"].startswith("https://"))
                self.assertNotIn("{host}", build_command(entry))
                self.assertNotIn("{ports}", build_command(entry))

    def test_parameter_validation_prevents_shell_fragments(self):
        entry = RECIPE_BY_ID["nmap-tcp"]
        for host in ("-sV", "127.0.0.1;whoami", "$(whoami)", "example.com other.com", "1.2.3.999", "https://example.com", "a..com"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                build_command(entry, host)
        for ports in ("0", "65536", "9-1", "80;whoami", "22,,80", ""):
            with self.subTest(ports=ports), self.assertRaises(ValueError):
                build_command(entry, "127.0.0.1", ports)
        self.assertIn("192.168.1.0/24", build_command(entry, "192.168.1.0/24"))
        with self.assertRaises(ValueError):
            build_command(RECIPE_BY_ID["curl-headers"], "192.168.1.0/24")

    def test_powershell_braces_survive_and_search_works(self):
        command = build_command(RECIPE_BY_ID["ps-events"])
        self.assertIn("@{LogName='System'; Level=2}", command)
        self.assertTrue(search_recipes("certificate", tool="Nmap"))
        self.assertEqual(len(search_recipes(favorites=["nmap-tcp"])), 1)


if __name__ == "__main__":
    unittest.main()

