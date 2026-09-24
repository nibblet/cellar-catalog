"""tatuajecigars.com — a small static (no CMS, no sitemap) legacy site; one HTML page per line,
linked from the homepage's "Smokes" grid. Pete Johnson's company sells several nominally distinct
brands here (Cabaiguan, La Riqueza, El Triunfador, Ambos Mundos, La Casita Criolla, Fausto, Havana
VI, Seleccion de Cazador) alongside the core Tatuaje lines (Black Label, Tattoo, Series P, Avion,
Negociant, Nuevitas, 15th Anniversary); the catalog already files all of it under the "Tatuaje"
brand as a single company catch-all, so this importer keeps that convention. WRAPPER/BINDER/FILLER
and COUNTRY OF ORIGIN are plain labelled tiles; STRENGTH is a "1 2 3 4 5" scale with the current
value wrapped in a `strength-active` span. Sizes are `<div class="single-smoke">` blocks, each a
bold "Name<br>[Wrapper Variant<br>]L x R" paragraph next to its own product photo. A couple of
pages (Guapos) print the wrapper/binder/filler block twice, once per Natural/Maduro variant tag;
handled by splitting into one record per tag, matched to the sizes whose own name ends in it."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5  # robots.txt states no crawl-delay
SITE = "https://tatuajecigars.com"
SITEMAP = SITE + "/"  # no sitemap; only for IMAGE_PREFIX derivation in scripts
IMAGE_PREFIX = SITE + "/img/"
BRAND = "Tatuaje"

# No sitemap; these are the pages linked from the homepage's "Smokes" grid.
SLUGS = [
    "15thAnniversary", "cazador", "miami-reserva", "reserva", "havanavi", "cabaiguan", "guapos",
    "fausto", "lariqueza", "eltriunfador", "ambosmundos", "lacasita", "avion", "verocu",
    "blacklabel", "negociant", "seriesp", "tattoo", "nuevitas",
]

COUNTRY_MAP = {"usa": "United States", "nicaragua": "Nicaragua"}
DIMS_LINE = re.compile(r"^\d+(?:\s+\d/\d)?\s*x\s*\d+(?:/\d+)?$", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"{SITE}/{slug}.html" for slug in SLUGS]


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


def _clean_line(title: str) -> str:
    if title.lower().startswith(BRAND.lower()):
        title = title[len(BRAND):].strip(" -–—:")
    return title


def _strength(page: str) -> str | None:
    m = re.search(r'<font class="strength-active">([^<]+)</font>', page)
    if not m:
        return None
    digits = [int(d) for d in re.findall(r"\d", m.group(1))]
    if not digits:
        return None
    n = round(sum(digits) / len(digits))
    return {1: "mild", 2: "mild_medium", 3: "medium", 4: "medium_full", 5: "full"}.get(n)


def _facts_blocks(lines: list[str]) -> list[tuple[str | None, str, str, str]]:
    """Every (tag, wrapper, binder, filler) tuple, in order. tag is the all-caps line right
    before "WRAPPER" (e.g. "NATURAL", "MADURO") when the page states the block more than once."""
    blocks = []
    for i, l in enumerate(lines):
        if l != "WRAPPER" or i + 5 >= len(lines):
            continue
        if lines[i + 2] != "BINDER" or lines[i + 4] != "FILLER":
            continue
        tag = lines[i - 1] if i > 0 and lines[i - 1].isupper() and lines[i - 1] != "WRAPPER" else None
        blocks.append((tag, lines[i + 1], lines[i + 3], lines[i + 5]))
    return blocks


def _sizes(page: str) -> list[Vitola]:
    vitolas = []
    for m in re.finditer(r'<div class="single-smoke[^"]*"[^>]*>.*?</div>', page, re.S):
        block = m.group(0)
        p = re.search(r'<p style="font-weight:bold;">(.*?)</p>', block, re.S)
        img = re.search(r'<img src="([^"]+)"', block)
        if not p:
            continue
        parts = [html.unescape(re.sub(r"\s+", " ", seg)).strip() for seg in p.group(1).split("<br>")]
        parts = [seg for seg in parts if seg]
        if not parts or not DIMS_LINE.match(parts[-1]):
            continue
        name = " ".join(parts[:-1])
        length_in, ring = dimensions(parts[-1])
        if length_in is None or ring is None:
            continue
        image = SITE + "/" + img.group(1) if img and not img.group(1).startswith("http") else (img.group(1) if img else None)
        vitolas.append(Vitola(name=name, length_in=length_in, ring_gauge=ring, image_url=image))
    return vitolas


def parse(url: str, page: str) -> LineRecord | list[LineRecord] | None:
    h2 = re.search(r"<h2>(.*?)</h2>", page, re.S)
    if not h2:
        return None
    line = _clean_line(html.unescape(re.sub(r"<[^>]+>", "", h2.group(1))).strip())
    lines = _lines(page)
    vitolas = _sizes(page)
    if not vitolas:
        return None
    blocks = _facts_blocks(lines)
    body = _strength(page)
    country = None
    if "COUNTRY OF ORIGIN" in lines:
        i = lines.index("COUNTRY OF ORIGIN")
        if i + 1 < len(lines):
            country = COUNTRY_MAP.get(lines[i + 1].strip().lower(), lines[i + 1].strip())
    if len(blocks) <= 1:
        wrapper, binder, filler = blocks[0][1:] if blocks else (None, None, None)
        return LineRecord(brand=BRAND, line=line, source_url=url, wrapper_raw=wrapper, binder=binder,
                           filler=filler, body=body, band_image_url=vitolas[0].image_url,
                           country=country, vitolas=vitolas)
    # more than one wrapper/binder/filler block (a Natural/Maduro split): match each size's own
    # name against the tag before its block, rather than guessing which block a size belongs to.
    records = []
    for tag, wrapper, binder, filler in blocks:
        if not tag:
            continue
        matched = [v for v in vitolas if v.name.lower().endswith(tag.lower())]
        if matched:
            records.append(LineRecord(brand=BRAND, line=line, source_url=url, wrapper_raw=wrapper,
                                       binder=binder, filler=filler, body=body,
                                       band_image_url=matched[0].image_url, country=country, vitolas=matched))
    return records or None
