"""cigarworld.com — General Cigar's site, one page per line. Wrapper/binder/filler are named
tobaccos (links under /cigars/tobacco/), body is a 1–5 scale, and every size is inline in the
page's Vue markup: title = 'No.I Natural', ring = '54', length = '7.25', shape = 'Parejo'.

The site also lists other makers' brands; only General Cigar's own are treated as maker data.
Thin modules (hoyo.py, punch.py …) pick the brand slugs; this one does the work."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import clean_value, shape, size_name, wrapper

DELAY = 3
SITEMAP = "https://www.cigarworld.com/sitemap.xml/sitemap/Cw-Cigars-Objects-Product/1"
IMAGE_PREFIX = "https://d25bsrltkk1hnl.cloudfront.net/"

BODY = {"1": "Mild", "2": "Mild-Medium", "3": "Medium", "4": "Medium-Full", "5": "Full"}  # setBodyKeyword()

# Site brand slug → (catalog brand, line prefix). Excalibur is filed under Hoyo, as General's
# own copy still calls it "Hoyo de Monterrey Excalibur".
BRAND_MAP = {
    "hoyo-de-monterrey": ("Hoyo de Monterrey", None),
    "excalibur": ("Hoyo de Monterrey", "Excalibur"),
    "punch": ("Punch", None),
    "cohiba": ("Cohiba", None),
    "cao": ("CAO", None),
    "cao-flavours": ("CAO", "Flavours"),
    "macanudo": ("Macanudo", None),
    "partagas": ("Partagas", None),
    "la-gloria-cubana": ("La Gloria Cubana", None),
}


def list_urls(fetcher, brands: list[str]) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = re.findall(r"<loc>(https://www\.cigarworld\.com/cigars/([a-z0-9-]+)/[a-z0-9-]+/)</loc>", xml)
    return sorted(u for u, b in set(urls) if b in brands and not u.endswith("/reviews/"))


def _text(fragment: str) -> str:
    # NFC: the copy sometimes spells "Estelí" with a combining accent, which no pattern would match
    return unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).replace("\xa0", " ").replace("\u2011", "-")


def _tobaccos(page: str, cls: str) -> str | None:
    block = re.search(rf'<div class="{cls}"[^>]*>(.*?)</div>', page, re.S)
    if not block:
        return None
    names = [_text(n).strip() for n in re.findall(r'<a href="/cigars/tobacco/[^"]+">(.*?)</a>', block.group(1), re.S)]
    return clean_value(", ".join(n for n in names if n)) or None


LEAF_WORDS = r"san andr[eé]s|connecticut broadleaf|broadleaf|connecticut shade|connecticut|cameroon|sumatra|habano|corojo|criollo|candela|maduro|oscuro|rosado|sun[- ]?grown"
MADE_IN = re.compile(r"(?i)(?:hand-?made|hand-?crafted|crafted|made|rolled|produced|manufactured)\s+(?:in|at)\s+(?:the\s+)?(?:STG\s+)?([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ,]{2,40}?)(?=[.,;]|\s+(?:by|for|with|using|from|and|this|the)\b)")
PLACE_MADE = re.compile(r"(?i)\b(Estel[ií]|Danl[ií]|Santiago|Nicaragua|Honduras)[- ]made\b")  # "this Estelí-made blend"
FACTORY_COUNTRY = {"esteli": "Nicaragua", "estelí": "Nicaragua", "danli": "Honduras", "danlí": "Honduras", "santiago": "Dominican Republic",
                   "nicaragua": "Nicaragua", "honduras": "Honduras", "dominican republic": "Dominican Republic"}
# General's own factories, when the copy names one instead of a country
FACTORY_NAMES = {"el credito": "Dominican Republic"}  # El Credito Cigar Factory, Santiago


def _country(desc: str) -> str | None:
    """The country the maker's own copy says the cigar is rolled in, if it says so."""
    for m in MADE_IN.finditer(desc):
        place = m.group(1).strip().lower()
        for k, v in FACTORY_COUNTRY.items():
            if k in place:
                return v
    m = PLACE_MADE.search(desc)
    if m:
        return FACTORY_COUNTRY[m.group(1).lower()]
    for k, v in FACTORY_NAMES.items():
        if re.search(rf"(?i)\b{k} (?:cigar )?factory\b", desc):
            return v
    return None


def parse(url: str, page: str, country_by_line: dict | None = None) -> LineRecord | None:
    slug = url.split("/")[4]
    if slug not in BRAND_MAP:
        return None
    brand, prefix = BRAND_MAP[slug]
    h1 = re.search(r"<h1>\s*<a[^>]*>\s*<span class=\"brand\">(.*?)</span>\s*</a>\s*(.*?)\s*</h1>", page, re.S)
    if not h1:
        return None
    line = _text(h1.group(2)).strip()
    if prefix:
        line = prefix if line.lower() == prefix.lower() else (line if prefix.lower() in line.lower() else f"{prefix} {line}")
    sizes = []
    for title, ring, length, shp in re.findall(r"title = '([^']*)', ring = '([^']*)', length = '([^']*)', shape = '([^']*)'", page):
        name = re.sub(r"\bNo\.(?=\S)", "No. ", html.unescape(title).replace("\\'", "'")).strip()  # "No.I" → "No. I"
        # the maker's shape word ("Torpedo", "Perfecto"; "Cigarillo" is a parejo) beats the size name
        L, R = (float(length) if length else None), (int(ring) if ring else None)
        if L is not None and R is not None and L >= 20 > R:
            L, R = float(R), int(L)  # the site occasionally swaps them ("54 x 7")
        if not L or not R:
            L = R = None  # "0 x 0" is the site's blank
        sizes.append(Vitola(name=name, length_in=L, ring_gauge=R, shape=shape(shp)[0]))
    if not sizes:
        return None
    # "Toro Tubo (Aluminum Tube)" → "Toro Tubo": packaging asides go, unless that would merge two sizes
    short = [size_name(v.name) or v.name for v in sizes]
    if len(set(short)) == len(sizes):
        for v, s in zip(sizes, short):
            v.name = s
    body = re.search(r"setBodyKeyword\((\d)\)", page)
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    d = re.search(r'<p class="description">(.*?)</p>', page, re.S)
    desc = _text(d.group(1)) if d else ""
    # "Ecuadorian" names only the region; the copy often names the leaf ("Habano wrapper")
    wrapper_raw = _tobaccos(page, "wrappers")
    if wrapper_raw and "," in wrapper_raw:
        wrapper_raw = None  # two wrappers listed for one line (natural and maduro sizes): nothing to pin on a row
    elif wrapper_raw and wrapper(wrapper_raw)[0] == "unknown":
        words = [w for w in re.findall(LEAF_WORDS, desc, re.I)
                 if re.search(rf"\b{re.escape(w)}\b[^.]{{0,40}}wrapp|wrapp[^.]{{0,40}}\b{re.escape(w)}\b", desc, re.I)]
        if words:
            wrapper_raw = wrapper_raw + " " + " ".join(dict.fromkeys(w.lower() for w in words))
    country = _country(desc) or (country_by_line or {}).get(line)
    return LineRecord(
        brand=brand, line=line, source_url=url,
        wrapper_raw=wrapper_raw, binder=_tobaccos(page, "binders"), filler=_tobaccos(page, "fillers"),
        body=BODY.get(body.group(1)) if body else None,
        band_image_url=og.group(1) if og else None, vitolas=sizes, country=country,
    )
