"""joyacigars.com — WordPress, one page per line under /cigars/<slug>/ (the sitemap also lists a
Spanish /es/cigars/<slug>-es/ mirror of each; skipped). Facts are labelled tiles: STRENGTH as a
disclosed "N/5" rating, WRAPPER/BINDER/FILLER as plain text. Sizes are a "Name" / "L x R" list
(fractions sometimes use the Unicode fraction slash ⁄, U+2044, not "/") found by scanning for any
line that reads as dimensions, since there is no reliable heading to bound the list by. The
homepage states "a brand of cigars made in Nicaragua...manufacture its products today from its
headquarters in Estelí" — a company-wide statement, so country is curated from it, not per line."""
from __future__ import annotations

import re

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5
SITE = "https://joyacigars.com"
SITEMAP = SITE + "/cigars-sitemap.xml"
IMAGE_PREFIX = SITE + "/wp-content/uploads/"
BRAND = "Joya de Nicaragua"
COUNTRY = "Nicaragua"  # CURATED — homepage: "a brand of cigars made in Nicaragua...headquarters in Estelí"

STRENGTH = {1: "mild", 2: "mild_medium", 3: "medium", 4: "medium_full", 5: "full"}
LABELS = ("STRENGTH", "WRAPPER", "BINDER", "FILLER")
DIMS_LINE = re.compile(r"^\d+(?:[ .]\d+[/⁄]\d+)?\s*x\s*\d+(?:\s*\(BP\))?$", re.I)


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    return sorted(u for u in urls if re.search(r"/cigars/[^/]+/$", u) and "/es/" not in u)


def _lines(page: str) -> list[str]:
    import html, unicodedata
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


# Codes/acronyms the site's own shouted headings would otherwise mangle ("Ct", "Taa"); other
# pages already mix case correctly on their own ("El Embargo (Outside USA)") and are left alone —
# only a line that shouts in full is touched at all.
SHOUT_EXCEPTIONS = {"CT", "RR", "TAA"}
STOPWORDS = {"de", "del", "la", "el", "los", "las", "y"}


def _unshout(text: str) -> str:
    if not text.isupper():
        return text
    out = []
    for w in text.split():
        if w in SHOUT_EXCEPTIONS:
            out.append(w)
        elif w.lower() in STOPWORDS:
            out.append(w.lower())
        else:
            out.append(w.title())
    return " ".join(out)


def _sizes(lines: list[str], end: int) -> list[Vitola]:
    vitolas = []
    for i in range(min(end, len(lines)) - 1):
        dims = lines[i + 1].strip()
        if not DIMS_LINE.match(dims):
            continue
        length_in, ring = dimensions(dims.replace("⁄", "/"))
        if length_in is not None and ring is not None:
            vitolas.append(Vitola(name=_unshout(lines[i]), length_in=length_in, ring_gauge=ring))
    return vitolas


def parse(url: str, page: str) -> LineRecord | None:
    if not re.search(r"/cigars/[^/]+/$", url) or "/es/" in url:
        return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if not h1:
        return None
    line = _unshout(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1.group(1))).strip())
    lines = _lines(page)
    facts, i = {}, 0
    while i < len(lines) - 1:
        if lines[i] in LABELS:
            facts[lines[i]] = lines[i + 1]
        i += 1
    end = lines.index("MORE CIGARS") if "MORE CIGARS" in lines else len(lines)
    vitolas = _sizes(lines, end)
    if not vitolas:
        return None
    m = re.match(r"(\d)\s*/\s*5", facts.get("STRENGTH", ""))
    body = STRENGTH.get(int(m.group(1))) if m else None
    imgs = re.findall(r'src="(' + re.escape(IMAGE_PREFIX) + r'[^"]+)"', page)
    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=facts.get("WRAPPER"), binder=facts.get("BINDER"), filler=facts.get("FILLER"),
        body=body, band_image_url=imgs[0] if imgs else None, country=COUNTRY, vitolas=vitolas,
    )
