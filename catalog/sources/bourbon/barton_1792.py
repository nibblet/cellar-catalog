"""1792bourbon.com — Barton 1792 Distillery (Sazerac). A static site with one page per expression under
the root (/high-rye, /full-proof…); each has a paragraph of copy, tasting notes and a straight-on
bottle shot in /img/. The pages rarely state a proof: the flagship Small Batch's is the legal line in
the footer ("46.85% Alc / Abv. 93.7 Proof"), Full Proof is "bottled at its original 125 barrel entry
proof" (the one case where entry proof is the bottling proof), Bottled in Bond is 100 by law. The
rest keep whatever proof the catalog holds. There is no Small Batch page; /our-bourbon stands for it."""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin, urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Barton 1792"
DELAY = 5
SITEMAP = "https://1792bourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://1792bourbon.com/"
CATALOG_FAMILIES = ["1792"]

# slug → (expression, aliases). Every page is a 1792.
PAGES = {
    "our-bourbon": ("Small Batch", ["1792 Small Batch Bourbon", "1792 Ridgemont Reserve", "1792 Bourbon"]),
    "sweet-wheat": ("Sweet Wheat", []),
    "aged-twelve-years": ("12 Year", ["1792 Aged Twelve Years", "1792 12 Year Old"]),
    "high-rye": ("High Rye", []),
    "single-barrel": ("Single Barrel", []),
    "full-proof": ("Full Proof", []),
    "bottled-in-bond": ("Bottled in Bond", ["1792 Bottled-in-Bond"]),
    "port-finish": ("Port Finish", []),
}
NOT_CORE = re.compile(r"12 year|port finish|sweet wheat", re.I)
RARITY = [(r"12 year", "lottery"), (r"full proof|port finish|sweet wheat|bottled in bond", "allocated"), (r"single barrel|high rye", "limited"), (r".", "shelf")]
MASH_BILLS = {}
PRODUCER_BY_FAMILY = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://1792bourbon.com/{slug}" for slug in PAGES]


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.strip("/")
    expression, aliases = PAGES[slug]
    name = f"1792 {expression}"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat)
    copy = flat.split("TASTING NOTES")[0].split("Buy Online")[-1] if "TASTING NOTES" in flat else ""
    notes = (re.search(r"TASTING NOTES\|?\s*(.*?)\|", flat) or [None, ""])[1]
    pf = None
    if slug == "our-bourbon":
        m = re.search(r"(\d{2,3}(?:\.\d+)?) Proof", flat)  # the footer's legal line is the flagship's
        pf = float(m.group(1)) if m else None
    elif slug == "full-proof":
        m = re.search(r"(\d{3}) barrel entry proof", copy)
        pf = float(m.group(1)) if m else None
    elif slug == "bottled-in-bond":
        pf = 100.0  # by statute
    else:
        m = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b|bottled at (\d{2,3}(?:\.\d+)?)", copy, re.I)
        pf = float(next(g for g in m.groups() if g)) if m else None
    years, label = age(copy) if copy else (None, None)
    if years is None and label is None:
        years, label = age(expression)
    img = next((urljoin(url, src) for src in re.findall(r'<img[^>]+src="([^"]+)"', page) if re.search(r"Bottle", src)), None)
    class_raw = "Kentucky Straight Bourbon Whiskey" + (" Bottled-in-Bond" if slug == "bottled-in-bond" else "")
    mash = "wheated" if slug == "sweet-wheat" else "high_rye" if slug == "high-rye" else None
    return BottlingRecord(
        brand_family="1792", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=_text(copy), tasting_notes=_text(notes), image_url=img,
        finish="Port Casks" if slug == "port-finish" else None, aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
