"""altadisusa.com — WordPress (Altadis USA / Tabacalera USA: Montecristo, Romeo y Julieta, H. Upmann,
and 13 other brands on one platform, each its own `cigar_product` post type). Scoped to Montecristo,
Romeo y Julieta and H. Upmann per the brand queue. Every line page states origin/wrapper/binder/filler as
labelled "spec tiles", and sizes as a repeating "Name:" / "A x B" list — most pages give ring gauge
first, length second (the reverse of most makers), but a few give length first, and one page mixes
both orders on different rows; whichever number reads as a plausible ring gauge (a whole number in
the high-20s to 80s) is taken as the ring, not fixed position. About half the pages also carry a
numeric "strength" tile (1 to 9 observed), but the site never discloses its scale, so body stays
unknown rather than guess a mapping."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola

DELAY = 5
SITE = "https://www.altadisusa.com"
SITEMAP = SITE + "/wp-sitemap-posts-cigar_product-1.xml"
IMAGE_PREFIX = SITE + "/wp-content/uploads/"
BRANDS = {"montecristo": "Montecristo", "romeo-y-julieta": "Romeo y Julieta", "h-upmann": "H. Upmann"}

# Origin states an adjective ("Nicaraguan") as often as a country name ("Nicaragua"), and adds a
# factory aside either way round: "Nicaragua (Manufactured at Plasencia Nicaragua)" or
# "AJ Fernandez (Nicaragua)". A bare factory name with no country anywhere ("TDG") stays unknown.
COUNTRY_ADJ = {
    "nicaraguan": "Nicaragua", "dominican": "Dominican Republic", "honduran": "Honduras",
    "mexican": "Mexico", "ecuadorian": "Ecuador", "cuban": "Cuba",
}
COUNTRIES = {"Nicaragua", "Dominican Republic", "Honduras", "Mexico", "Ecuador", "Cuba", "United States"}

LABELS = ("origin", "wrapper", "binder", "filler", "strength")
DIMS = re.compile(r"(\d+(?:\.\d+)?)(?:\s+(\d)/(\d))?\s*x\s*(\d+(?:\.\d+)?)(?:\s+(\d)/(\d))?", re.I)

# The site's own wp-sitemap 404s for stretches at a time (seen during the Montecristo/Romeo y
# Julieta import and again for H. Upmann) while every individual product page keeps loading fine —
# a CDN-cache issue, not a bot block. Last known-good sitemap listing for our three brands, used
# only when the sitemap itself is unreachable.
FALLBACK_URLS = [
    SITE + p for p in (
        "/cigars/h-upmann/h-upmann-1844-classic/", "/cigars/h-upmann/h-upmann-1844-reserve/",
        "/cigars/h-upmann/h-upmann-aj-fernandez/", "/cigars/h-upmann/h-upmann-anejo/",
        "/cigars/h-upmann/h-upmann-nicaragua-aj-fernandez-heritage/",
        "/cigars/h-upmann/h-upmann-the-banker-daytrader/", "/cigars/h-upmann/h-upmann-the-banker/",
        "/cigars/h-upmann/h-upmann-vintage-cameroon/",
        "/cigars/montecristo/montecristo-1935-edition-diamante/", "/cigars/montecristo/montecristo-1935/",
        "/cigars/montecristo/montecristo-classic-series/", "/cigars/montecristo/montecristo-epic-vintage-12/",
        "/cigars/montecristo/montecristo-epic/", "/cigars/montecristo/montecristo-espada-oscuro/",
        "/cigars/montecristo/montecristo-espada-signature-limited-edition/",
        "/cigars/montecristo/montecristo-espada/", "/cigars/montecristo/montecristo-nicaragua-series/",
        "/cigars/montecristo/montecristo-original/", "/cigars/montecristo/montecristo-platinum-series/",
        "/cigars/montecristo/montecristo-white-series/", "/cigars/montecristo/montecristo_m/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-150th-anniversary/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-1875-by-ryj/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-1875-connecticut-nicaragua/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-1875-nicaragua/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-1875-reserve-maduro/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-1875/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-reserva-real-nicaragua-midnight-twist/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-reserva-real-nicaragua/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-reserva-real-twisted/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-reserva-real/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-reserve/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-romeo-by-romeo/",
        "/cigars/romeo-y-julieta/romeo-y-julieta-vintage/",
    )
]


def list_urls(fetcher) -> list[str]:
    try:
        xml = fetcher.get(SITEMAP)
    except Exception:
        return sorted(FALLBACK_URLS)
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    return sorted(u for u in urls if any(f"/cigars/{b}/" in u for b in BRANDS))


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


def _country(raw: str | None) -> str | None:
    if not raw:
        return None
    m = re.search(r"\(([^)]*)\)", raw)
    outer = re.sub(r"\s*\([^)]*\)", "", raw).strip()
    for candidate in (outer, m.group(1).strip() if m else ""):
        if not candidate:
            continue
        key = candidate.lower()
        if key in COUNTRY_ADJ:
            return COUNTRY_ADJ[key]
        first = candidate.split()[0].lower()
        if first in COUNTRY_ADJ:
            return COUNTRY_ADJ[first]
        if candidate in COUNTRIES:
            return candidate
        hit = next((c for c in COUNTRIES if c.lower() in key), None)
        if hit:
            return hit
    return None


def _num(whole: str, num: str | None, den: str | None) -> float:
    v = float(whole)
    return v + (int(num) / int(den) if num else 0.0)


def _dims(text: str) -> tuple[float | None, int | None]:
    m = DIMS.search(text.strip())
    if not m:
        return None, None
    a = _num(m.group(1), m.group(2), m.group(3))
    b = _num(m.group(4), m.group(5), m.group(6))
    def is_ring(v):
        return v == int(v) and 20 <= v <= 90
    if is_ring(a) and not is_ring(b):
        return b, int(a)
    if is_ring(b) and not is_ring(a):
        return a, int(b)
    return None, None  # both or neither look like a ring gauge: genuinely ambiguous, don't guess


def _unshout(text: str) -> str:
    # a handful of pages shout a name in full caps (TORO, DEMI); title-case real words back to
    # the site's normal style, leaving short tokens (initials, codes) alone
    return " ".join(w.title() if (w.isupper() and len(w) > 3) else w for w in text.split())


# A page's own brand-prefix spelling occasionally drops the period's space ("H.Upmann The Banker
# Daytrader" vs. every other H. Upmann page's "H. Upmann ___").
BRAND_PREFIXES = {"H. Upmann": ("H. Upmann", "H.Upmann")}


def _clean_line(title: str, brand: str) -> str | None:
    line = title
    for prefix in BRAND_PREFIXES.get(brand, (brand,)):
        if line.lower().startswith(prefix.lower()):
            line = line[len(prefix):].strip(" -–—:")
            break
    return _unshout(line) or None


def _sizes(lines: list[str], start: int, end: int) -> list[Vitola]:
    vitolas = []
    i = start
    while i < end - 1:
        name = lines[i]
        if not name.endswith(":"):
            i += 1
            continue
        name = name[:-1].strip()
        name = re.sub(r"\s*:?\s*\d+\s*x\s*\d.*$", "", name, flags=re.I).strip()  # a size's own name occasionally repeats its dims ("Churchill: 50 x 7")
        name = _unshout(name)
        length_in, ring = _dims(lines[i + 1])
        if length_in is not None:
            vitolas.append(Vitola(name=name, length_in=length_in, ring_gauge=ring))
        i += 2
    return vitolas


def parse(url: str, page: str) -> LineRecord | None:
    seg = url.rstrip("/").split("/")
    brand = BRANDS.get(seg[-2]) if len(seg) >= 2 else None
    if not brand:
        return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if not h1:
        return None
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1.group(1))).strip()
    line = _clean_line(title, brand)
    lines = _lines(page)
    if "Available in Sizes" not in lines:
        return None
    start = lines.index("Available in Sizes") + 1
    end = next((i for i in range(start, len(lines)) if lines[i] in LABELS), len(lines))
    vitolas = _sizes(lines, start, end)
    if not vitolas:
        return None
    facts, i = {}, end
    while i < len(lines) - 1 and lines[i] in LABELS:
        facts[lines[i]] = lines[i + 1]
        i += 2
    imgs = re.findall(r'src="(' + re.escape(IMAGE_PREFIX) + r'[^"]+)"', page)
    image = imgs[1] if len(imgs) > 1 else (imgs[0] if imgs else None)
    return LineRecord(
        brand=brand, line=line, source_url=url,
        wrapper_raw=facts.get("wrapper"), binder=facts.get("binder"), filler=facts.get("filler"),
        body=None, band_image_url=image, country=_country(facts.get("origin")), vitolas=vitolas,
    )
