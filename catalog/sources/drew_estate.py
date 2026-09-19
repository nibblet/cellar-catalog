"""drewestate.com — one page per line under /products/<brand>/<line>/. Facts sit in an SVG
(label/value pairs), body in .cigar-body-label, sizes as .card-sizing cards, band as img.brand-logo."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import clean_value, dimensions, size_name

BRANDS = {
    "liga-privada": "Liga Privada", "undercrown": "Undercrown", "herrera-esteli": "Herrera Esteli",
    "nica-rustica": "Nica Rustica", "acid": "Acid", "kentucky-fire-cured": "Kentucky Fire Cured",
    "tabak-especial": "Tabak Especial", "isla-del-sol": "Isla del Sol", "deadwood": "Deadwood",
    "java": "Java", "factory-smokes": "Factory Smokes", "20-acre-farm": "20 Acre Farm",
    "blackened": "Blackened", "larutan": "Larutan", "natural": "Natural", "ambrosia": "Ambrosia",
    "muwat": "MUWAT", "pappy-van-winkle": "Pappy Van Winkle", "freestyle-live": "Freestyle Live",
    "drew-estate": "Drew Estate",
}


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).strip()


def _svg_value(page: str, label: str) -> str | None:
    m = re.search(rf'cigar-label"[^>]*>\s*<tspan[^>]*>{label}</tspan>.*?</g>(.*?)</g>', page, re.S)
    if not m:
        return None
    vals = re.findall(r"<tspan[^>]*>(.*?)</tspan>", m.group(1))
    v = " ".join(html.unescape(x).strip() for x in vals if x.strip())
    return re.sub(r"\s+", " ", v) or None


def parse(url: str, page: str) -> LineRecord | None:
    m = re.match(r"https://drewestate\.com/products/([^/]+)/(?:([^/]+)/)?$", url)
    if not m:
        return None
    brand_slug, line_slug = m.group(1), m.group(2)
    # Brand hubs carry no sizes; a one-line brand (20 Acre Farm) lists its sizes on the hub itself.

    title = re.search(r"<title>(.*?)</title>", page, re.S)
    title = html.unescape(title.group(1)).split(" - Drew Estate")[0].strip() if title else line_slug
    brand = BRANDS.get(brand_slug, brand_slug.replace("-", " ").title())
    line = None if not line_slug else title
    if line and line.lower().startswith(brand.lower()):
        line = line[len(brand):].strip(" -–—:") or None
    if line:
        # The site shouts some names (BLUE, S84 SHADE TO BLACK); keep short all-caps tokens like UC, M81.
        line = " ".join(w.title() if (w.isupper() and len(w) > 3) else w for w in line.split())

    sizes = []
    # Cards are siblings: split on the opener and read each chunk up to its <p>dimensions</p>.
    for card in re.split(r'<div class="card-sizing">', page)[1:]:
        card = card.split("</p>", 1)[0]
        name = re.search(r'card-sizing-label">(.*?)</h3>', card, re.S)
        dims = re.search(r"<p>(.*)$", card, re.S)
        if not name:
            continue
        length, ring = dimensions(_text(dims.group(1))) if dims else (None, None)
        img = re.search(r'<img[^>]+src="([^"]+)"', card)
        sizes.append(Vitola(name=size_name(_text(name.group(1))), length_in=length, ring_gauge=ring, image_url=img.group(1) if img else None))
    if not sizes:
        return None

    body = re.search(r'cigar-body-label">(.*?)</div>', page, re.S)
    band = re.search(r'<img[^>]+src="([^"]+)"[^>]+class="brand-logo desktop-brand-logo"', page) \
        or re.search(r'<img[^>]+class="brand-logo desktop-brand-logo"[^>]+src="([^"]+)"', page)

    return LineRecord(
        brand=brand, line=line, source_url=url,
        wrapper_raw=clean_value(_svg_value(page, "WRAPPER")), binder=clean_value(_svg_value(page, "BINDER")), filler=clean_value(_svg_value(page, "FILLER")),
        body=_text(body.group(1)) if body else None,
        band_image_url=band.group(1) if band else None,
        vitolas=sizes,
    )
