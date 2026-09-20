"""olivacigar.com — WordPress, one page per line. Sizes are `.cigar-item` cards whose <h3> reads
"L x R Name" ("7x50 Churchill", "Melanio 6x60 Double Toro"). Blend facts are a single
"Wrapper – Ecuador | Binder – Nicaragua | Filler – Nicaragua" heading: the wrapper is named by
origin only, so the leaf comes from the line's description when it names one, else stays unknown."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import clean_value, dimensions, size_name

BRAND = "Oliva"
COUNTRY = "Nicaragua"  # everything is rolled at TABOLISA in Estelí
DELAY = 10
SITEMAP = "https://olivacigar.com/products-sitemap.xml"

# Catalog rows re-filed by hand: the maker's name for the same product.
OVERRIDES = {
    "7faa52ee-1556-4dc1-82c2-927d399c63e4": {"line": "Serie G"},                    # "Serie G Cameroon" is the site's plain Serie G
    "03bca963-91e2-4149-a176-a27fa411591f": {"expression": "Special V Figurado"},  # Serie V "Figurado" is the Special V Figurado
}

# Leaf words the descriptions use; the origin from the stats line is prepended.
LEAF_WORDS = r"san andr[eé]s|connecticut broadleaf|broadleaf|connecticut shade|connecticut|cameroon|sumatra|habano|corojo|criollo|candela|maduro|sun[- ]?grown"


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(set(re.findall(r"<loc>(https://olivacigar\.com/cigars/[^<]+/)</loc>", xml)))


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("\xad", "")  # soft hyphens in "Con­necticut"


def parse(url: str, page: str) -> LineRecord | None:
    anchor = re.search(r'class="[^"]*\bcigar-sizes\b[^"]*"', page)
    if not anchor:
        return None
    body = page[anchor.start():]
    title = re.search(r"<h2>\s*(?:The\s+)?(.*?)\s*</h2>", page[: anchor.start()], re.S)
    line = _text(title.group(1)).strip() if title else None
    if line and line.lower().startswith(BRAND.lower() + " "):
        line = line[len(BRAND) :].strip()
    if line:
        line = re.sub(r"\bDe\b", "de", line)  # the site title-cases "Flor De Oliva"

    sizes = []
    for card in re.finditer(r'<div class="cigar-wrapper clearfix">(.*?)</div>\s*</div>', body, re.S):
        img = re.search(r'<img[^>]+src="([^"]+)"', card.group(1))
        h3 = re.search(r"<h3>(.*?)</h3>", card.group(1), re.S)
        if not h3:
            continue
        label = re.sub(r"\s+", " ", _text(h3.group(1))).strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d{2,3})", label, re.I)
        if not m:
            continue
        length, ring = dimensions(f"{m.group(1)} x {m.group(2)}")
        name = (label[: m.start()] + " " + label[m.end() :]).strip()
        # cards may carry a line word ("Melanio 6x60 Double Toro"); the size is what's left
        for w in (line or "").split():
            name = re.sub(rf"^{re.escape(w)}\s+", "", name, flags=re.I)
        name = size_name(re.sub(r"^NO\.", "No.", name)) or f"{m.group(1)}x{m.group(2)}"
        sizes.append(Vitola(name=name, length_in=length, ring_gauge=ring, image_url=img.group(1) if img else None))
    if not sizes:
        return None

    stats_text = re.sub(r"\s+", " ", _text(re.sub(r"</?strong>", "", body)))
    stats = re.search(r"Wrapper\s*[–-]\s*([A-Za-z ]+?)\s*\|\s*Binder\s*[–-]\s*([A-Za-z ]+?)\s*\|\s*Filler\s*[–-]\s*([A-Za-z]+(?: [a-z]+)*)", stats_text)
    origin = binder = filler = None
    if stats:
        origin, binder, filler = (clean_value(x.strip()) for x in stats.groups())
    # the description sits in <h4>s after the size cards
    desc = " ".join(_text(h) for h in re.findall(r"<h4[^>]*>(.*?)</h4>", body, re.S))
    words = re.findall(LEAF_WORDS, desc, re.I)
    words = [w for w in words if re.search(rf"\b{re.escape(w)}\b[^.]{{0,40}}wrapp|wrapp[^.]{{0,60}}\b{re.escape(w)}\b", desc, re.I)]
    # like Kristoff, the line name often carries the leaf or shade ("Flor Corojo", "Serie V Maduro")
    words += re.findall(LEAF_WORDS, line or "", re.I)
    hint = " ".join(dict.fromkeys(w.lower() for w in words))
    wrapper_raw = " ".join(x for x in (origin, hint) if x) or None
    band = re.search(r'class="banner-image"><img src="([^"]+)"', page)
    strength = re.search(r"\b(mild to medium|medium to full|mild|medium|full)[- ]bod", desc, re.I)
    return LineRecord(
        brand=BRAND, line=line, source_url=url, wrapper_raw=wrapper_raw, binder=binder, filler=filler,
        body=strength.group(1).title() if strength else None,
        band_image_url=band.group(1) if band else None, vitolas=sizes,
    )
