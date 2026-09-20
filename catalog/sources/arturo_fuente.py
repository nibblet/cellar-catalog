"""arturofuente.com — WordPress/Divi, one page per line under /our-cigars/. Sizes sit in a
MasterSlider: <h3><strong>Name</strong></h3><p>Length: 6" … Ring Gauge: 47 … Wrappers: (N)(M)(SG)</p>.
Figurados print two rings ("42/49"). The wrapper codes have no legend on the site; they are read
from usage: N natural, M maduro, S and SG sun grown, RSG rosado sun grown (the Chateau Fuente
"King T Rosado Sungrown" is the (S) size), C candela (the classic Fuente candela sizes).
"(D' Oro)" on three Gran Reserva sizes is not a wrapper we can name and is skipped.

Blend facts are per-line prose where the page has any. Country comes from the maker's own history
page: Tabacalera A. Fuente y Cia. in Santiago is "the manufacturer of Fuente Fuente OpusX and
Arturo Fuente cigars" (https://arturofuente.com/history/family-history/).

The Medium Filler page is one slider for six small products; two names (Cubanitos, Exquisitos)
exist only as images and are transcribed here, cited by file (cuban-txt.png, ex-text.png)."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import dimensions, shape

BRAND = "Arturo Fuente"
COUNTRY = "Dominican Republic"
DELAY = 5
SITEMAP = "https://arturofuente.com/wp-sitemap-posts-page-1.xml"
IMAGE_PREFIX = "https://arturofuente.com/"

# Page slug → catalog line (the maker's name; the OpusX family keeps its full name).
LINES = {
    "gran2": "Gran Reserva",
    "hemingway": "Hemingway",
    "chateau-fuente": "Chateau Fuente",
    "anejo": "Añejo",
    "don-carlos": "Don Carlos",
    "casa-cuba": "Casa Cuba",
    "destino-al-siglo": "Destino al Siglo",
    "magnumr": "Magnum R",
    "rare-pink": "Rare Pink",
    "ff-opusx": "Fuente Fuente OpusX",
    "oro-oscuro": "Fuente Fuente OpusX Oro Oscuro",
    "angels-share": "Fuente Fuente OpusX Angel's Share",
    "ffox-20th": "Fuente Fuente OpusX 20th Anniversary",
    "forbidden-x": "Fuente Fuente OpusX Forbidden X",
    "medium-filler": None,  # several lines; see _medium_filler
}
CODES = {"N": "Natural", "M": "Maduro", "S": "Sun Grown", "SG": "Sun Grown", "RSG": "Rosado Sun Grown", "C": "Candela"}
# The OpusX family's wrapper is the maker's own Dominican leaf ("the first ever Dominican Puro",
# "born from Chateau de la Fuente"); the pages never name the seed.
WRAPPER_BY_SLUG = {"ff-opusx": "Dominican", "angels-share": "Dominican", "ffox-20th": "Dominican", "forbidden-x": "Dominican", "oro-oscuro": "Dominican oscuro"}
BLEND_BY_SLUG = {"ff-opusx": "Dominican", "oro-oscuro": "Dominican"}  # binder and filler, from the same "Dominican Puro" statement
LEAF_WORDS = r"connecticut broadleaf|broadleaf|connecticut shade|connecticut|cameroon|sumatra|habano|havana|corojo|criollo|candela|maduro|oscuro|rosado|sun ?grown|ecuador(?:ian)?|dominican|african|nicaraguan|mexican"

# Catalog rows re-filed by hand: seed rows filed under the wrapper or a half-line, and Fuente's
# Natural/Maduro pairs assigned by the row's wrapper_shade.
OVERRIDES = {
    "b9e75506-7ea3-4a1c-b729-bcee8a4e6139": {"line": "Gran Reserva", "expression": "Flor Fina 8-5-8 Maduro"},
    "3fa9cb06-0e2b-4138-9178-90d9b8840406": {"expression": "Flor Fina 8-5-8 Natural"},                        # cameroon/colorado is the Natural
    "e2deb4ec-f744-48ce-9a20-cdfc3c444726": {"line": "Gran Reserva", "expression": "Spanish Lonsdale Natural"},
    "ea48a046-841b-4088-affc-c2be8313a531": {"expression": "No. 77 Shark"},
    "d1b2cf1b-f7b3-4398-a815-e5c6491a7fec": {"expression": "King T Natural"},                                 # the (N) King T; the (S) is "King T Rosado Sungrown"
    "03865f3f-f581-48c1-937f-fa2a4b7722b3": {"expression": "Personal Reserve - Eye of The Shark"},
    "cfa453c8-e913-44c9-b6f5-6f8ac6aaf4a1": {"expression": "Conquistadores"},
    "9d3080c1-1025-4c1d-bb50-38d1da19385a": {"line": "Fuente Fuente OpusX", "expression": "Reserva D' Chateau"},
    "81fee4d3-bf76-4886-b429-ed70fac0abd0": {"line": "Fuente Fuente OpusX", "expression": "PerfecXion No. 4 Series X"},
    "19801f6d-a9b9-4881-837f-8167ed82e11f": {"line": "Fuente Fuente OpusX", "expression": "PerfecXion X"},
    "71fe48fb-cc2f-4463-a59c-26dcb5891b89": {"line": "Magnum R", "expression": "Vitola 54"},
    "a03b8ad8-57aa-449d-b441-2fd21b6f1f90": {"expression": "Best Seller Natural"},                            # Hemingway seed rows are cameroon/colorado: the Natural
    "a9286961-47ea-478f-87be-dc901b1bdfc8": {"expression": "Classic Natural"},
    "c0345b7b-3695-4234-8eb7-7e54c5c63ba3": {"expression": "Masterpiece Natural"},
    "1631f2cb-3804-46a8-b8d8-235639215644": {"expression": "Short Story Natural"},
    "0532113d-9dc3-4122-b6df-551832c318e1": {"expression": "Work of Art Natural"},
    # left alone: "OpusX / ForbiddenX 13" (a 2013 release the site no longer lists), "Don Carlos / Sangre de Toro
    # Undefeated", "Don Carlos Edición de Aniversario / Toro", "God of Fire by Carlito" (not an Arturo Fuente line)
}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = re.findall(r"<loc>(https://arturofuente\.com/our-cigars/[^<]+/)</loc>", xml)
    return sorted(u for u in set(urls) if u.rstrip("/").split("/")[-1] in LINES)


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").strip()


def _name(raw: str) -> str:
    n = re.sub(r"\s+", " ", _text(raw)).replace("®", "").strip()
    return re.sub(r"\bNo\.(?=\S)", "No. ", n)  # "No.77 Shark" → "No. 77 Shark"


def _wrapper_from(desc: str) -> str | None:
    words = [w for w in re.findall(LEAF_WORDS, desc, re.I)
             if re.search(rf"\b{re.escape(w)}\b[^.]{{0,50}}wrapp|wrapp[^.]{{0,50}}\b{re.escape(w)}\b", desc, re.I)]
    return " ".join(dict.fromkeys(w.lower() for w in words)) or None


def _desc(page: str) -> str:
    """The line's prose: MasterSlider text layers and paragraphs, minus the cookie dialog and size blocks."""
    body = page[: page.find("Cookie Consent")] if "Cookie Consent" in page else page
    paras = [_text(p) for p in re.findall(r'<div\s+class="ms-layer[^"]*"[^>]*>(.*?)</div>|<p(?:\s[^>]*)?>(.*?)</p>', body, re.S) for p in p if p]
    return " ".join(p for p in paras if len(p) > 100 and "Length:" not in p)[:4000]


def _sizes(page: str):
    """Yield (name, length, ring, codes, image) for every slide with a size block."""
    for slide in re.split(r'<div\s+class="ms-slide"', page)[1:]:
        m = re.search(r"<h3[^>]*>\s*<strong>(.*?)</strong>\s*</h3>\s*<p(?:\s[^>]*)?>(.*?)</p>", slide, re.S)
        if not m:
            continue
        body = _text(m.group(2))
        L = re.search(r"Length:\s*([\d.]+)", body)
        R = re.search(r"Ring Gauge:\s*([\d/]+)", body)
        if not (L and R):
            continue
        codes = re.findall(r"\(([^)]+)\)", (re.search(r"Wrappers:\s*(.*)$", body) or [None, ""])[1] if "Wrappers:" in body else "")
        img = re.search(r'data-src="([^"]+)"', slide)
        yield _name(m.group(1)), float(L.group(1)), max(int(r) for r in R.group(1).split("/")), [c.strip() for c in codes], (img.group(1) if img else None), "/" in R.group(1)


def _record(line, url, sizes, wrapper_raw, desc, **extra) -> LineRecord:
    return LineRecord(brand=BRAND, line=line, source_url=url, wrapper_raw=wrapper_raw, vitolas=sizes, country=COUNTRY,
                      body=(lambda m: m.group(1).title() if m else None)(re.search(r"\b(mild to medium|medium to full|mild|medium|full)[- ]bod", desc, re.I)), **extra)


def _vitola(name, L, R, img, tapered, perfectos=False) -> Vitola:
    shp = "torpedo" if "shark" in name.lower() else shape(name)[0]  # the No. 77 "Shark" is Fuente's torpedo
    if tapered and shp == "parejo":
        shp = "perfecto" if perfectos else "figurado"  # two rings printed: it tapers; only the page says how
    return Vitola(name=name, length_in=L, ring_gauge=R, image_url=img, shape=shp if (tapered or "shark" in name.lower()) else None)


def parse(url: str, page: str):
    slug = url.rstrip("/").split("/")[-1]
    if slug not in LINES:
        return None
    if slug == "medium-filler":
        return _medium_filler(url, page)
    line = LINES[slug]
    desc = _desc(page)
    wrapper_raw = WRAPPER_BY_SLUG.get(slug) or _wrapper_from(desc)
    blend = BLEND_BY_SLUG.get(slug)
    if slug == "casa-cuba":
        blend = "Cuban-seed Dominican"  # "a mix of Cuban-seed Dominican grown long filler and binder"
    by_variant: dict[str | None, list[Vitola]] = {}
    for name, L, R, codes, img, tapered in _sizes(page):
        variants = [CODES[c] for c in codes if c in CODES] if codes else [None]
        for v in dict.fromkeys(variants):
            # "King T Rosado Sungrown (S)": the name already says it
            full = name if v is None or v.lower().replace(" ", "") in name.lower().replace(" ", "") else f"{name} {v}"
            by_variant.setdefault(v, []).append(_vitola(full, L, R, img, tapered, perfectos="perfecto" in desc.lower()))
    if not by_variant:
        return None
    recs = []
    for v, sizes in by_variant.items():
        raw = " ".join(x for x in (wrapper_raw, v.lower() if v else None) if x) or None
        recs.append(_record(line, url, sizes, raw, desc, binder=blend, filler=blend))
    return recs


# The Medium Filler slider, in order. Names in images are transcribed (file cited).
MEDIUM_FILLER = [
    ("Cubanitos", "cuban-txt.png"),        # slide1: tin of 10, 4 1/2 x 32
    ("Brevas Royales", None),              # slide2: named in the text
    ("Especiales", None),                  # slide3: three named sizes
    ("Exquisitos", "ex-text.png"),         # slide4: Gran Reserva blend minis, natural and maduro
    ("Curly Head", None),                  # slide5: two named products
]


def _medium_filler(url: str, page: str):
    recs = []
    slides = [s for s in re.split(r'<div\s+class="ms-slide"', page)[1:] if "Length (inches)" in s]
    for (line, _), slide in zip(MEDIUM_FILLER, slides):
        text = re.sub(r"\s+", " ", _text(re.sub(r"</p>", " | ", slide)))
        img = re.search(r'data-src="([^"]+)"', slide)
        blocks = re.findall(r"(?:\|\s*([A-Z][A-Za-z ]{2,30}?)\s+)?Length \(inches\):\s*([\d /]+?)\s*Ring Gauge:\s*(\d+)", text)
        if line == "Curly Head":  # each product's name opens its own paragraph
            blocks = [(n, l, r) for (n, l, r) in zip(re.findall(r"(?:>|\|)\s*(Curly Head(?: Deluxe)?)\s", text), [b[1] for b in blocks], [b[2] for b in blocks])]
        desc = text
        wrapper_raw = _wrapper_from(desc)
        if line == "Especiales":
            sizes = [_vitola(n.strip(), dimensions(f"{l} x {r}")[0], int(r), img and img.group(1), False) for n, l, r in blocks]
            recs.append(_record(line, url, sizes, wrapper_raw, desc, filler="Dominican"))  # "a blend of aged Dominican tobaccos"
        elif line == "Curly Head":
            for n, l, r in blocks:
                recs.append(_record(n.strip(), url, [_vitola(n.strip(), dimensions(f"{l} x {r}")[0], int(r), img and img.group(1), False)], wrapper_raw, desc))
        elif line == "Exquisitos":
            l, r = blocks[0][1], blocks[0][2]
            for v in ("Natural", "Maduro"):  # "Available in Natural and Maduro"
                recs.append(_record(line, url, [_vitola(f"{line} {v}", dimensions(f"{l} x {r}")[0], int(r), img and img.group(1), False)], v.lower(), desc))
        else:
            l, r = blocks[0][1], blocks[0][2]
            recs.append(_record(line, url, [_vitola(line, dimensions(f"{l} x {r}")[0], int(r), img and img.group(1), False)], wrapper_raw, desc))
    return recs
