"""bluerunspirits.com (Blue Run Spirits, Lexington — the whiskey is contract distilled at Castle & Key, so
the family stays Blue Run Spirits, not Castle & Key). Drupal; the sitemap lists nine /whiskey(s)/... pages
(one /whiskey/ page, Blueprint, sits outside the /whiskeys/ tree). Every page prints "Proof: | 111.0 |
750ml" in a fixed block, and the bottle photo is the first `typeof="foaf:Image"` <img> (og:image is
empty). Two traps: the limited-releases slug `bourboon-rye-whiskeys` is actually the Glimmer gin-barrel
bourbon (the h1 says so, the slug is a leftover), and `flight-series-iii` is one page carrying six
bottlings, each with its own Proof block and a `BRS-Listing-Thumbnail-FIII-<Name>.png` thumbnail, so it
yields six records. No page states an age or a mash bill (Trifecta's "six-year-old base" is one component
of a blend, not an age statement). tasting_notes is the bottling's own "Tasting Notes" block (01 Nose / 02 Palate /
03 Finish; on the Flight Series III page each of the six has its own block after its Proof line)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Blue Run Spirits"
DELAY = 6
SITEMAP = "https://www.bluerunspirits.com/sitemap.xml"
IMAGE_PREFIX = "https://www.bluerunspirits.com/"
CATALOG_FAMILIES = ["Blue Run"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class)
BOURBON = "Kentucky Straight Bourbon Whiskey"
RYE = "Kentucky Straight Rye Whiskey"
REFILE = {
    "blue-run-blueprint-series-kentucky-straight-bourbon-whiskey": ("Blueprint Series", [], BOURBON),
    "emerald-1": ("Emerald I Rye", ["Blue Run Emerald Rye"], RYE),
    "emerald-ii-kentucky-straight-rye-whiskey": ("Emerald II Rye", [], RYE),
    "kentucky-straight-high-rye-bourbon": ("High Rye", ["Blue Run High Rye Bourbon"], BOURBON),
    "reflection-i-kentucky-straight-bourbon": ("Reflection I", ["Blue Run Reflection 1", "Blue Run Reflection I Bourbon"], BOURBON),
    "reflection-ii-kentucky-straight-bourbon": ("Reflection II", ["Blue Run Reflection II Bourbon"], BOURBON),
    "bourboon-rye-whiskeys": ("Glimmer Gin Barrel Finish", ["Blue Run Glimmer"], BOURBON),
    "trifecta-kentucky-straight-bourbon": ("Trifecta", [], BOURBON),
}
FLIGHT_III = {  # name → class (the page's own order)
    "Beach & Blooms": BOURBON, "Buck & Brush": BOURBON, "Filly & Fiddle": BOURBON,
    "Fit & Flair": BOURBON, "Sails & Rails": BOURBON, "Sun & Salt": BOURBON,
}
CORE = {"Blueprint Series", "Emerald I Rye", "Emerald II Rye", "High Rye", "Reflection I", "Reflection II"}
RARITY = [(r"flight series|glimmer|trifecta", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = re.findall(r"<loc>([^<]+/whiskeys?/[^<]+)</loc>", fetcher.get(SITEMAP))
    return sorted({u for u in urls if u.rstrip("/").split("/")[-1] in REFILE or u.rstrip("/").endswith("flight-series-iii")})


def _text(page: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _abs(src: str) -> str:
    return html.unescape(src) if src.startswith("http") else IMAGE_PREFIX.rstrip("/") + html.unescape(src)


def _notes(block: str) -> str | None:
    """Nose / Palate / Finish out of one "Tasting Notes" block of the `_text` form ("Nose| ... | Palate| ... | Finish| ...")."""
    parts = re.findall(r"\b(Nose|Palate|Finish)\|\s*([^|]+)", block)
    t = " ".join(f"{k}: {v.strip()}" for k, v in parts if v.strip())
    t = t.replace("\u200d", "").replace("\u200b", "")
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:900].rsplit(" ", 1)[0] if len(t) > 900 else t) or None


def parse(url: str, page: str):
    slug = url.rstrip("/").split("/")[-1]
    text = _text(page)
    if slug == "flight-series-iii":
        out = []
        for name, class_raw in FLIGHT_III.items():
            m = re.search(re.escape(name) + r"\s*\|\s*Proof:\|\s*(\d{2,3}(?:\.\d+)?)", text)
            key = name.replace("&", "and").replace(" ", "")
            img = re.search(r'src="([^"]*Thumbnail-FIII-%s[^"]*)"' % re.escape(key), page)
            nm = re.search(re.escape(name) + r"\s*\|\s*Proof:.*?Tasting Notes(.*?)(?:Find a Retailer|Catch a butterfly|$)", text, re.S | re.I)
            out.append(BottlingRecord(
                brand_family="Blue Run", expression=f"Flight Series III: {name}", name=f"Blue Run Flight Series III: {name}",
                source_url=url, proof=float(m.group(1)) if m else None, class_raw=class_raw,
                tasting_notes=_notes(nm.group(1)) if nm else None, image_url=_abs(img.group(1)) if img else None,
                aliases=[], is_core_range=False,
            ))
        return out
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"Blue Run {expression}"
    start = text.find("‹‹")
    own = text[start:text.find("Tasting Notes", start)] if start >= 0 else text
    m = re.search(r"Proof:\|\s*(\d{2,3}(?:\.\d+)?)", own)
    img = re.search(r'<img[^>]*src="([^"]+)"[^>]*typeof="foaf:Image"', page)
    nm = re.search(r"Tasting Notes(.*?)(?:Catch a butterfly|Find Blue Run Spirits|$)", text[start:] if start >= 0 else text, re.S)
    desc = re.sub(r"\s*\|\s*", " ", own.split("Small-Batch Whiskey", 1)[-1].split("Proof:")[0]).strip() or None
    return BottlingRecord(
        brand_family="Blue Run", expression=expression, name=name, source_url=url,
        proof=float(m.group(1)) if m else None, class_raw=class_raw,
        description=desc[:600] if desc else None, tasting_notes=_notes(nm.group(1)) if nm else None, image_url=_abs(img.group(1)) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
