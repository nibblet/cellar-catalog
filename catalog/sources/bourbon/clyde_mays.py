"""clydemays.com (Clyde May's Whiskey, made by Conecuh Ridge Distillery, Troy, Alabama — the footer says
so; the brand is Conecuh Ridge's, so the catalog's existing producer 'Conecuh Ridge' is right and nothing
is re-pointed). WordPress (Rank Math sitemap_index.xml, robots.txt asks for Crawl-delay: 10 — honoured via
DELAY). Four whiskey pages under /whiskeys, each static: a header line "Straight Bourbon | 92 Proof | 750ml"
(the Special Reserve adds "6 Year Old"), a one-paragraph description that states the age ("Aged 4 to 5
years", "aged 6 years", "Aged a minimum of 4 years"), and a Tasting Notes block. No mash bill anywhere.

Judgment kept here:
 - /alabama-style-whiskey/ ("The Original", 85 proof, "finished with a hint of apple") is a flavored
   whiskey, out of the catalog's bourbon/rye scope, so it is deliberately not in REFILE and not crawled.
 - og:image is a title banner ("pp-title-bourbon_opaque.png"), not the bottle; the bottle shot is the one
   full-size "Clyde-Mays-<Name>-750x1500px-optimized.png" file on the page (resized -NNNxNNN copies skipped).
 - "Aged 4 to 5 years" is a range the label prints, so `normalize.age()` returns an age label ("4-5 yr")
   and no number; the seed's 4.5 is left alone (the diff only sets a label where the row has no age).
 - "Aged a minimum of 4 years" (the rye) is the maker's own stated age floor, read as 4 the same way
   Green River's 'a minimum of five years' is.
 - Age and proof are read only from the product block (from the 'N Proof' header to 'Tasting Notes'): the
   rest of the page is the shared nav/footer, and award lines ('95 Points') sit just after the block."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Conecuh Ridge"
DELAY = 10
SITEMAP = "https://clydemays.com/sitemap_index.xml"
IMAGE_PREFIX = "https://clydemays.com/"
CATALOG_FAMILIES = ["Clyde May's"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class statement). expression None is the plain "Clyde May's" flagship.
REFILE = {
    "straight-bourbon-whiskey": (None, ["Clyde May's Straight Bourbon", "Clyde May's Straight Bourbon Whiskey"], "Straight Bourbon Whiskey"),
    "special-reserve-bourbon": ("Special Reserve", ["Clyde May's Special Reserve Bourbon", "Clyde May's Special Reserve Straight Bourbon"], "Straight Bourbon Whiskey"),
    "straight-rye-whiskey": ("Rye", ["Clyde May's Straight Rye", "Clyde May's Straight Rye Whiskey"], "Straight Rye Whiskey"),
}
CORE = {None, "Special Reserve", "Rye"}
RARITY = [(r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://clydemays.com/{slug}/" for slug in REFILE]


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
    expression, aliases, class_raw = REFILE[slug]
    name = f"Clyde May's {expression}" if expression else "Clyde May's"

    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*Proof", own, re.I)
    proof = float(pm.group(1)) if pm else None
    # the product block: from the header line to the Tasting Notes accordion
    block = own[max(0, pm.start() - 80):] if pm else own
    block = block.split("Tasting Notes", 1)[0]
    block = re.sub(r"\|", " ", block)
    years, label = age(block)

    img = None
    for m in re.finditer(r'https://clydemays\.com/wp-content/uploads/[^"\'\s)\\,]*750x1500px[^"\'\s)\\,]*\.png', page):
        if not re.search(r"-\d+x\d+\.png$", m.group(0)):
            img = m.group(0)
            break

    desc = _text(block.split("750ml", 1)[-1].split("Award-winning", 1)[0])

    return BottlingRecord(
        brand_family="Clyde May's", expression=expression, name=name,
        source_url=f"https://clydemays.com/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style="rye" if "Rye" in class_raw else None, description=desc,
        image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
