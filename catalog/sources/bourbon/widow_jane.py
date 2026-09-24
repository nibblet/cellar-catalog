"""widowjane.com (Cacao Prieto, Brooklyn — a bottler, not a distiller; the age and proof are the maker's
own statement of what it sources and blends). One WordPress page per bottling under /whiskey/<slug>/: an
h1 name, then a run of tag pills — "AGED N YEARS", "M PROOF N.N% ALC/VOL", a class/finish tag ("Bourbon",
"Rye Whiskey", "Maple Barrel Finish", "Mizunara Oak") — and a bottle shot as the first
`attachment-post-thumbnail` image. Paradigm Rye states no age. The whole lineup is bourbon or rye; a page
that doesn't say "Rye Whiskey" is bourbon."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Widow Jane"
DELAY = 6
SITEMAP = "https://widowjane.com/whiskey-sitemap.xml"
IMAGE_PREFIX = "https://widowjane.com/"
CATALOG_FAMILIES = ["Widow Jane"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases).
REFILE = {
    "10-year-bourbon": ("10 Year", []),
    "baby-jane-bourbon": ("Baby Jane", []),
    "decadence": ("Decadence", []),
    "lucky-thirteen": ("Lucky Thirteen", []),
    "paradigm-rye": ("Paradigm Rye", []),
    "black-opal": ("Black Opal", ["Widow Jane Black Opal 20 Year"]),
    "the-vaults": ("The Vaults", ["Widow Jane The Vaults 15 Year"]),
    "apple-wood-aged-rye": ("Apple Wood Aged Rye", []),
    "tequila-ocho-cask-finish": ("Tequila Ocho Cask Finish", []),
    "borough-blend": ("Borough Blend", ["Widow Jane 10 Year Borough Blend"]),
}
NOT_CORE = re.compile(r"black opal|the vaults|tequila ocho|borough blend|lucky thirteen", re.I)
RARITY = [(r"black opal|the vaults", "unicorn"), (r"tequila ocho|borough blend|lucky thirteen", "lottery"),
          (r"baby jane|apple wood", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted({u for u in re.findall(r"<loc>(https://widowjane\.com/whiskey/[a-z0-9-]+/)</loc>", fetcher.get(SITEMAP))})


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Widow Jane {expression}"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = flat.split("| Shop|", 1)[-1][:2000]
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?) PROOF\b", own)
    pf = float(m.group(1)) if m else None
    years, label = age(own[:400])
    if years is None and label is None:
        years, label = age(name)
    rye = bool(re.search(r"Rye Whiskey", own[:400]))
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Straight Bourbon Whiskey"
    tag = re.search(r"ALC/VOL\|\s*([^|]+)", own)
    finish = None
    if tag and re.search(r"finish|oak\b", tag.group(1), re.I) and "whiskey" not in tag.group(1).lower():
        finish = tag.group(1).strip().title()
    desc = _text((re.search(r"ALC/VOL\|\s*(?:[^|]+\|\s*)?([^|]{40,500})", own) or [None, None])[1])
    img = (re.search(r'<img[^>]+src="([^"]+)"[^>]*class="attachment-post-thumbnail', page) or [None, None])[1]
    return BottlingRecord(
        brand_family="Widow Jane", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style="rye" if rye else None, description=desc,
        image_url=html.unescape(img) if img else None, finish=finish,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
