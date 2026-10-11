"""boonedistilling.com (Boone County Distilling Co., Petersburg / Boone County, Kentucky; madebyghosts.com
and the older boonecountydistilling.com redirect or lead here). WordPress + Elementor, Yoast sitemap, robots
Crawl-delay 10 (honoured). One page per bottling under /<collection>-<product>/; the "Are you of legal drinking
age?" overlay is markup in the static HTML and nothing here clicks through it.

Every product page has the same "TASTING NOTES | Proof | 90.8 | ALC/VOL 45.4%" block, so proof is read from that
block only. The page copy states a class and an age only sometimes: Small Batch Rye "aged a minimum of 5 years",
Founder's Reserve "Aged five to seven years" (a range, so it is stored as the label "5-7 yr" and never as an
age_years); the Small Batch Bourbon and Lexington Club pages state no age at all. Mash bills are never stated.

The lineup today is the distillery's own pot-still whiskey (Small Batch, Founder's Reserve, the cask-finished
Founder's Reserves, Lexington Club). The "Eighteen33" 12-year MGP-sourced bourbon the catalog seeded as the
Boone County family is not on the site anywhere (no page, no sitemap entry, no mention); third-party sites call
it discontinued but the maker's own page is not *gone* (we never saw its URL), so the two seed rows are left as
they are and show up in STALE for a human decision.

Not imported (and why):
- Single Barrel Founder's Reserve Bourbon / Rye and Single Barrel Bourbon: proof is "Cask strength" with no
  number (and it varies by barrel), so there is no statement to confirm; a program, not a fixed bottling.
- Chicory Finished Bourbon: the page says the Founder's Reserve was *infused* with chicory (flavored).
- Stadium Club Whiskey (80 proof): the page states no class and is sold as a Reds stadium-drink mixer.
- Gentleman's Cut (Stephen Curry's brand, distilled here; has its own site, gentlemanscutbourbon.com): another
  party's label with no stated class; not this family.
- Tanner's Curse Bourbon / Rye / Wheated Bourbon "Mash Recipe" pages: 120-proof unaged new make ("a clear sparkle").
- Bengals Limited Edition and America 250 pages: image-only text overlays, no proof anywhere (checked the
  images: they are title graphics, not bottle labels).
- Bourbon Cream and Chocolate Bourbon Cream (liqueurs), Extra Dry Gin, merchandise, events.

Lexington Club (a revived 1878 brand the distillery re-introduced) is its own catalog family under this maker."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Boone County"
DELAY = 10
SITEMAP = "https://boonedistilling.com/sitemap_index.xml"
IMAGE_PREFIX = "https://boonedistilling.com/"
CATALOG_FAMILIES = ["Boone County", "Lexington Club"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Kentucky Bourbon Whiskey"
RYE = "Kentucky Rye Whiskey"
STRAIGHT_BOURBON = "Straight Bourbon Whiskey"
STRAIGHT_RYE = "Straight Rye Whiskey"

# page slug → (family, expression, aliases, class statement as the page words it)
REFILE = {
    "essentials-small-batch-bourbon": ("Boone County", "Small Batch Bourbon", ["Boone County Small Batch"], STRAIGHT_BOURBON),
    "essentials-small-batch-rye": ("Boone County", "Small Batch Rye", [], STRAIGHT_RYE),
    "founders-reserve-kentucky-bourbon": ("Boone County", "Founder's Reserve Bourbon", ["Boone County Founder's Reserve Kentucky Bourbon"], BOURBON),
    "founders-reserve-kentucky-rye": ("Boone County", "Founder's Reserve Rye", ["Boone County Founder's Reserve Kentucky Rye"], RYE),
    "caskfinished-toasted-cask-finished": ("Boone County", "Toasted Cask Finished", [], BOURBON),
    "caskfinished-amburana-cask-finished": ("Boone County", "Amburana Cask Finished", [], BOURBON),
    "caskfinished-honey-soaked-cask-finished": ("Boone County", "Honey Soaked Cask Finished", [], BOURBON),
    "caskfinished-maple-cask-finished": ("Boone County", "Maple Cask Finished", [], BOURBON),
    "limited-releases-caribbean-rum-cask-finish": ("Boone County", "Caribbean Rum Cask Finished", [], BOURBON),
    "lexingtonclub-lexington-club-bourbon": ("Lexington Club", None, [], "Kentucky Straight Bourbon Whiskey"),
}
# The finish, read by hand from each page's own sentence ("finished ... in <cask>"); normalize.finish() would read the
# page title ("Toasted Cask Finished") but not the cask the maker actually describes.
FINISH = {
    "caskfinished-toasted-cask-finished": "Toasted American Oak Barrels",
    "caskfinished-amburana-cask-finished": "Amburana Brazilian Oak Casks",
    "caskfinished-honey-soaked-cask-finished": "Honey Soaked Bourbon Barrels",
    "caskfinished-maple-cask-finished": "Maple Syrup Soaked American Oak Barrels",
    "limited-releases-caribbean-rum-cask-finish": "Caribbean Rum Soaked Casks",
}
CORE = {"Small Batch Bourbon", "Small Batch Rye", "Founder's Reserve Bourbon", "Founder's Reserve Rye", None}
RARITY = [(r"caribbean", "limited"), (r".", "shelf")]
MASH_BILLS = {}

_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://boonedistilling.com/{slug}/" for slug in REFILE)


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = re.sub(r"\s+", " ", fragment.replace("|", " ")).strip()
    return t or None


def _age(copy: str) -> tuple[float | None, str | None]:
    """'aged a minimum of 5 years' → 5; 'Aged five to seven years' → the label '5-7 yr' (a range is never an age)."""
    m = re.search(r"aged\s+(?:a\s+minimum\s+of\s+|at\s+least\s+)?(\d{1,2})\s+years?", copy, re.I)
    if m:
        return float(m.group(1)), f"{int(m.group(1))} yr"
    m = re.search(r"aged\s+(\w+)\s+to\s+(\w+)\s+years?", copy, re.I)
    if m:
        lo, hi = (_NUM.get(g.lower()) or (int(g) if g.isdigit() else None) for g in m.groups())
        if lo and hi:
            return None, f"{lo}–{hi} yr"
    return None, None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    family, expression, aliases, class_raw = REFILE[slug]
    name = f"{family} {expression}" if expression else "Lexington Club Bourbon"
    own = _flatten(page)

    # Cut to the product's own copy: from the product heading (after the nav, which repeats) to the footer/related links.
    head = own.rfind("Event Contact|")
    body = own[head + len("Event Contact|"):] if head >= 0 else own
    body = body.split("BOOK A TOUR|", 1)[0]
    copy, _, notes = body.partition("TASTING NOTES")

    pm = re.search(r"Proof\s*\|\s*(\d{2,3}(?:\.\d+)?)\s*\|\s*ALC/VOL", notes)
    proof = float(pm.group(1)) if pm else None
    years, label = _age(copy)

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]

    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, finish=FINISH.get(slug),
        description=_text(copy[:600]), image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
