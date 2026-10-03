"""Public RSS/Atom + CISA KEV ingestion, with bounded requests and honest cache state."""
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from hub_core import atomic_json, utc_now

SOURCES = (
    {"id": "cisa", "name": "CISA KEV", "kind": "kev",
     "url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
     "fallback": "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json",
     "home": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"},
    {"id": "bleeping", "name": "BleepingComputer", "kind": "rss",
     "url": "https://www.bleepingcomputer.com/feed/", "home": "https://www.bleepingcomputer.com/"},
    {"id": "thn", "name": "The Hacker News", "kind": "rss",
     "url": "https://feeds.feedburner.com/TheHackersNews", "home": "https://thehackernews.com/"},
    {"id": "talos", "name": "Cisco Talos", "kind": "rss",
     "url": "https://blog.talosintelligence.com/rss/", "home": "https://blog.talosintelligence.com/"},
)
SOURCE_BY_ID = {source["id"]: source for source in SOURCES}
MAX_RESPONSE = 8 * 1024 * 1024
ZERO_DAY = re.compile(r"\b(?:zero[\s\u2010-\u2015-]?day|0[\s-]?day)s?\b", re.I)
CVE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.I)


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "br", "div", "li"):
            self.chunks.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.chunks.append(data)


def plain_text(value, limit=1200):
    parser = PlainText()
    parser.feed(str(value)[:100000])
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", " ".join(parser.chunks))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def safe_url(value):
    if not isinstance(value, str) or len(value) > 4096 or re.search(r"[\x00-\x20]", value):
        return ""
    try:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            return ""
        return value
    except ValueError:
        return ""


def normalized_date(value):
    if not value:
        return ""
    try:
        date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return ""
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    try:
        return date.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, OverflowError):
        return ""


def parse_rss(data, source):
    if len(data) > MAX_RESPONSE:
        raise ValueError("Feed exceeds the 8 MB size limit.")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Feed contains unsupported XML declarations.")
    root = ET.fromstring(data)
    items = []
    entries = [node for node in root.iter() if node.tag.split("}")[-1] in ("item", "entry")]
    for node in entries[:150]:
        fields = {}
        link = ""
        for child in node:
            name = child.tag.split("}")[-1]
            fields.setdefault(name, "".join(child.itertext()))
            if name == "link":
                candidate = child.attrib.get("href") or child.text or ""
                if child.attrib.get("rel", "alternate") == "alternate":
                    link = safe_url(candidate.strip()) or link
        title = plain_text(fields.get("title", ""), 300)
        link = link or safe_url(fields.get("guid", "").strip())
        if not title or not link:
            continue
        summary = plain_text(fields.get("description") or fields.get("summary") or fields.get("content") or fields.get("encoded", ""), 500)
        published = normalized_date(fields.get("pubDate") or fields.get("published") or fields.get("date") or fields.get("updated", ""))
        items.append({
            "id": hashlib.sha256((source["id"] + link).encode()).hexdigest()[:24],
            "source_id": source["id"], "source": source["name"], "kind": "news",
            "title": title, "summary": summary, "url": link, "published": published,
            "zero_day": bool(ZERO_DAY.search(title)),
            "cves": sorted(set(match.upper() for match in CVE.findall(title + " " + summary))),
        })
    if not items:
        raise ValueError("No readable articles were returned.")
    return items


def parse_kev(data, source):
    raw = json.loads(data)
    if not isinstance(raw, dict) or not isinstance(raw.get("vulnerabilities"), list):
        raise ValueError("CISA returned an unexpected catalog format.")
    items = []
    for vulnerability in raw["vulnerabilities"]:
        if not isinstance(vulnerability, dict):
            continue
        cve = str(vulnerability.get("cveID", "")).upper()
        if not CVE.fullmatch(cve):
            continue
        title = cve + "  |  " + plain_text(vulnerability.get("vulnerabilityName", cve), 250)
        notes = plain_text(vulnerability.get("notes", ""), 1500)
        links = [safe_url(url.rstrip(".,;)")) for url in re.findall(r"https?://[^\s<>]+", notes)]
        items.append({
            "id": "kev-" + cve, "source_id": source["id"], "source": source["name"], "kind": "kev",
            "title": title, "summary": plain_text(vulnerability.get("shortDescription", ""), 1500),
            "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=" + cve,
            "published": normalized_date(vulnerability.get("dateAdded", "")),
            "zero_day": False, "cves": [cve],
            "vendor": plain_text(vulnerability.get("vendorProject", ""), 120),
            "product": plain_text(vulnerability.get("product", ""), 180),
            "action": plain_text(vulnerability.get("requiredAction", ""), 1500),
            "due": str(vulnerability.get("dueDate", "")),
            "ransomware": str(vulnerability.get("knownRansomwareCampaignUse", "Unknown")),
            "references": [url for url in links if url][:8],
            "catalog_version": str(raw.get("catalogVersion", "")),
        })
    if not items:
        raise ValueError("The CISA catalog contained no valid entries.")
    return sorted(items, key=lambda item: item["published"], reverse=True)


def fetch_source(source):
    errors = []
    for url in (source["url"], source.get("fallback")):
        if not url:
            continue
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "NeonCyberHub/2.0 (desktop feed reader)",
                              "Accept": "application/json, application/rss+xml, application/atom+xml, text/xml"})
            with urllib.request.urlopen(request, timeout=15) as response:
                if urllib.parse.urlsplit(response.url).scheme != "https":
                    raise ValueError("Source redirected away from HTTPS.")
                if int(response.headers.get("Content-Length") or 0) > MAX_RESPONSE:
                    raise ValueError("Source exceeds the 8 MB limit.")
                data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise ValueError("Source exceeds the 8 MB limit.")
            items = parse_kev(data, source) if source["kind"] == "kev" else parse_rss(data, source)
            return {"items": items, "fetched": utc_now(), "error": "", "endpoint": url}
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {str(exc)[:160]}")
    raise ValueError(" / ".join(errors))


class NewsCache:
    def __init__(self, directory):
        self.path = directory / "news-cache.json"
        self.sources = {}
        self.warning = ""
        try:
            if self.path.exists():
                if self.path.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError("News cache exceeds its size limit.")
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                for source_id, result in raw.get("sources", {}).items():
                    if source_id not in SOURCE_BY_ID or not isinstance(result, dict):
                        continue
                    items = [item for item in result.get("items", []) if isinstance(item, dict)
                             and isinstance(item.get("title"), str) and isinstance(item.get("id"), str)
                             and safe_url(item.get("url", ""))]
                    self.sources[source_id] = dict(result, items=items[:5000])
        except (ValueError, OSError, TypeError, AttributeError) as exc:
            self.warning = "News cache unavailable: " + str(exc)

    @property
    def items(self):
        unique = {item["id"]: item for result in self.sources.values() for item in result.get("items", [])}
        return sorted(unique.values(), key=lambda item: item.get("published", ""), reverse=True)

    def refresh(self, deliver, cancelled=None):
        """Run off the UI thread; deliver immutable results through a queue."""
        def worker(source):
            try:
                result = fetch_source(source)
            except Exception as exc:
                result = {"error": str(exc), "attempted": utc_now()}
            if not cancelled or not cancelled.is_set():
                deliver(source["id"], result)
        workers = [threading.Thread(target=worker, args=(source,), daemon=True) for source in SOURCES]
        for worker_thread in workers:
            worker_thread.start()
        while any(worker_thread.is_alive() for worker_thread in workers):
            if cancelled and cancelled.is_set():
                return
            for worker_thread in workers:
                worker_thread.join(timeout=0.1)

    def accept(self, source_id, result):
        previous = self.sources.get(source_id, {})
        if "items" in result:
            self.sources[source_id] = result
        else:
            self.sources[source_id] = dict(previous, error=result["error"], attempted=result.get("attempted", utc_now()))

    def save(self):
        atomic_json(self.path, {"version": 1, "sources": self.sources})

    def should_refresh(self, seconds=1800):
        now = time.time()
        for source in SOURCES:
            record = self.sources.get(source["id"], {})
            try:
                timestamp = datetime.fromisoformat(record.get("fetched", "")).timestamp()
            except (ValueError, TypeError):
                return True
            if now - timestamp > seconds or record.get("error"):
                return True
        return False


def filter_items(items, query="", category="All intelligence", source="All sources",
                 watchlist=(), bookmark_ids=()):
    terms = query.lower().split()
    watched = [term.lower().strip() for term in watchlist if term.strip()]
    bookmarks = set(bookmark_ids)
    result = []
    for item in items:
        searchable = " ".join(str(item.get(key, "")) for key in ("title", "summary", "vendor", "product", "source")).lower()
        if any(term not in searchable for term in terms):
            continue
        if source != "All sources" and item.get("source") != source:
            continue
        if category == "Zero-day reports" and not item.get("zero_day"):
            continue
        if category == "Known exploited (CISA)" and item.get("kind") != "kev":
            continue
        if category == "News & research" and item.get("kind") != "news":
            continue
        if category == "Watchlist" and not any(term in searchable for term in watched):
            continue
        if category == "Bookmarked" and item.get("id") not in bookmarks:
            continue
        result.append(item)
    return result

