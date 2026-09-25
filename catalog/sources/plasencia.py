"""plasenciacigars.com — WordPress (Yoast) with a custom "collection" post type: one page per
line (`/collection/<slug>/`), each with an embedded owl-carousel gallery of every size in that
line (name + shape + dims + its own photo) plus a shared spec table and a leaf-icon strength
meter for the whole line. The site also publishes one landing page per SIZE under `/cigar/`, but
those carry no spec data at all — hero image and title only — so this importer reads only the
9 collection pages. The spec table's "Origin" field is inconsistent across lines (sometimes a
plain country — "Nicaragua" — sometimes a factory name — "Tabacos Oriente" — sometimes a blend of
two countries joined by "&"); country is read from it only when it resolves to exactly one known
country name, never guessed from a factory name or left ambiguous across a blend."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5  # robots.txt states no crawl-delay
SITE = "https://www.plasenciacigars.com"
SITEMAP = SITE + "/collection-sitemap.xml"
BRAND = "Plasencia"

COUNTRIES = ("Nicaragua", "Honduras", "Dominican Republic", "United States", "Ecuador", "Mexico", "Cuba")
STRENGTH_SCALE = {1: "mild", 2: "mild_medium", 3: "medium", 4: "medium_full", 5: "full"}
DASH_FRACTION = re.compile(r"(\d)-(\d/\d)")


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    return sorted(u for u in urls if u.rstrip("/") != SITE + "/collection")


def _strip(text: str) -> str:
    return unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def _unshout(text: str) -> str:
    # most lines' size names are already properly cased ("Cortez", "Santa Fe"); Cosecha 151's
    # page shouts them ("LA MÚSICA") — title-case only a string that is entirely uppercase, so a
    # normally-cased name is never touched.
    return text.title() if text.isupper() else text


def _country(text: str | None) -> str | None:
    if not text:
        return None
    hits = {c for c in COUNTRIES if c in text}
    return hits.pop() if len(hits) == 1 else None


def _strength(page: str) -> str | None:
    m = re.search(r'class="strength-leaves">(.*?)</ul>', page, re.S)
    if not m:
        return None
    classes = re.findall(r'<li class="([^"]*)"', m.group(1))
    if not classes:
        return None
    n = sum(1.0 if c == "active" else 0.5 if c == "half" else 0.0 for c in classes)
    return STRENGTH_SCALE.get(round(n)) if n else None


def _facts(page: str) -> dict[str, str]:
    m = re.search(r'<table class="info">(.*?)</table>', page, re.S)
    if not m:
        return {}
    labels = re.findall(r"<th><h3>(.*?)</h3></th>", m.group(1), re.S)
    values = re.findall(r"<td><p>(.*?)</p></td>", m.group(1), re.S)
    return {_strip(k).lower(): _strip(v) for k, v in zip(labels, values)}


def _sizes(page: str) -> list[Vitola]:
    vitolas = []
    for m in re.finditer(r'<div class="item">(.*?)</div>', page, re.S):
        block = m.group(0)
        t = re.search(r'class="title[^"]*">(.*?)</h3>', block, re.S)
        img = re.search(r'<img[^>]*src="([^"]+)"', block)
        s = re.search(r'class="subtitle[^"]*">(.*?)</h3>', block, re.S)
        if not t or not s:
            continue
        name = _strip(re.sub(r"<br\s*/?>", " ", t.group(1)))
        name = _unshout(re.sub(r"\s+", " ", name).strip())
        sub = _strip(re.sub(r"<br\s*/?>", " ", s.group(1)))
        sub = re.sub(r"\s+", " ", sub).strip()
        if not name or not sub:
            continue
        dm = re.match(r"^(\D*?)\s*([\d].*)$", sub)
        if not dm:
            continue
        dims_text = DASH_FRACTION.sub(r"\1 \2", dm.group(2))
        length_in, ring = dimensions(dims_text)
        if length_in is None:
            continue
        image = img.group(1) if img else None
        vitolas.append(Vitola(name=name, length_in=length_in, ring_gauge=ring, image_url=image))
    return vitolas


def parse(url: str, page: str) -> LineRecord | None:
    t = re.search(r"<title>(.*?)</title>", page, re.S)
    if not t:
        return None
    line = _strip(t.group(1)).split(" - ")[0].strip()
    if not line or line.lower() == "collection":
        return None
    vitolas = _sizes(page)
    if not vitolas:
        return None
    facts = _facts(page)
    country = _country(facts.get("origin")) or _country(facts.get("blend"))
    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=facts.get("wrapper"), binder=facts.get("binder"), filler=facts.get("filler"),
        body=_strength(page), band_image_url=vitolas[0].image_url,
        country=country, vitolas=vitolas,
    )
