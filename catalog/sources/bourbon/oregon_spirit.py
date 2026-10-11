"""oregonspiritdistillers.com (Oregon Spirit Distillers, Bend, Oregon). WordPress + SiteOrigin page builder,
static HTML, no cart (a "Shop now" button links out to Total Wine). robots.txt asks `Crawl-delay: 30`, so
DELAY is 30 (ten pages is five minutes; the site's own request, honoured). The bottling pages sit in the page
sitemap; the nav lists seven whiskeys and a 7-year cask-strength single barrel is linked from the whiskeys
landing page but not the nav.

Each page carries a plain "Age: N years  Proof: N" pair (the straight pages) or "Proof: N" alone (the three
Bottled-in-Bond pages, whose only age words are the federal rule's "no less than 4 years" — a law's minimum,
not an age statement, so age is read from the "Age:" field only and the BiB pages state none). The mash bill
is a graphic on every page ("Mash Bill:" followed by an image), so it is never machine-readable; the only
mash words in text are the bourbon's "four grain bourbon made with corn, rye, wheat, and malted barley" and
the rye's "100% Oregon-grown rye grain". og:image is the site's recipes icon on every page; the bottle shot is
the first body image that is not the header line-art, a mash-bill graphic, a logo or a recipe photo.

The label on the BiB bottles reads "Single Barrel Bottled in Bond" (confirmed from the maker's own bottle
photographs, and the pages' "single barrel program" copy), so that is the expression; the straight bottles say
"Straight American <grain> Whiskey". The seed filed these under "Oregon Spirit Distillers <grain>" in places and
"Oregon Spirit <grain>" in others; the family is "Oregon Spirit" and the name is `Oregon Spirit <expression>`.
The old names are aliases so each existing row claims its page by name."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Oregon Spirit"
DELAY = 30
SITEMAP = "https://oregonspiritdistillers.com/sitemap.xml"
IMAGE_PREFIX = "https://oregonspiritdistillers.com/"
CATALOG_FAMILIES = ["Oregon Spirit"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class statement as the label reads it).
REFILE = {
    "straight-american-bourbon-whiskey": (
        "Straight American Bourbon", ["Oregon Spirit Distillers Bourbon", "Oregon Spirit Bourbon"], "Straight Bourbon Whiskey"),
    "bourbon-whiskey-bottled-in-bond": (
        "Single Barrel Bottled in Bond Bourbon",
        ["Oregon Spirit Distillers Single Barrel Bottled In Bond", "Oregon Spirit Distillers Single Barrel Bottled In Bond Bourbon",
         "Oregon Spirit Bottled in Bond Bourbon"], "Bottled in Bond Bourbon Whiskey"),
    "straight-american-7-year-bourbon-cask-strength": (
        "7 Year Cask Strength Single Barrel", ["Oregon Spirit 7 Year Cask Strength Bourbon"], "Straight Bourbon Whiskey Cask Strength"),
    "straight-american-rye-whiskey": (
        "Straight American Rye", ["Oregon Spirit Distillers Rye", "Oregon Spirit Distillers Straight Rye", "Oregon Spirit Rye"], "Straight Rye Whiskey"),
    "bottled-in-bond-rye-whiskey": (
        "Single Barrel Bottled in Bond Rye", ["Oregon Spirit Bottled in Bond Rye", "Oregon Spirit Distillers Single Barrel Bottled In Bond Rye"],
        "Bottled in Bond Rye Whiskey"),
    "straight-american-wheat-whiskey": (
        "Straight American Wheat", ["Oregon Spirit Straight American Wheat Whiskey", "Oregon Spirit Distillers Wheat"], "Straight Wheat Whiskey"),
    "bottled-in-bond-wheat-whiskey": (
        "Single Barrel Bottled in Bond Wheat",
        ["Oregon Spirit Distillers Single Barrel Bottled In Bond Wheat", "Oregon Spirit Distillers Single Barrel Bottled In Bond Wheat Whiskey"],
        "Bottled in Bond Wheat Whiskey"),
    "straight-american-malt-whiskey": (
        "Straight American Malt", ["Oregon Spirit Straight American Malt Whiskey", "Oregon Spirit Distillers Malt"], "Straight American Malt Whiskey"),
}
CORE = {e for slug, (e, _a, _c) in REFILE.items() if "7-year" not in slug}
RARITY = [(r"7 year", "limited"), (r".", "shelf")]
MASH_BILLS = {}

NOT_BOTTLE = re.compile(r"logo|favicon|icon|Oregon-Spirit-Line|mash|recipe|old-fash|julep|/r-[a-z]|Your-paragraph", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"https://oregonspiritdistillers.com/{slug}/" for slug in REFILE]


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"Oregon Spirit {expression}"
    own = _flatten(page)
    # Everything before the BiB explainer ("What Specifically Makes it Bottled in Bond?") and the reviews/recipes.
    own = re.split(r"What Specifically Makes it Bottled|\| REVIEWS\||\| RECIPES\|", own)[0]

    pm = re.search(r"Proof:\s*\|?\s*(\d{2,3}(?:\.\d+)?)\b", own)
    proof = float(pm.group(1)) if pm else None

    am = re.search(r"Age:\s*\|?\s*(\d{1,2})\s*years?\b", own)
    years = float(am.group(1)) if am else None
    label = f"{int(years)} yr" if years else None

    mash_raw = None
    if re.search(r"four grain bourbon made with corn, rye, wheat, and malted barley", own, re.I):
        mash_raw = "Four grain: corn, rye, wheat, malted barley"
    elif re.search(r"100% Oregon-grown rye grain", own, re.I):
        mash_raw = "100% Rye"

    img = None
    for m in re.finditer(r'<img[^>]*\bsrc="([^"]+/wp-content/uploads/[^"]+)"', page):
        if not NOT_BOTTLE.search(m.group(1)):
            img = m.group(1)
            break

    desc = own.split("SHOP NOW|")[-1].split("Tasting Notes|")[0].split("Flavor Notes:|")[0]
    desc = re.sub(r"\s*\|\s*", " ", desc).strip()[:600] or None

    return BottlingRecord(
        brand_family="Oregon Spirit", expression=expression, name=name,
        source_url=f"https://oregonspiritdistillers.com/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
