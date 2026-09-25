"""yellowstonebourbon.com (Limestone Branch Distillery, Lebanon, Kentucky — a Luxco/MGP brand; the
2025 Limited Edition page names Limestone Branch and sister distillery Ross & Squibb, Lawrenceburg,
Indiana as the blend's two sources). WordPress with no product sitemap — every bottling is a plain page,
hand-listed here. Every page states "N Proof / N% abv" and a short prose description; no mash bill is
published anywhere on the site. Two known site errors are worked around rather than trusted verbatim:
Single Barrel states "Bottled-in-Bond" (legally exactly 100 proof) while its own displayed figure reads
"93 Proof" — the label BiB claim wins, since a 100-proof floor is federal law, not a maker's guess; and
Select's "a perfect blend of 4- and 7-year bourbons" names two component ages with no aggregate, so no
age is read from it at all rather than picking one arbitrarily (the elliptical "N- and N-year" phrasing
is stripped before calling `age()`, which would otherwise resolve the second, unpaired number). Limited
Edition is a single evolving page overwritten each year (dated mirrors like `/limited-edition-25/` exist
only for the current cycle, and every `/limited-edition-NN/` guess for a past year 404s), so it's read as
one current release, not a historical series."""
from __future__ import annotations

import html
import re
import urllib.parse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Yellowstone"
DELAY = 6
SITEMAP = "https://yellowstonebourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://yellowstonebourbon.com/"
CATALOG_FAMILIES = ["Yellowstone"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases).
REFILE = {
    "small-batch-107": ("Small Batch 107", []),
    "select-bourbon": ("Select", []),
    "single-barrel": ("Single Barrel", ["Yellowstone , Single Barrel", "Yellowstone Hand Picked Collection, Single Barrel"]),
    "limited-edition": ("Limited Edition", ["Yellowstone Limited Edition 7 year old"]),
    "american-single-malt": ("American Single Malt", []),
    "special-finishes-collection-toasted": ("Special Finishes Toasted", []),
    "rum-cask": ("Special Finishes Rum Cask", []),
    "recollection-series": ("Recollection Series", ["Yellowstone Recollection Bourbon"]),
}
CORE = {"Small Batch 107", "Select", "Single Barrel"}
RARITY = [(r"limited edition|recollection", "unicorn"), (r"special finishes|single malt", "lottery"),
          (r"single barrel", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://yellowstonebourbon.com/{slug}/" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Yellowstone {expression}"

    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)

    bib = bool(re.search(r"bottled-in-bond", own, re.I))
    if bib:
        proof = 100.0  # the page's own displayed figure ("93 Proof") contradicts its own BiB claim; the law wins
    else:
        pm = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*Proof\s*/\s*[\d.]+%\s*abv", own, re.I)
        proof = float(pm.group(1)) if pm else None

    age_text = re.sub(r"\d+-\s*and\s*\d+-\s*year", "[ages]", own, flags=re.I)
    years, label = age(age_text)

    single_malt = expression == "American Single Malt"
    class_raw = "American Single Malt Whiskey" if single_malt else "Kentucky Straight Bourbon Whiskey"
    if bib:
        class_raw += " Bottled-in-Bond"

    # og:image is a site-wide logo, not the bottle shot; the real photo is the first "imgs/bottles/" image
    im = re.search(r'<img[^>]*src="([^"]*imgs/bottles/[^"]*)"', page)
    img = None
    if im:
        path = im.group(1)
        img = "https://yellowstonebourbon.com" + urllib.parse.quote(path, safe="/") if path.startswith("/") else path

    desc = _text(own.split("BUY NOW", 2)[-1][:600]) if own.count("BUY NOW") >= 2 else _text(own[:600])

    return BottlingRecord(
        brand_family="Yellowstone", expression=expression, name=name,
        source_url=f"https://yellowstonebourbon.com/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=None, description=desc,
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
