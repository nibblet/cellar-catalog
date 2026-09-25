"""casacarrillocigars.com — epcarrillo.com redirects here (a 2025 rebrand from "E.P. Carrillo" to
"Casa Carrillo"). WordPress + WPBakery; no cigar sitemap and no clean product index in the site's
own page sitemap (it's a sprawling marketing site — contests, samplers, a loyalty-club page — mixed
in with the real product pages), so the line list is hand-curated from the site's own "all-products"
page plus a few newer releases not yet added there (Ascend, Battleborn, La Historia Silk).

Each line page states "Sizes" as a `<ul>` of "Name: L x R" (one line each), "Tobaccos" as
Origin/Wrapper/Binder/Filler labels each followed by its value on the next line, and a "Strength –
Word" heading somewhere on the page (not always near the other two blocks). A few limited releases
state a single, sometimes unnamed, size under a bare "Size:" label instead of the plural "Sizes"
list; an unnamed size is kept as its own dimension string, never given an invented name. Origin is
always "Dominican Republic" on every page checked — used directly as country, since it's an
explicit per-page statement, not a curated guess. "Encore Black" (prose only, no size list),
"Legacy League" (a loyalty program, not a cigar) and "Pledge of Allegiance" (data only in prose, one
of its two variants still unreleased) publish nothing this importer can read cleanly and are
skipped."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5  # robots.txt states no crawl-delay
SITE = "https://casacarrillocigars.com"
SITEMAP = SITE + "/page-sitemap.xml"
BRAND = "EP Carrillo"

LINES = {
    "pledge": "Pledge", "la-historia": "La Historia", "encore": "Encore", "allegiance-2": "Allegiance",
    "endure": "Endure", "ascend": "Ascend", "essencesumatra": "Essence Sumatra",
    "essencemaduro": "Essence Maduro", "essencehonduras": "Essence Honduras",
    "essence-connecticut": "Essence Connecticut", "inch-natural": "INCH Natural",
    "inch-maduro": "INCH Maduro", "inch-nicaragua": "INCH Nicaragua",
    "new-wave-connecticut": "New Wave Connecticut", "pledgepurple": "Pledge Purple",
    "deep-blue": "Deep Blue", "battleborn": "Battleborn", "la-historia-silk": "La Historia Silk",
}

STRENGTH_MAP = {
    "mild": "mild", "mild plus": "mild_medium", "medium": "medium", "medium plus": "medium_full",
    "full": "full", "full plus": "full",
}
DIMS_LINE = re.compile(r"^\d.*[x×]\s*\d", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"{SITE}/{slug}/" for slug in LINES]


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    flat = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in flat.split("\n") if l.strip()]


def _country(text: str | None) -> str | None:
    if not text:
        return None
    t = text.strip().lower()
    if "dominican" in t:
        return "Dominican Republic"
    return None


def _strength(lines: list[str]) -> str | None:
    for l in lines:
        m = re.match(r"^Strength\s*[–—-]\s*(.+)$", l, re.I)
        if m:
            return STRENGTH_MAP.get(m.group(1).strip().lower())
    return None


def _facts(lines: list[str]) -> dict[str, str]:
    facts = {}
    for label, key in (("Origin:", "origin"), ("Wrapper:", "wrapper"), ("Binder:", "binder"), ("Filler:", "filler"), ("Fillers:", "filler")):
        if label in lines:
            i = lines.index(label)
            if i + 1 < len(lines):
                facts[key] = lines[i + 1]
    return facts


def _sizes(lines: list[str]) -> list[Vitola]:
    vitolas = []
    started = False
    i = 0
    while i < len(lines):
        l = lines[i]
        if l in ("Sizes", "Size:"):
            started, i = True, i + 1
            continue
        if not started:
            i += 1
            continue
        if l == "Tobaccos":
            break
        m = re.match(r"^(.+?):\s*(\d.*[x×].*\d.*)$", l, re.I)
        if m:
            length_in, ring = dimensions(m.group(2))
            if length_in is not None:
                vitolas.append(Vitola(name=m.group(1).strip(), length_in=length_in, ring_gauge=ring))
            i += 1
            continue
        if l.endswith(":") and i + 1 < len(lines) and DIMS_LINE.match(lines[i + 1]):
            length_in, ring = dimensions(lines[i + 1])
            if length_in is not None:
                vitolas.append(Vitola(name=l.rstrip(":").strip(), length_in=length_in, ring_gauge=ring))
            i += 2
            continue
        if DIMS_LINE.match(l):
            length_in, ring = dimensions(l)  # unnamed size: kept as its own dimension string
            if length_in is not None:
                vitolas.append(Vitola(name=l, length_in=length_in, ring_gauge=ring))
            i += 1
            continue
        i += 1
    return vitolas


def parse(url: str, page: str) -> LineRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    line = LINES.get(slug)
    if not line:
        return None
    lines = _lines(page)
    vitolas = _sizes(lines)
    if not vitolas:
        return None
    facts = _facts(lines)
    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=facts.get("wrapper"), binder=facts.get("binder"), filler=facts.get("filler"),
        body=_strength(lines), country=_country(facts.get("origin")), vitolas=vitolas,
    )
