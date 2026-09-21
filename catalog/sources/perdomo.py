"""perdomocigars.com — Squarespace, one page per line with a section per wrapper (Connecticut /
Sun Grown / Maduro …). Each section states wrapper, binder, filler, Strength and a sizes list of
"Name • L x R". Country is company-wide: The Perdomo Way page says the manufacturing facilities are
in Estelí, Nicaragua, and the line pages call their blends Nicaraguan puros."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5
SITE = "https://www.perdomocigars.com"
SITEMAP = SITE + "/sitemap.xml"  # the sitemap mixes drafts, galleries and duplicates; the nav's line pages are listed here
IMAGE_PREFIX = "https://static1.squarespace.com/"  # the pages' og:image, served over https
BRAND = "Perdomo"
COUNTRY = "Nicaragua"  # https://www.perdomocigars.com/the-perdomo-way
# The nav's line pages. Estate Seleccion Vintage, Small Batch Series, Special Craft Series, Factory Tour
# Blend and Nick's Sticks have gallery pages only (sizes in images), so they can't be imported.
LINES = {
    "legacy": "Legacy", "30th-anniversary": "30th Anniversary", "double-aged-12-year-vintage": "Double Aged 12 Year Vintage",
    "20th-anniversary": "20th Anniversary", "10th-anniversary": "10th Anniversary Champagne",
    "habano-bourbon-barrel-aged": "Habano Bourbon Barrel-Aged", "perdomo-lot-23": "Lot 23", "inmenso-seventy": "Inmenso Seventy",
    "perdomo-fresco": "Fresco",
}
# Catalog rows re-filed by hand. The seed put the wrapper in the line ("Lot 23 Maduro"); the maker's page
# is one line with a section per wrapper, so the wrapper moves into the size name ("Maduro Robusto").
OVERRIDES = {
    "23989b4f-6bd8-478f-aa4f-a6584b014058": {"line": "Lot 23", "expression": "Sun Grown Robusto"},      # "Natural" is the page's Sun Grown
    "77cebcea-396a-453c-9790-c8f76938989b": {"line": "Lot 23", "expression": "Sun Grown Toro"},
    "00adfd70-eb68-4d3a-b601-29921213b8e0": {"expression": "Connecticut Robusto"},                     # seed dims 6 x 50 were the Toro's
    "fa8f7f6e-dac3-4386-8e6a-7c58053c7b02": {"expression": "Sun Grown Robusto"},                       # seed said Habano, colorado: the Sun Grown
    "6814efde-0a82-480d-b3e0-a81e050bee06": {"line": "10th Anniversary Champagne", "expression": "Connecticut Robusto"},
    "b1905587-cd86-4be9-8947-a91f4a9fc14e": {"line": "10th Anniversary Champagne", "expression": "Maduro Robusto"},
    "f81c2de6-aa34-4883-946e-6e8ee314d186": {"line": "10th Anniversary Champagne", "expression": "Sun Grown Robusto"},
    # merged after apply: "Champagne Noir / Robusto" 5 x 54 is the 10th Anniversary Maduro Robusto above.
    # left alone: Estate Seleccion Vintage, Factory Tour Blend, Small Batch — gallery pages only, sizes in images
}
LABELS = ("wrapper", "binder", "filler", "strength", "finish", "taste", "pairings", "sizes")
ORIGIN_WORDS = r"^(?:ecuadorian|nicaraguan|cuban-seed|cuban seed)\s+"


def list_urls(fetcher) -> list[str]:
    return [f"{SITE}/{slug}" for slug in LINES]


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


def _sections(lines: list[str]) -> list[dict]:
    """Each run of label/value pairs starting at a 'wrapper' label is one wrapper's blend; its sizes
    follow the 'sizes' label as Name / "• L x R" pairs."""
    out, cur, label, buf, i = [], None, None, [], 0
    while i < len(lines):
        l = lines[i]
        k = l.lower()
        if k == "wrapper" and (cur is None or "sizes" in cur):
            cur = {"wrapper": "", "desc": " ".join(buf)}; out.append(cur); label = "wrapper"; buf = []
        elif cur is not None and k in LABELS:
            # Lot 23's Sun Grown section labels binder and filler "wrapper" too: take them in order
            if k == "wrapper" and "wrapper" in cur:
                k = "binder" if "binder" not in cur else "filler"
            label = k
            cur.setdefault(label, [] if label == "sizes" else "")
        elif cur is not None and label == "sizes":
            m = re.match(r"^•?\s*(\d.*)$", l)
            if m and cur["sizes"] and isinstance(cur["sizes"][-1], str):
                L, R = dimensions(m.group(1))
                name = cur["sizes"].pop()
                if L and R:
                    cur["sizes"].append((name, L, R))
            elif l == "•":
                pass
            elif re.match(r"^[A-Z][A-Za-z ]{2,24}$", l) and l not in ("Featured", "Back", "Next", "Overview", "Navigation", "Hero"):
                cur["sizes"].append(l)
            else:
                label = None  # "Featured", "Read more →", the next heading …
        elif cur is not None and label:
            if l.startswith("Read more") or l == "Featured" or re.match(r"^\d\d\. ", l):
                label = None
            else:
                cur[label] = (cur[label] + " " + l).strip()
        else:
            buf.append(l)  # the copy before a section's wrapper label describes that wrapper's blend
        i += 1
    return [s for s in out if s.get("sizes") and any(isinstance(x, tuple) for x in s["sizes"])]


def parse(url: str, page: str) -> list[LineRecord] | None:
    slug = url.rstrip("/").split("/")[-1]
    line = LINES.get(slug)
    if not line:
        return None
    lines = _lines(page)
    og = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    image = og.group(1).replace("http://", "https://") if og else None
    records = []
    for s in _sections(lines):
        box = bool(re.search(r"box[- ]?pressed", s["desc"], re.I)) or None  # 10th Anniversary presses only its Sun Grown and Maduro
        wrapper = s.get("wrapper", "")
        variant = re.sub(ORIGIN_WORDS, "", wrapper, flags=re.I).strip()  # "Ecuadorian Connecticut" → Connecticut
        body = re.sub(r"[- ]bodied$", "", s.get("strength", ""), flags=re.I).strip() or None
        sizes = [Vitola(name=f"{variant} {x[0]}", length_in=x[1], ring_gauge=x[2]) for x in s["sizes"] if isinstance(x, tuple)]
        records.append(LineRecord(brand=BRAND, line=line, source_url=url, wrapper_raw=wrapper or None, binder=s.get("binder") or None,
                                  filler=s.get("filler") or None, body=body, band_image_url=image,
                                  vitolas=sizes, country=COUNTRY, box_pressed=box))
    return records or None
