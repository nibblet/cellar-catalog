"""fourrosesbourbon.com — Next.js. One page per bottling under /bourbon/<slug>; the facts sit in one
line, "90 Proof / Aged 6 - 7 Years", and the bottle shot is the second /images/bourbons/ file the page
renders (a background comes first). Recipe single barrels (OBSV, OESK…) are releases of Single Barrel; each year's
Limited Edition Small Batch is a release of the one Limited Edition Small Batch bottling (the newest
year supplies its facts); Al Young 50th, Anthology and Experimental releases keep their own names."""
from __future__ import annotations

import html
import re
from urllib.parse import unquote, urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof, titlecase

PRODUCER = "Four Roses"
DELAY = 5
SITEMAP = "https://www.fourrosesbourbon.com/sitemaps-1-section-bourbons-1-sitemap.xml"
IMAGE_PREFIX = "https://four-roses.files.svdcdn.com/"
CATALOG_FAMILIES = ["Four Roses"]

REFILE = {
    "four-roses-bourbon": ("Four Roses", "Yellow Label", ["Four Roses Bourbon", "Four Roses Kentucky Straight Bourbon"]),
    "small-batch": ("Four Roses", "Small Batch", []),
    "small-batch-select": ("Four Roses", "Small Batch Select", []),
    "single-barrel": ("Four Roses", "Single Barrel", ["Four Roses Single Barrel OBSV"]),
    "2017-al-young-50th-anniversary": ("Four Roses", "Al Young 50th Anniversary", ["Four Roses 2017 Al Young 50th Anniversary"]),
    "chapter-1-origin": ("Four Roses", "Anthology Collection Chapter 1: Origin", ["Four Roses Chapter 1 Origin"]),
    "mizunara-cask-finish": ("Four Roses", "Experimental Series: Mizunara Cask Finish", ["Four Roses Experimental Series 001: Mizunara Finish", "Four Roses Mizunara Cask Finish"]),
    "honey-cask-finish": ("Four Roses", "Experimental Series: Honey Cask Finish", ["Four Roses Honey Cask Finish"]),
}
SINGLE_BARREL_RECIPE = re.compile(r"^single-barrel-o[be]s[vkoqf]$")
LIMITED_EDITION = re.compile(r"^\d{4}-(?:le|limited-edition|135th-limited-edition)(?:-small-batch)?$")
NOT_CORE = re.compile(r"limited edition|anniversary|anthology|experimental", re.I)
RARITY = [(r"limited edition|anniversary|anthology", "lottery"), (r"experimental", "allocated"), (r"small batch select", "limited"), (r".", "shelf")]
MASH_BILLS = {}
PRODUCER_BY_FAMILY = {}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(set(re.findall(r"<loc>(https://www\.fourrosesbourbon\.com/bourbon/[^<]+)</loc>", xml)))


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    h1 = _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat)
    m = re.search(r"(\d{2,3}(?:\.\d+)?) Proof / Aged ([^|]+)\|", flat)  # the first is the page's own; siblings follow "View details for"
    if not m or not h1:
        return None
    pf = float(m.group(1))
    age_raw = m.group(2).strip()
    rng = re.match(r"(?:Minimum )?(\d{1,2})\s*-\s*(\d{1,2}) years", age_raw, re.I)
    if rng:
        years, label = None, f"{rng.group(1)}–{rng.group(2)} yr"
    elif re.match(r"Minimum (\d{1,2}) years", age_raw, re.I):
        years, label = float(re.match(r"Minimum (\d{1,2})", age_raw, re.I).group(1)), f"{re.match(r'Minimum (\d{1,2})', age_raw, re.I).group(1)} yr"
    elif re.search(r"&|and", age_raw):
        years, label = None, re.sub(r"\s*years?", " yr", age_raw)  # "13 & 19 years": a blend, no single number
    else:
        years, label = age("aged " + age_raw)
    if slug in REFILE:
        family, expression, aliases = REFILE[slug]
    elif SINGLE_BARREL_RECIPE.match(slug):
        family, expression, aliases = "Four Roses", "Single Barrel", [f"Four Roses {h1}"]
    elif LIMITED_EDITION.match(slug):
        family, expression, aliases = "Four Roses", "Limited Edition Small Batch", [f"Four Roses {h1}", "Four Roses Limited Edition Small Batch " + slug[:4]]
    else:
        family, expression, aliases = "Four Roses", titlecase(h1), []
    name = f"{family} {expression}"
    # The page renders a background, then the bottle, then both again: the bottle is the second bourbons image.
    shots = []
    for src in re.findall(r'<img[^>]+src="([^"]+)"', page):
        mm = re.search(r"(https://four-roses\.files\.svdcdn\.com/production/images/bourbons/[^&?]+)", unquote(src))
        if mm:
            shots.append(mm.group(1))
    img = shots[1] if len(shots) > 1 else None
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw="Kentucky Straight Bourbon Whiskey", mash_raw=None, mash_style=None, description=None, image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
