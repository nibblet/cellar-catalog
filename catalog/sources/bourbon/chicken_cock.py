"""chickencockwhiskey.com (Chicken Cock Whiskey, a pre-Prohibition brand revived by Grain & Barrel
Spirits — collaboratively distilled, aged and blended at Bardstown Bourbon Company, not self-distilled).
WordPress; a spoofed desktop-Chrome User-Agent gets a 403 from the host's WAF, a plain/custom one doesn't
(`catalog.fetch`'s own identifying UA is well clear of this). The newer core lineup carries a clean
"PROOF: | AGE: | MASHBILL: | CHAR/TOAST:" block with spelled-out grain words, no abbreviation legend
needed; several limited releases (Chanticleer, the 15 Year, 20 Year Cotton Club Rye) predate that layout
and only state proof inline ("750ML | 51.5% ABV | 103 PROOF"), with no age or mash bill field at all —
the age is trusted from the product's own name where it states one plainly ("15 Year", "20 Year Old").
Two limited pages (Chanticleer, 20 Year Cotton Club Rye) show "Bottles Remaining | 0" — sold out, but
still the maker's own current statement of the bottling's specs, same as any other confirmed row.
Eight one-off retailer single-barrel selections (Field Ethos, Garden Gun, Ampal, Criquet, the New Orleans
Bourbon Festival cask, Miller's Reserve, Ryeteous Blonde) and a private-cask program page are not
crawled — too many one-off store picks to be "most available", the same call made for other makers'
single-barrel programs.

`tasting_notes` is the "Tasting Notes" panel (Nose or Aroma / Palate / Finish lines) that follows the price; it stops at the
first line that is not a label and its value, so the review form and customers' reviews after it are never read. Old Glory
and the 15 Year print the heading with no notes under it and keep none."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Chicken Cock"
DELAY = 6
SITEMAP = "https://chickencockwhiskey.com/whiskey-sitemap.xml"
IMAGE_PREFIX = "https://chickencockwhiskey.com/"
CATALOG_FAMILIES = ["Chicken Cock"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases). expression None is the plain "Chicken Cock" flagship.
REFILE = {
    "kentucky-straight-bourbon-whiskey": (None, []),
    "kentucky-straight-rye-whiskey": ("Rye", []),
    "double-oak-kentucky-whiskey": ("Double Oak", []),
    "small-batch": ("Small Batch", []),
    "wheated-bourbon": ("Wheated Bourbon", []),
    "old-glory": ("Old Glory", []),
    "chanticleer": ("Chanticleer", []),
    "15-year-kentucky-straight-bourbon": ("15 Year", ["Chicken Cock Barrel Proof 15 Year"]),
    "20-year-old-cotton-club-rye": ("Cotton Club", ["Chicken Cock Cotton Club"]),
    "mizunara": ("Mizunara", []),
    "red-stave": ("Red Stave", []),
    "island-rooster": ("Island Rooster", []),
}
RYE_SLUGS = {"kentucky-straight-rye-whiskey", "20-year-old-cotton-club-rye", "island-rooster"}
CORE = {None, "Rye", "Small Batch", "Wheated Bourbon"}
RARITY = [(r"15 year|cotton club|chanticleer", "unicorn"), (r"mizunara|red stave|island rooster|old glory", "lottery"),
          (r"double oak", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://chickencockwhiskey.com/whiskey/{slug}/" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


_NOTE_LABELS = {"nose", "aroma", "palate", "taste", "finish"}


def _tasting(own: str) -> str | None:
    segs = [x.strip() for x in own.split("|") if x.strip()]
    start = next((i for i, x in enumerate(segs) if x == "Tasting Notes"), None)
    if start is None:
        return None
    parts, j = [], start + 1
    while j + 1 < len(segs) and segs[j].lower() in _NOTE_LABELS:
        value = re.sub(r"\bavors\b", "flavors", re.sub(r"\bnish\b", "finish", segs[j + 1]))  # the Red Stave page lost its fi/fl ligatures
        parts.append(f"{segs[j].title()}: {value.rstrip('. ')}.")
        j += 2
    return " ".join(parts)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Chicken Cock {expression}" if expression else "Chicken Cock"

    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)

    pm = re.search(r"PROOF:\|\s*(\d{2,3}(?:\.\d+)?)", own) or re.search(r"\|\s*(\d{2,3}(?:\.\d+)?)\s*PROOF\b", own, re.I)
    proof = float(pm.group(1)) if pm else None

    am = re.search(r"AGE:\|\s*([^|]+)", own)
    years, label = age(am.group(1)) if am else (None, None)
    if years is None and label is None:
        years, label = age(slug.replace("-", " "))  # "15-year-..." / "20-year-old-..." when the page has no AGE: field

    mm = re.search(r"MASHBILL:\|\s*([^|]+)", own)
    mash_raw = mm.group(1).strip() if mm else None

    rye = slug in RYE_SLUGS
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]

    desc = _text(own.split("Tasting Notes", 1)[0][-600:])

    return BottlingRecord(
        brand_family="Chicken Cock", expression=expression, name=name,
        source_url=f"https://chickencockwhiskey.com/whiskey/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style="rye" if rye else None, description=desc, tasting_notes=_tasting(own),
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
