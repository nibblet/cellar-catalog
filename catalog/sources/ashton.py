"""ashtoncigar.com and laaromadecuba.com — Ashton Distributors' two open brands (both classic
Drupal 7, same template). Each line page's shape chart carries size data as
data-dimensions='LxR' data-shapename='Name' pairs (more reliable than the page's own visible
text, which prints some names in lowercase — e.g. La Aroma de Cuba Noblesse); a Product Details
block gives Strength / Country / Wrapper. Neither site states binder or filler as a fact, but the
line's own prose usually names them ("a blend of Dominican binder and filler tobaccos").

A third Ashton Distributors brand, San Cristobal, now lives on sancristobalcigar.com behind a
Drupal 11 rebuild; that site 403s any non-browser User-Agent (including this crawler's honest,
contactable one) even before its age gate, so it is left out — same call as AJ Fernandez."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 10  # both sites' robots.txt ask for 10s
SITEMAP = "https://ashtoncigar.com/sitemap.xml"  # only for IMAGE_PREFIX derivation in scripts
IMAGE_PREFIX = "https://www.ashtoncigar.com/"  # La Aroma de Cuba's laaromadecuba.com images get a second, manual product_images insert

# sitemap.xml and the nav each miss lines the other has, so both are hand-merged here. Samplers
# and the brand-history/our-craft pages carry no product data.
ASHTON_LINES = [
    "ashton", "ashton-aged-maduro", "ashton-cabinet-selection", "ashton-esquire",
    "ashton-estate-sun-grown", "ashton-heritage-puro-sol", "ashton-small-cigars",
    "ashton-symmetry", "ashton-vsg", "small-cigars-connecticut",
]
# "la-aroma-de-cuba-mi-amor-reserva" is dropped: the page's own <link rel="canonical"> points at
# "la-aroma-de-cuba-reserva" — an old URL for the same line, not a separate one.
LAAC_LINES = [
    "la-aroma-de-cuba", "la-aroma-de-cuba-connecticut", "la-aroma-de-cuba-edicion-especial",
    "la-aroma-de-cuba-habano-reserve", "la-aroma-de-cuba-mi-amor",
    "la-aroma-de-cuba-noblesse", "la-aroma-de-cuba-pasion", "la-aroma-de-cuba-reserva",
    "la-aroma-de-cuba-small-batch",
]
BRAND_BY_HOST = {"ashtoncigar.com": "Ashton", "laaromadecuba.com": "La Aroma de Cuba"}
# CURATED, not maker text: Ashton's two small-format lines don't state a country. Every other
# Ashton line does, and all of them are Dominican Republic (the prose here names Dominican and/or
# Cameroon fillers, not a rolling country, so it isn't read as one).
NO_COUNTRY_DEFAULT = {"ashton-small-cigars": "Dominican Republic", "small-cigars-connecticut": "Dominican Republic"}


def list_urls(fetcher) -> list[str]:
    return ([f"https://ashtoncigar.com/cigars/ashton/{s}" for s in ASHTON_LINES] +
            [f"https://laaromadecuba.com/cigars/la-aroma-de-cuba-cigars/{s}" for s in LAAC_LINES])


def _text(fragment: str) -> str:
    t = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))
    return re.sub(r"\s+", " ", t).strip()


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


LABELS = ("Strength", "Country", "Wrapper", "Tasting Notes", "Accolades", "Available Sizes")


def _size_name(raw: str) -> str:
    """data-shapename is properly cased almost everywhere, but La Aroma de Cuba Noblesse's are
    all lowercase ("regency", not "Regency") — a site bug, not a maker naming choice."""
    name = _text(raw)
    return name.title() if name.islower() else name


def _facts(lines: list[str]) -> dict[str, str]:
    facts: dict[str, str] = {}
    i = 0
    while i < len(lines):
        if lines[i].rstrip(":") in LABELS:
            label = lines[i].rstrip(":")
            if i + 1 < len(lines) and lines[i + 1].rstrip(":") not in LABELS:
                facts[label] = lines[i + 1]
            i += 2
        else:
            i += 1
    return facts


def _blend(text: str) -> tuple[str | None, str | None]:
    """The Product Details block never states binder or filler, but the line's own description
    usually names one or both: "a blend of Dominican binder and filler tobaccos" (one origin
    shared by both), "Dominican fillers and Cameroon binders" (one each), or just "Nicaraguan
    long-filler tobaccos" (filler only, the maker's copy never names a binder for these lines)."""
    m = re.search(r"([A-Z][a-zA-Z]+)\s+binders?\s+and\s+fillers?", text)
    if m:
        return m.group(1), m.group(1)
    binder = re.search(r"([A-Z][a-zA-Z]+)\s+binders?\b", text)
    filler = re.search(r"([A-Z][a-zA-Z]+)\s+(?:long-)?fillers?\b", text)
    return (binder.group(1) if binder else None), (filler.group(1) if filler else None)


def parse(url: str, page: str) -> LineRecord | list[LineRecord] | None:
    host = url.split("/")[2].replace("www.", "")
    brand = BRAND_BY_HOST.get(host)
    if not brand:
        return None
    slug = url.rstrip("/").split("/")[-1]
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    line = _text(h1.group(1)) if h1 else None
    if not line:
        return None
    line = re.sub(rf"^{re.escape(brand)}\s+", "", line, flags=re.I).strip()
    if line.lower() == brand.lower():
        line = None  # the flagship page just repeats the brand name
    sizes = [Vitola(name=_size_name(name), length_in=L, ring_gauge=R)
             for L_txt, name in re.findall(r"data-dimensions='([^']*)'\s+data-shapename='([^']*)'", page)
             for L, R in [dimensions(L_txt.replace("x", " x "))] if L and R]
    if not sizes:
        return None
    lines = _lines(page)
    facts = _facts(lines)
    # the description paragraph sits either just before or just after the "Product
    # Details" heading, depending on the template (Ashton vs. La Aroma de Cuba) -
    # search both windows rather than assume a direction.
    pd = lines.index("Product Details") if "Product Details" in lines else len(lines)
    end = next((i for i in range(pd + 1, len(lines)) if lines[i].rstrip(":") in LABELS), len(lines))
    desc = " ".join(lines[:pd]) + " " + " ".join(lines[pd + 1:end])
    binder, filler = _blend(desc)
    body = facts.get("Strength")
    country = facts.get("Country") or NO_COUNTRY_DEFAULT.get(slug)
    box = bool(re.search(r"box[- ]?press", " ".join(lines), re.I)) or None
    og = re.search(r'(?:property|name)="og:image" content="([^"]+)"', page)
    image = og.group(1) if og else None
    wrapper = facts.get("Wrapper")

    variants = re.findall(r"([^,]+?)\s*\(([^)]+)\)", wrapper or "")
    if len(variants) > 1 and len(sizes) == len(variants):
        # a size sold in more than one wrapper (Ashton Esquire: Natural and Maduro, same dims):
        # one row per variant, the variant word appended so the two don't collide on name
        records = []
        for (w, tag), v in zip(variants, sizes):
            records.append(LineRecord(brand=brand, line=line, source_url=url, wrapper_raw=w.strip(), binder=binder,
                                      filler=filler, body=body, band_image_url=image, country=country, box_pressed=box,
                                      vitolas=[Vitola(name=f"{v.name} {tag.strip()}", length_in=v.length_in, ring_gauge=v.ring_gauge)]))
        return records
    return LineRecord(brand=brand, line=line, source_url=url, wrapper_raw=wrapper, binder=binder, filler=filler,
                      body=body, band_image_url=image, vitolas=sizes, country=country, box_pressed=box)
