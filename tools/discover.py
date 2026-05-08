#!/usr/bin/env python3
"""
discover.py — Automated discovery for Synthetic-Marketer audits.

Fetches a target site, runs a structured checklist of marketing/SEO/technical
checks, validates JSON-LD schema for common defects, and emits a structured
_DIGEST.md plus a raw HTML cache. Designed to replace the manual discovery
phase of the audit pipeline so subagents start with the same facts every time.

Usage:
    python3 tools/discover.py <url> <project_bin_folder>
    python3 tools/discover.py https://example.com Synth-mkt_Example_20260507

Outputs (inside the project bin):
    raw/                       cached HTML for every fetched page
    _DIGEST.md                 structured discovery digest (facts, no narrative)
    _DISCOVERY-NOTES.md        explicit checklist with pass/fail markers
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Common slugs to probe for 404s (informs "missing pages" findings)
PROBE_SLUGS = [
    "blog", "resources", "pricing", "about", "contact", "team", "leadership",
    "testimonials", "case-studies", "faq", "privacy", "terms", "careers",
    "press", "events", "calendar", "store", "shop", "products", "services",
    "members", "membership", "private-events", "book", "reviews",
]

# AI crawlers worth flagging in robots.txt
AI_CRAWLERS = {
    "GPTBot", "ClaudeBot", "anthropic-ai", "PerplexityBot", "Google-Extended",
    "Applebot-Extended", "CCBot", "Bytespider", "Meta-ExternalAgent",
    "OAI-SearchBot", "Amazonbot", "AI2Bot", "Ai2Bot-Dolma", "cohere-ai",
    "DuckAssistBot", "FacebookBot", "GoogleOther", "MyCentralAIScraperBot",
    "Quora-Bot", "TikTokSpider", "YouBot", "img2dataset",
}

# AdsBot variants whose blocking damages Google Ads quality score
ADSBOT_CRAWLERS = {
    "AdsBot-Google", "AdsBot-Google-Mobile", "AdsBot-Google-Mobile-Apps",
}

# Known social/external platforms worth identifying
SOCIAL_HOSTS = [
    ("instagram.com", "Instagram"),
    ("facebook.com", "Facebook"),
    ("twitter.com", "Twitter/X"),
    ("x.com", "Twitter/X"),
    ("threads.net", "Threads"),
    ("linkedin.com", "LinkedIn"),
    ("youtube.com", "YouTube"),
    ("youtu.be", "YouTube"),
    ("tiktok.com", "TikTok"),
    ("discord.gg", "Discord"),
    ("discord.com", "Discord"),
    ("reddit.com", "Reddit"),
    ("pinterest.com", "Pinterest"),
    ("snapchat.com", "Snapchat"),
    ("vimeo.com", "Vimeo"),
    ("twitch.tv", "Twitch"),
    ("medium.com", "Medium"),
    ("substack.com", "Substack"),
    ("github.com", "GitHub"),
    ("square.site", "Square Online Store"),
    ("squareup.com", "Square"),
    ("shopify.com", "Shopify"),
    ("etsy.com", "Etsy"),
    ("eventbrite.com", "Eventbrite"),
    ("calendly.com", "Calendly"),
    ("tcgplayer.com", "TCGplayer"),
    ("tcgplayerpro.com", "TCGplayer Pro"),
    ("amazon.com", "Amazon"),
    ("yelp.com", "Yelp"),
    ("trustpilot.com", "Trustpilot"),
    ("g2.com", "G2"),
    ("bbb.org", "BBB"),
]

# CMS/platform fingerprints
PLATFORM_SIGNATURES = [
    (r"static\.squarespace\.com|squarespace-cdn\.com|/squarespace_external_api", "Squarespace"),
    (r"wp-content/|wp-includes/|/wp-json/", "WordPress"),
    (r"cdn\.shopify\.com|/shopify-pay-button|shopify\.theme", "Shopify"),
    (r"webflow\.com|/webflow\.[a-z0-9]+\.css", "Webflow"),
    (r"_next/static|__NEXT_DATA__", "Next.js"),
    (r"wix-static\.com|/_partials/", "Wix"),
    (r"hubspot\.net|/hs-fs/|/_hcms/", "HubSpot CMS"),
    (r"ghost\.org|/ghost/api/", "Ghost"),
    (r"drupal\.org|drupal-settings", "Drupal"),
    (r"joomla\.org|/templates/system/", "Joomla"),
]

# Schema sub-types worth flagging (generic LocalBusiness should usually be specialized)
GENERIC_LOCALBUSINESS_TYPES = {"LocalBusiness", "Organization"}

# ----------------------------------------------------------------------------
# Fetching
# ----------------------------------------------------------------------------

def fetch(url: str, out_path: Path | None = None, timeout: int = 30) -> tuple[int, str]:
    """Fetch a URL with curl + browser UA. Save HTML to out_path if given. Return (status, body)."""
    cmd = [
        "curl", "-sSL", "-A", USER_AGENT,
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.5",
        "--max-time", str(timeout),
        "-o", str(out_path) if out_path else "-",
        "-w", "%{http_code}",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return 0, ""
    code_str = result.stdout.strip().split()[-1] if result.stdout else "0"
    try:
        code = int(code_str)
    except ValueError:
        code = 0
    if out_path and out_path.exists():
        body = out_path.read_text(encoding="utf-8", errors="replace")
    else:
        body = result.stdout if not out_path else ""
    return code, body


# ----------------------------------------------------------------------------
# HTML parsing
# ----------------------------------------------------------------------------

class PageParser(HTMLParser):
    """One-pass HTML extraction: text, links, headings, images, meta, JSON-LD."""

    def __init__(self):
        super().__init__()
        self.skip_depth = 0  # script/style/svg/noscript depth
        self.text_buf: list[str] = []
        self.links: list[str] = []
        self.images_total = 0
        self.images_with_alt = 0
        self.images_alt_nonempty = 0
        self.headings: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
        self._heading_stack: list[str] = []
        self._heading_buf: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._title_buf: list[str] = []
        self.meta_description: str | None = None
        self.meta_robots: str | None = None
        self.meta_viewport: str | None = None
        self.meta_generator: str | None = None
        self.meta_og_title: str | None = None
        self.meta_og_description: str | None = None
        self.meta_og_type: str | None = None
        self.meta_twitter_card: str | None = None
        self.canonical: str | None = None
        self.jsonld_blocks: list[str] = []
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self.forms: list[dict] = []
        self._in_form = False
        self._cur_form: dict | None = None
        self._in_textarea = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            if tag == "script" and a.get("type") == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []
            else:
                self.skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            content = a.get("content") or ""
            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.meta_robots = content
            elif name == "viewport":
                self.meta_viewport = content
            elif name == "generator":
                self.meta_generator = content
            elif name == "twitter:card":
                self.meta_twitter_card = content
            elif prop == "og:title":
                self.meta_og_title = content
            elif prop == "og:description":
                self.meta_og_description = content
            elif prop == "og:type":
                self.meta_og_type = content
            return
        if tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href")
            return
        if tag == "a":
            href = a.get("href")
            if href:
                self.links.append(href)
            return
        if tag == "img":
            self.images_total += 1
            alt = a.get("alt")
            if alt is not None:
                self.images_with_alt += 1
                if alt.strip():
                    self.images_alt_nonempty += 1
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_stack.append(tag)
            self._heading_buf = []
            return
        if tag == "form":
            self._in_form = True
            self._cur_form = {
                "action": a.get("action", ""),
                "method": (a.get("method") or "get").upper(),
                "fields": [],
            }
            return
        if tag in ("input", "select", "textarea") and self._cur_form is not None:
            field = {
                "tag": tag,
                "name": a.get("name", ""),
                "type": (a.get("type") or "").lower() if tag == "input" else tag,
                "required": "required" in a,
                "placeholder": a.get("placeholder", ""),
            }
            self._cur_form["fields"].append(field)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            if tag == "script" and self._in_jsonld:
                self.jsonld_blocks.append("".join(self._jsonld_buf))
                self._in_jsonld = False
                self._jsonld_buf = []
            else:
                self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag == "title":
            self.title = "".join(self._title_buf).strip()
            self._title_buf = []
            self._in_title = False
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = " ".join(self._heading_buf).strip()
            if self._heading_stack and self._heading_stack[-1] == tag:
                self._heading_stack.pop()
            self.headings[tag].append(text)
            self._heading_buf = []
            return
        if tag == "form":
            if self._cur_form is not None:
                self.forms.append(self._cur_form)
            self._in_form = False
            self._cur_form = None

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        if self.skip_depth:
            return
        if self._in_title:
            self._title_buf.append(data)
            return
        if self._heading_stack:
            self._heading_buf.append(data)
        self.text_buf.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text_buf)).strip()


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------

def parse_html(html: str) -> PageParser:
    p = PageParser()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


def parse_jsonld_blocks(blocks: list[str]) -> list:
    """Best-effort parse JSON-LD blocks. Return list of parsed objects (each may be dict or list)."""
    parsed = []
    for raw in blocks:
        try:
            obj = json.loads(raw)
            parsed.append(obj)
        except json.JSONDecodeError:
            continue
    return parsed


def flatten_jsonld(parsed_blocks: list) -> list[dict]:
    """Flatten JSON-LD into a list of node dicts (handles @graph and arrays)."""
    nodes: list[dict] = []
    def visit(obj):
        if isinstance(obj, list):
            for item in obj:
                visit(item)
        elif isinstance(obj, dict):
            graph = obj.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    visit(item)
                # also keep the wrapper if it has its own @type
                if "@type" in obj:
                    nodes.append(obj)
            else:
                nodes.append(obj)
    for block in parsed_blocks:
        visit(block)
    return nodes


def detect_platform(html: str) -> str | None:
    for pattern, name in PLATFORM_SIGNATURES:
        if re.search(pattern, html, re.IGNORECASE):
            return name
    return None


def parse_robots_txt(text: str) -> dict:
    """Parse robots.txt. Return {'global_rules': {...}, 'agents': {agent: {'disallow': [...], 'allow': [...]}}}."""
    agents: dict = {}
    cur_agents: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            cur_agents = []
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            cur_agents.append(value)
            agents.setdefault(value, {"allow": [], "disallow": []})
        elif key == "disallow" and cur_agents:
            for ua in cur_agents:
                agents.setdefault(ua, {"allow": [], "disallow": []})
                agents[ua]["disallow"].append(value)
        elif key == "allow" and cur_agents:
            for ua in cur_agents:
                agents.setdefault(ua, {"allow": [], "disallow": []})
                agents[ua]["allow"].append(value)
    return agents


def is_blocked(robots: dict, agent: str) -> bool:
    """Heuristic: an agent is blocked if it appears with a Disallow rule (any rule, including empty)."""
    rules = robots.get(agent)
    if not rules:
        return False
    return any(d.strip() in ("/", "*") or d.strip() == "" or d.strip().startswith("/") for d in rules.get("disallow", []))


def parse_sitemap(text: str) -> list[str]:
    """Best-effort sitemap.xml parse. Returns a list of <loc> URLs."""
    return re.findall(r"<loc>([^<]+)</loc>", text)


def absolutize(url: str, base: str) -> str:
    return urllib.parse.urljoin(base, url)


def normalize_internal(url: str, base_host: str) -> str | None:
    """Return path-only string for internal link, or None for external/anchor/mailto/tel."""
    if not url:
        return None
    if url.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc and parsed.netloc not in (base_host, f"www.{base_host}", base_host.removeprefix("www.")):
        return None
    path = parsed.path or "/"
    return path


def find_phones(text: str) -> list[str]:
    """Find US-style phone numbers."""
    matches = re.findall(r"\(?\b\d{3}\)?[\s\-\.]+\d{3}[\s\-\.]+\d{4}\b", text)
    return list(dict.fromkeys(matches))[:8]


def find_emails(text: str) -> list[str]:
    matches = re.findall(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", text)
    return list(dict.fromkeys(m for m in matches if not m.endswith(".png") and not m.endswith(".jpg")))[:8]


def classify_socials(links: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for link in links:
        for host, name in SOCIAL_HOSTS:
            if host in link:
                out.setdefault(name, [])
                if link not in out[name]:
                    out[name].append(link)
                break
    return out


# ----------------------------------------------------------------------------
# Schema validation
# ----------------------------------------------------------------------------

def schema_defects(nodes: list[dict], displayed_brand: str | None = None) -> list[str]:
    """Detect known-bad schema patterns. Returns list of human-readable defect strings."""
    defects: list[str] = []
    for n in nodes:
        ntype = n.get("@type")
        types = ntype if isinstance(ntype, list) else ([ntype] if ntype else [])
        # 1. Wrong NAME field (looks like a street address)
        name = n.get("name") or n.get("legalName")
        if isinstance(name, str) and re.match(r"^\s*\d+\s+\w+", name) and (
            "St" in name or "Ave" in name or "Rd" in name or "Dr" in name or "Ln" in name
            or "Suite" in name or "#" in name or "Blvd" in name or "Ct" in name
        ):
            defects.append(f"{'/'.join(types) or 'node'} has NAME that looks like a street address: '{name}'")
        # 2. Generic LocalBusiness without subtype
        if any(t == "LocalBusiness" for t in types) and not any(
            t not in GENERIC_LOCALBUSINESS_TYPES for t in types
        ):
            defects.append("LocalBusiness uses generic type — consider specialized subtype (Store, HobbyShop, FinancialService, Restaurant, etc.)")
        # 3. Malformed openingHours (string of commas, empty, or missing)
        oh = n.get("openingHours")
        if oh is not None:
            if isinstance(oh, str) and re.fullmatch(r"[\s,]*", oh):
                defects.append(f"openingHours is malformed empty/comma string: '{oh}'")
            elif isinstance(oh, list) and not any(s.strip() for s in oh if isinstance(s, str)):
                defects.append("openingHours array contains only empty strings")
        # 4. Address: city only, no streetAddress
        addr = n.get("address")
        if isinstance(addr, dict) and not addr.get("streetAddress"):
            if addr.get("addressLocality") or addr.get("addressRegion"):
                defects.append("PostalAddress has city/region but no streetAddress")
        # 5. Organization missing sameAs
        if any(t in ("Organization", "Corporation") for t in types) and not n.get("sameAs"):
            defects.append("Organization schema missing 'sameAs' (no social profile cross-references)")
        # 6. Brand-name mismatch (only checked if caller passed displayed_brand)
        if displayed_brand and isinstance(name, str):
            if displayed_brand.lower() not in name.lower() and not any(re.match(r"^\s*\d+", name) for _ in [0]):
                # don't double-flag the address-as-name case
                pass
    return defects


def select_psi_pages(pages: list[dict], max_pages: int) -> list[str]:
    """Pick the most-conversion-relevant URLs for PSI testing."""
    candidates = [p for p in pages if p.get("status") == 200]
    # Always include homepage if present
    homepage = None
    rest = []
    for p in candidates:
        path = urllib.parse.urlparse(p["url"]).path
        if path in ("", "/"):
            homepage = p["url"]
        else:
            rest.append(p)
    # Score remaining by hint match + shorter path (more important)
    def score(p: dict) -> int:
        path = urllib.parse.urlparse(p["url"]).path.lower()
        s = 0
        for hint in KEY_PAGE_HINTS:
            if hint != "/" and hint in path:
                s += 10
        s += max(0, 20 - len(path))
        return -s
    rest.sort(key=score)
    selected = []
    if homepage:
        selected.append(homepage)
    for p in rest:
        if len(selected) >= max_pages:
            break
        selected.append(p["url"])
    return selected


def run_psi(url: str, strategy: str = "mobile", retries: int = 2) -> dict | None:
    """Call PageSpeed Insights API and return a flattened metric dict, or None on failure.

    Retries automatically on 429 (rate limit) with exponential backoff.
    If PAGESPEED_API_KEY env var is set, it's used to lift rate limits significantly
    (free Google API key, 25K queries/day).
    """
    import json as _json
    import time as _time
    import urllib.request
    import urllib.error
    qs = {"url": url, "strategy": strategy, "category": "performance"}
    api_key = os.environ.get("PAGESPEED_API_KEY")
    if api_key:
        qs["key"] = api_key
    params = urllib.parse.urlencode(qs, doseq=True)
    extra = "&category=accessibility&category=best-practices&category=seo"
    full_url = f"{PSI_API}?{params}{extra}"
    data = None
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(full_url, timeout=PSI_TIMEOUT) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt < retries:
                wait = 5 * (attempt + 1)
                print(f"[discover]   PSI 429 — backing off {wait}s")
                _time.sleep(wait)
                continue
            return {"error": f"HTTP {e.code}: {e.reason}"[:200]}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            return {"error": str(e)[:200]}
    if data is None:
        return {"error": str(last_err)[:200] if last_err else "unknown PSI failure"}
    out: dict = {"strategy": strategy}
    lh = data.get("lighthouseResult", {})
    cats = lh.get("categories", {})
    for key, label in [("performance", "performance"), ("accessibility", "accessibility"),
                       ("best-practices", "best_practices"), ("seo", "seo")]:
        score = cats.get(key, {}).get("score")
        out[label] = round(score * 100) if isinstance(score, (int, float)) else None
    audits = lh.get("audits", {})
    def metric(audit_id: str) -> float | None:
        a = audits.get(audit_id, {})
        return a.get("numericValue")
    out["lcp_ms"] = metric("largest-contentful-paint")
    out["cls"] = metric("cumulative-layout-shift")
    out["fcp_ms"] = metric("first-contentful-paint")
    out["si_ms"] = metric("speed-index")
    out["tbt_ms"] = metric("total-blocking-time")
    out["tti_ms"] = metric("interactive")
    # CrUX field data (real-world)
    field = data.get("loadingExperience", {}).get("metrics", {})
    def field_p75(key: str) -> int | None:
        v = field.get(key, {}).get("percentile")
        return v if isinstance(v, (int, float)) else None
    out["field_lcp_p75_ms"] = field_p75("LARGEST_CONTENTFUL_PAINT_MS")
    out["field_cls_p75"] = field_p75("CUMULATIVE_LAYOUT_SHIFT_SCORE")
    out["field_inp_p75_ms"] = field_p75("INTERACTION_TO_NEXT_PAINT")
    out["field_overall"] = data.get("loadingExperience", {}).get("overall_category")
    return out


def expected_schemas_for_business_type(text_corpus: str) -> list[tuple[str, str]]:
    """Heuristic-suggest schema types based on signals in body text."""
    out = []
    lower = text_corpus.lower()
    if any(k in lower for k in ("event", "tournament", "workshop", "class", "register")):
        out.append(("Event", "Pages mention events/tournaments/workshops"))
    if any(k in lower for k in ("price", "$", "buy now", "add to cart", "shop")):
        out.append(("Product / OfferCatalog", "Commerce signals detected"))
    if any(k in lower for k in ("frequently asked", "faq", "questions and answers")):
        out.append(("FAQPage", "FAQ content present"))
    if any(k in lower for k in ("review", "testimonial", "rating", "star")):
        out.append(("Review / AggregateRating", "Reviews/testimonials referenced"))
    if any(k in lower for k in ("address", "directions", "open mon", "open tue", "hours", "near me")):
        out.append(("LocalBusiness + PostalAddress + OpeningHoursSpecification", "Local-business signals present"))
    if any(k in lower for k in ("our team", "meet the", "founder", "ceo", "instructor", "host")):
        out.append(("Person", "Team / leadership references found"))
    return out


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------

def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_") or "page"


def write_digest(bin_dir: Path, data: dict) -> None:
    """Render the structured discovery digest to _DIGEST.md in the project bin."""
    out = bin_dir / "_DIGEST.md"
    L = []  # lines

    def H(level, text):
        L.append("#" * level + " " + text)
        L.append("")

    def P(text=""):
        L.append(text)

    H(1, f"Discovery Digest — {data['brand_name']}")
    P(f"**URL:** {data['url']}")
    P(f"**Date fetched:** {data['date']}")
    if data.get("platform"):
        P(f"**Platform:** {data['platform']}")
    P(f"**Discovery script version:** {SCRIPT_VERSION}")
    P()
    P("> This digest is auto-generated by `tools/discover.py` and contains only **facts** from the discovery scan. Analytical interpretation belongs in the audit subagents and the MARKETING-AUDIT.md narrative.")
    P()

    # Site map
    H(2, "Site map")
    P(f"**Total pages fetched:** {len(data['pages'])}")
    P(f"**Sitemap URLs found:** {len(data.get('sitemap_urls', []))}")
    P()
    P("| URL | Status | Title | Bytes |")
    P("|---|---|---|---|")
    for p in data["pages"]:
        title = (p.get("title") or "").replace("|", "\\|")[:80]
        L.append(f"| `{p['url']}` | {p['status']} | {title} | {p['bytes']} |")
    P()

    # Probed slugs that 404'd
    if data.get("probe_404s"):
        H(3, "Probed common slugs returning 404 (potential missing pages)")
        for slug in data["probe_404s"]:
            P(f"- `{slug}`")
        P()

    # Headings audit
    H(2, "Headings audit")
    P("| URL | H1 count | H1 text | H2 count | Headings issue |")
    P("|---|---|---|---|---|")
    for p in data["pages"]:
        if p["status"] != 200:
            continue
        h1s = p.get("h1", [])
        h1_text = " | ".join(h1s)[:80] if h1s else "_(none)_"
        flags = []
        if len(h1s) == 0:
            flags.append("no H1")
        elif len(h1s) > 1:
            flags.append(f"{len(h1s)} H1s")
        elif not h1s[0].strip():
            flags.append("empty H1 tag")
        h2s = p.get("h2", [])
        if not h2s and not h1s:
            flags.append("no headings at all")
        flag_str = ", ".join(flags) or "ok"
        L.append(f"| `{p['url']}` | {len(h1s)} | {h1_text} | {len(h2s)} | {flag_str} |")
    P()

    # Meta descriptions audit
    H(2, "Meta descriptions audit")
    desc_seen: dict[str, list[str]] = {}
    for p in data["pages"]:
        if p["status"] != 200:
            continue
        d = (p.get("meta_description") or "").strip()
        desc_seen.setdefault(d, []).append(p["url"])
    P("| URL | Meta description | Length |")
    P("|---|---|---|")
    for p in data["pages"]:
        if p["status"] != 200:
            continue
        d = (p.get("meta_description") or "").replace("|", "\\|")
        L.append(f"| `{p['url']}` | {d[:120] or '_(none)_'} | {len(d)} |")
    P()
    duplicates = {k: v for k, v in desc_seen.items() if k and len(v) > 1}
    if duplicates:
        P("**Duplicate meta descriptions detected:**")
        for desc, urls in duplicates.items():
            P(f"- `{desc[:100]}` appears on: {', '.join('`'+u+'`' for u in urls)}")
        P()

    # Schema audit
    H(2, "JSON-LD schema audit")
    P(f"**Schema types found across all pages:** {', '.join(sorted(data.get('schema_types', set()))) or '_(none)_'}")
    P()
    if data.get("schema_defects"):
        P("**Defects detected:**")
        for d in data["schema_defects"]:
            P(f"- {d}")
        P()
    else:
        P("_No common defects detected._")
        P()
    if data.get("expected_schemas"):
        P("**Schema types likely needed but not found** (heuristic):")
        for stype, reason in data["expected_schemas"]:
            if stype not in data.get("schema_types", set()):
                P(f"- **{stype}** — {reason}")
        P()

    # Robots.txt
    H(2, "robots.txt audit")
    if data.get("robots_text"):
        if data.get("ai_bots_blocked"):
            P(f"**AI crawlers blocked:** {', '.join(sorted(data['ai_bots_blocked']))}")
        else:
            P("**AI crawlers blocked:** _(none detected)_")
        if data.get("adsbot_blocked"):
            P(f"**AdsBot variants blocked (Google Ads quality-score risk):** {', '.join(sorted(data['adsbot_blocked']))}")
        else:
            P("**AdsBot blocking:** _(none detected)_")
    else:
        P("_robots.txt not retrievable_")
    P()

    # NAP
    H(2, "NAP (Name / Address / Phone) consistency")
    P(f"**Phone numbers found:** {', '.join(data.get('phones', [])) or '_(none)_'}")
    P(f"**Email addresses found:** {', '.join(data.get('emails', [])) or '_(none)_'}")
    if data.get("schema_addresses"):
        P("**Addresses in schema:**")
        for a in data["schema_addresses"]:
            P(f"- {a}")
    P()

    # Forms / CTAs
    H(2, "Forms and CTA inventory")
    forms_total = sum(len(p.get("forms", [])) for p in data["pages"] if p["status"] == 200)
    P(f"**Total forms across site:** {forms_total}")
    P()
    for p in data["pages"]:
        if p["status"] != 200 or not p.get("forms"):
            continue
        P(f"**`{p['url']}`** — {len(p['forms'])} form(s):")
        for f in p["forms"]:
            field_summary = ", ".join(
                f"{fld['name'] or fld['tag']}({fld['type']})"
                for fld in f.get("fields", [])
                if fld.get("type") not in ("hidden", "submit", "")
            )
            P(f"  - action=`{f.get('action') or '(self)'}` method={f.get('method')} fields: {field_summary or '(none parsed)'}")
        P()

    # External / social links
    H(2, "External and social links")
    if data.get("socials"):
        for platform, links in sorted(data["socials"].items()):
            P(f"- **{platform}:** {', '.join(links[:3])}{(' …' if len(links) > 3 else '')}")
    else:
        P("_(none detected)_")
    P()

    # Image alt coverage
    H(2, "Image alt-text coverage")
    P("| URL | Total images | With alt | Non-empty alt | Coverage |")
    P("|---|---|---|---|---|")
    for p in data["pages"]:
        if p["status"] != 200:
            continue
        total = p.get("images_total", 0)
        with_alt = p.get("images_with_alt", 0)
        nonempty = p.get("images_alt_nonempty", 0)
        coverage = f"{(nonempty/total*100):.0f}%" if total else "n/a"
        L.append(f"| `{p['url']}` | {total} | {with_alt} | {nonempty} | {coverage} |")
    P()

    # PageSpeed Insights (lab + field metrics)
    if data.get("psi_results"):
        H(2, "PageSpeed Insights (mobile)")
        P("_Lab metrics from a single Lighthouse run via the PSI API. Field metrics (CrUX p75) are real-world from Chrome users when available._")
        P()
        P("| URL | Perf | A11y | BP | SEO | LCP (lab) | CLS (lab) | TBT (lab) | LCP p75 (field) | INP p75 (field) | CLS p75 (field) | Overall (CrUX) |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in data["psi_results"]:
            if "error" in r:
                L.append(f"| `{r['url']}` | error: {r['error'][:50]} | | | | | | | | | | |")
                continue
            def fmt_ms(v):
                return f"{v/1000:.1f}s" if isinstance(v, (int, float)) else "—"
            def fmt_num(v, prec=2):
                if isinstance(v, (int, float)):
                    return f"{v:.{prec}f}" if prec else f"{int(v)}"
                return "—"
            def fmt_pct(v):
                return f"{v}" if v is not None else "—"
            row = (
                f"| `{r['url']}` "
                f"| {fmt_pct(r.get('performance'))} "
                f"| {fmt_pct(r.get('accessibility'))} "
                f"| {fmt_pct(r.get('best_practices'))} "
                f"| {fmt_pct(r.get('seo'))} "
                f"| {fmt_ms(r.get('lcp_ms'))} "
                f"| {fmt_num(r.get('cls'), 3)} "
                f"| {fmt_ms(r.get('tbt_ms'))} "
                f"| {fmt_ms(r.get('field_lcp_p75_ms'))} "
                f"| {fmt_num(r.get('field_inp_p75_ms'), 0)}ms "
                f"| {fmt_num(r.get('field_cls_p75'), 3)} "
                f"| {r.get('field_overall') or '—'} |"
            )
            L.append(row)
        P()
        P("**Core Web Vitals thresholds (Google):** LCP good < 2.5s, CLS good < 0.1, INP good < 200ms.")
        P()

    # Cached HTML files
    H(2, "Available files for subagents")
    P("Raw HTML cached at:")
    for p in data["pages"]:
        if p.get("cache_path"):
            P(f"- `{p['cache_path']}`")
    P()

    out.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_checklist(bin_dir: Path, data: dict) -> None:
    """Render the explicit checklist with pass/fail markers."""
    out = bin_dir / "_DISCOVERY-NOTES.md"
    L = []

    def check(passed: bool, label: str) -> str:
        return f"- {'✅' if passed else '❌'} {label}"

    pages = [p for p in data["pages"] if p["status"] == 200]
    home = next((p for p in pages if p["url"].rstrip("/") == data["url"].rstrip("/")), pages[0] if pages else None)

    L.append(f"# Discovery Checklist — {data['brand_name']}")
    L.append("")
    L.append(f"_Auto-generated by `tools/discover.py` v{SCRIPT_VERSION} on {data['date']}._")
    L.append("")
    L.append("## Pre-fetch")
    L.append(check(home is not None, "Homepage reachable (HTTP 200)"))
    L.append(check(bool(data.get("sitemap_urls")), f"Sitemap found ({len(data.get('sitemap_urls', []))} URLs)"))
    L.append(check(bool(data.get("robots_text")), "robots.txt retrieved"))
    L.append(check(bool(data.get("platform")), f"Platform detected: {data.get('platform') or 'unknown'}"))
    L.append("")
    L.append("## Headings hygiene")
    if home:
        L.append(check(len(home.get("h1", [])) == 1, f"Homepage has exactly one H1 (found {len(home.get('h1', []))})"))
        L.append(check(all(h.strip() for h in home.get("h1", [])), "Homepage H1 tag(s) contain text (no empty H1)"))
    multi_h1_pages = [p["url"] for p in pages if len(p.get("h1", [])) > 1]
    L.append(check(not multi_h1_pages, f"No pages with multiple H1s ({len(multi_h1_pages)} found)" if multi_h1_pages else "No pages with multiple H1s"))
    no_heading_pages = [p["url"] for p in pages if not any(p.get(f"h{i}", []) for i in range(1, 4))]
    L.append(check(not no_heading_pages, f"All pages have at least one heading ({len(no_heading_pages)} pages with no H1/H2/H3)"))
    if no_heading_pages:
        for url in no_heading_pages[:5]:
            L.append(f"  - `{url}`")
    L.append("")
    L.append("## Meta descriptions")
    desc_map: dict[str, list[str]] = {}
    for p in pages:
        d = (p.get("meta_description") or "").strip()
        if d:
            desc_map.setdefault(d, []).append(p["url"])
    duplicates = {k: v for k, v in desc_map.items() if len(v) > 1}
    L.append(check(all(p.get("meta_description") for p in pages), f"All pages have meta descriptions ({sum(1 for p in pages if not p.get('meta_description'))} missing)"))
    L.append(check(not duplicates, f"All meta descriptions unique ({len(duplicates)} duplicate strings detected)"))
    L.append("")
    L.append("## Schema (JSON-LD)")
    L.append(check(bool(data.get("schema_types")), f"Schema present (types: {', '.join(sorted(data.get('schema_types', set())))[:80] or 'none'})"))
    L.append(check(not data.get("schema_defects"), f"No schema defects detected ({len(data.get('schema_defects', []))} found)"))
    L.append("")
    L.append("## Crawler access")
    L.append(check(not data.get("ai_bots_blocked"), f"AI crawlers allowed ({len(data.get('ai_bots_blocked', set()))} blocked)"))
    L.append(check(not data.get("adsbot_blocked"), f"AdsBot allowed ({len(data.get('adsbot_blocked', set()))} variants blocked)"))
    L.append("")
    L.append("## Conversion surface")
    forms_total = sum(len(p.get("forms", [])) for p in pages)
    L.append(check(forms_total > 0, f"At least one form on site (found {forms_total})"))
    L.append(check(bool(data.get("phones")), f"Phone number(s) visible ({len(data.get('phones', []))} found)"))
    L.append("")
    L.append("## Content surface")
    page_count = len(pages)
    L.append(check(page_count >= 6, f"Site has 6+ real pages (found {page_count})"))
    L.append(check(not data.get("probe_404s"), f"Common slugs respond 200 ({len(data.get('probe_404s', []))} probed slugs returned 404)"))
    L.append("")
    L.append("## Image alt text")
    total_imgs = sum(p.get("images_total", 0) for p in pages)
    nonempty_imgs = sum(p.get("images_alt_nonempty", 0) for p in pages)
    coverage = (nonempty_imgs / total_imgs * 100) if total_imgs else 0
    L.append(check(coverage >= 50, f"Image alt-text coverage ≥50% (current: {coverage:.0f}%)"))
    L.append("")
    L.append("## NAP consistency")
    addrs = data.get("schema_addresses", [])
    L.append(check(len(set(addrs)) <= 1, f"Single canonical address in schema ({len(set(addrs))} distinct addresses found)"))
    L.append("")

    # PSI / Core Web Vitals
    psi = data.get("psi_results", [])
    if psi:
        L.append("## Performance (PageSpeed Insights)")
        for r in psi:
            if "error" in r:
                L.append(f"- ❌ {r['url']}: PSI error — {r['error'][:80]}")
                continue
            perf = r.get("performance")
            lcp_lab = r.get("lcp_ms")
            cls_lab = r.get("cls")
            tbt = r.get("tbt_ms")
            url_short = r["url"]
            perf_pass = isinstance(perf, (int, float)) and perf >= 90
            lcp_pass = isinstance(lcp_lab, (int, float)) and lcp_lab < 2500
            cls_pass = isinstance(cls_lab, (int, float)) and cls_lab < 0.1
            tbt_pass = isinstance(tbt, (int, float)) and tbt < 200
            L.append(f"- **{url_short}** — Perf: {perf}/100  LCP(lab): {lcp_lab/1000:.1f}s  CLS(lab): {cls_lab:.3f}  TBT(lab): {int(tbt) if isinstance(tbt, (int, float)) else '—'}ms" if all(isinstance(v, (int, float)) for v in [perf, lcp_lab, cls_lab, tbt]) else f"- {url_short}: partial PSI data")
            L.append(check(perf_pass, f"  Performance score ≥ 90 ({perf})"))
            L.append(check(lcp_pass, f"  Lab LCP < 2.5s ({lcp_lab/1000:.1f}s)" if isinstance(lcp_lab, (int, float)) else "  Lab LCP unknown"))
            L.append(check(cls_pass, f"  Lab CLS < 0.1 ({cls_lab:.3f})" if isinstance(cls_lab, (int, float)) else "  Lab CLS unknown"))
            L.append(check(tbt_pass, f"  Lab TBT < 200ms ({int(tbt) if isinstance(tbt, (int, float)) else '—'}ms)"))
            f_lcp = r.get("field_lcp_p75_ms")
            f_inp = r.get("field_inp_p75_ms")
            f_cls = r.get("field_cls_p75")
            if any(v is not None for v in (f_lcp, f_inp, f_cls)):
                L.append(check(isinstance(f_lcp, (int, float)) and f_lcp < 2500, f"  Field LCP p75 < 2.5s ({f_lcp/1000:.1f}s)" if isinstance(f_lcp, (int, float)) else "  Field LCP p75 not available"))
                L.append(check(isinstance(f_inp, (int, float)) and f_inp < 200, f"  Field INP p75 < 200ms ({int(f_inp)}ms)" if isinstance(f_inp, (int, float)) else "  Field INP p75 not available"))
                L.append(check(isinstance(f_cls, (int, float)) and f_cls < 0.1, f"  Field CLS p75 < 0.1 ({f_cls:.3f})" if isinstance(f_cls, (int, float)) else "  Field CLS p75 not available"))
        L.append("")

    out.write_text("\n".join(L) + "\n", encoding="utf-8")


SCRIPT_VERSION = "0.2.0"

# PageSpeed Insights API (no key required for low volumes)
PSI_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT = 90  # PSI can take 30-60s per page

# Page-priority hints for PSI selection (substring match in URL path)
KEY_PAGE_HINTS = [
    "/", "product", "pricing", "service", "contact", "shop", "store",
    "about", "team", "buy", "demo", "signup", "trial",
]


def discover(url: str, bin_dir: Path, do_psi: bool = True, psi_max: int = 3) -> dict:
    """Run the full discovery pipeline. Returns the data dict used to render outputs."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = bin_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    parsed_url = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    base_host = parsed_url.netloc
    base_url = f"{parsed_url.scheme}://{base_host}"
    home_url = f"{base_url}{parsed_url.path or '/'}"

    print(f"[discover] target: {home_url}")
    data: dict = {
        "url": home_url,
        "brand_name": base_host.removeprefix("www."),
        "date": dt.date.today().isoformat(),
        "pages": [],
        "sitemap_urls": [],
        "schema_types": set(),
        "schema_defects": [],
        "schema_addresses": [],
        "ai_bots_blocked": set(),
        "adsbot_blocked": set(),
        "robots_text": "",
        "platform": None,
        "phones": [],
        "emails": [],
        "socials": {},
        "probe_404s": [],
        "expected_schemas": [],
        "_run_psi": do_psi,
        "_psi_max": psi_max,
    }

    # Step 1: fetch homepage
    home_path = raw_dir / "home.html"
    code, body = fetch(home_url, home_path)
    if code != 200:
        # Try www variant
        if not base_host.startswith("www."):
            alt_url = f"https://www.{base_host}{parsed_url.path or '/'}"
            print(f"[discover] retrying {alt_url}")
            code, body = fetch(alt_url, home_path)
            if code == 200:
                home_url = alt_url
                base_host = f"www.{base_host}"
                base_url = f"https://{base_host}"
                data["url"] = home_url

    if code != 200:
        print(f"[discover] FATAL: homepage returned HTTP {code}")
        sys.exit(1)

    home_parser = parse_html(body)
    data["platform"] = detect_platform(body)
    print(f"[discover] platform: {data['platform']}")

    # Step 2: robots + sitemap
    robots_path = raw_dir / "robots.txt"
    code_r, robots_body = fetch(f"{base_url}/robots.txt", robots_path)
    if code_r == 200:
        data["robots_text"] = robots_body
        rules = parse_robots_txt(robots_body)
        for ua, rule in rules.items():
            if any(d.strip() in ("/", "*") or d.strip().startswith("/") for d in rule.get("disallow", [])):
                if ua in AI_CRAWLERS:
                    data["ai_bots_blocked"].add(ua)
                if ua in ADSBOT_CRAWLERS:
                    data["adsbot_blocked"].add(ua)

    sitemap_path = raw_dir / "sitemap.xml"
    sitemap_urls = []
    code_s, sitemap_body = fetch(f"{base_url}/sitemap.xml", sitemap_path)
    if code_s == 200:
        sitemap_urls = parse_sitemap(sitemap_body)
        # If sitemap-of-sitemaps, follow each child
        for s in sitemap_urls[:5]:
            if s.endswith(".xml") and "sitemap" in s.lower():
                child_path = raw_dir / f"sitemap-{slugify(s)}.xml"
                _, child_body = fetch(s, child_path)
                child_urls = parse_sitemap(child_body)
                sitemap_urls.extend(child_urls)
        sitemap_urls = list(dict.fromkeys(sitemap_urls))
    data["sitemap_urls"] = sitemap_urls

    # Step 3: build crawl set (homepage links + sitemap URLs)
    home_internal = []
    for href in home_parser.links:
        path = normalize_internal(href, base_host)
        if path:
            home_internal.append(path)
    home_internal = list(dict.fromkeys(home_internal))

    crawl_targets: list[str] = [home_url]
    seen = {home_url.rstrip("/")}
    # add sitemap urls
    for s in sitemap_urls:
        s_norm = s.rstrip("/")
        if base_host in s and s_norm not in seen:
            crawl_targets.append(s)
            seen.add(s_norm)
    # add homepage-internal links not already in sitemap
    for path in home_internal:
        full = f"{base_url}{path}".rstrip("/")
        if full not in seen and not path.startswith(("/cdn-cgi", "/wp-admin", "/admin")):
            crawl_targets.append(f"{base_url}{path}")
            seen.add(full)

    # cap crawl to a reasonable number
    crawl_targets = crawl_targets[:25]
    print(f"[discover] crawling {len(crawl_targets)} pages")

    # Step 4: fetch each page and parse
    page_records = []
    text_corpus_parts = []
    for target in crawl_targets:
        cache_name = slugify(urllib.parse.urlparse(target).path or "home") + ".html"
        cache_path = raw_dir / cache_name
        if target == home_url and home_path.exists():
            cache_path = home_path
            page_html = body
            status = 200
        else:
            status, page_html = fetch(target, cache_path)
        record = {
            "url": target,
            "status": status,
            "bytes": cache_path.stat().st_size if cache_path.exists() else 0,
            "cache_path": str(cache_path.relative_to(bin_dir)),
        }
        if status == 200 and page_html:
            pp = parse_html(page_html)
            record.update({
                "title": pp.title,
                "meta_description": pp.meta_description,
                "canonical": pp.canonical,
                "h1": pp.headings["h1"],
                "h2": pp.headings["h2"],
                "h3": pp.headings["h3"],
                "images_total": pp.images_total,
                "images_with_alt": pp.images_with_alt,
                "images_alt_nonempty": pp.images_alt_nonempty,
                "forms": pp.forms,
                "links": pp.links,
            })
            text_corpus_parts.append(pp.text)
            # collect schema
            for block in pp.jsonld_blocks:
                parsed = parse_jsonld_blocks([block])
                for node in flatten_jsonld(parsed):
                    ntype = node.get("@type")
                    if isinstance(ntype, list):
                        for t in ntype:
                            data["schema_types"].add(t)
                    elif isinstance(ntype, str):
                        data["schema_types"].add(ntype)
                    # collect address
                    addr = node.get("address")
                    if isinstance(addr, dict):
                        addr_str = ", ".join(filter(None, [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),
                        ]))
                        if addr_str:
                            data["schema_addresses"].append(addr_str)
                    # detect defects (per node)
                    nd = schema_defects([node])
                    for d in nd:
                        if d not in data["schema_defects"]:
                            data["schema_defects"].append(d)
        page_records.append(record)
    data["pages"] = page_records

    # Step 5: probe common slugs for 404s
    print(f"[discover] probing common slugs for 404s")
    probe_404s = []
    seen_paths = {urllib.parse.urlparse(p["url"]).path.strip("/") for p in page_records}
    for slug in PROBE_SLUGS:
        if slug in seen_paths:
            continue
        url = f"{base_url}/{slug}/"
        probe_path = raw_dir / f"_probe_{slug}.html"
        code_probe, _ = fetch(url, probe_path)
        if code_probe == 404:
            probe_404s.append(slug)
        # cleanup probe file regardless to keep raw/ tidy
        try:
            probe_path.unlink()
        except OSError:
            pass
    data["probe_404s"] = probe_404s

    # Step 6: NAP + socials from text corpus
    full_text = " ".join(text_corpus_parts)
    data["phones"] = find_phones(full_text)
    data["emails"] = find_emails(full_text)
    all_links = []
    for p in page_records:
        all_links.extend(p.get("links", []))
    data["socials"] = classify_socials(all_links)

    # Step 7: expected schemas heuristic
    data["expected_schemas"] = expected_schemas_for_business_type(full_text)

    # Step 8: PageSpeed Insights (optional)
    data["psi_results"] = []
    if data.get("_run_psi"):
        psi_pages = select_psi_pages(page_records, data.get("_psi_max", 3))
        print(f"[discover] running PageSpeed Insights on {len(psi_pages)} page(s) (mobile)")
        for i, psi_url in enumerate(psi_pages, 1):
            print(f"[discover]   PSI {i}/{len(psi_pages)}: {psi_url}")
            result = run_psi(psi_url, strategy="mobile")
            if result is not None:
                result["url"] = psi_url
                data["psi_results"].append(result)

    # Step 8: write outputs
    write_digest(bin_dir, data)
    write_checklist(bin_dir, data)
    print(f"[discover] wrote {bin_dir}/_DIGEST.md")
    print(f"[discover] wrote {bin_dir}/_DISCOVERY-NOTES.md")
    print(f"[discover] cached {len(page_records)} pages in {bin_dir}/raw/")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="Target site URL")
    ap.add_argument("bin_dir", help="Project bin folder (created if missing)")
    ap.add_argument("--no-psi", action="store_true",
                    help="Skip PageSpeed Insights pass (~30-60s per page)")
    ap.add_argument("--psi-pages", type=int, default=3,
                    help="Number of pages to test via PSI (default: 3)")
    args = ap.parse_args()
    bin_dir = Path(args.bin_dir).resolve()
    discover(args.url, bin_dir, do_psi=not args.no_psi, psi_max=args.psi_pages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
