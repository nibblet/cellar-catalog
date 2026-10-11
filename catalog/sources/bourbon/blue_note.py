"""bluenotebourbon.com (Blue Note Bourbon — B.R. Distilling Co., Memphis, Tennessee; the whiskey is "born in
Kentucky, raised in Memphis"). WordPress + WooCommerce, static HTML; robots.txt asks for a Crawl-delay of 10
(DELAY below) and disallows only cart/admin paths. The page carries a "By clicking YES you verify that you are
21" overlay in its static HTML — the product copy is served regardless and nothing here clicks through it.

The product index is /products/ (Current Releases only); the Limited and Past Releases lists appear in the nav
block of each product page, and the pages themselves sit in `page-sitemap.xml` (the `product` post type is tour
tickets). The list is hand-curated from that nav, not parsed from the sitemap.
Every product page ends its copy with a "Technical Details" block of labelled fields (Aged / Product Type /
Mash Bill / Proof & Filtration / Finish), in two typographies (a label with a colon on its own line, or a
"• AGED: ..." bullet on the Special Reserve pages). Proof is read only from the Proof & Filtration field
and only when it opens with a number: "93 proof, unfiltered", "119.6/ 59.8 % ABV", "112.5 Proof". "Variable
proof", "Barrel proof" and "Cask Strength" state none (Uncut, Las Notas, Single Barrel Reserve, Single Barrel
Rye, 17-Year) — those rows are listed, not confirmed, and the proof-less 17-Year and Single Barrel Reserve,
which have no catalog row, are not added. Age is read from the Aged field only ("A minimum of three years",
"Four years", "Minimum of seventeen years"); a range ("4-19 Years" on the Special Reserve blends) is a display
label. Las Notas says "Aged: Four years" and then "Additional 1 year in French Oak Las Notas barrels" as a
separate Finish field; the page states no aggregate, so no age is read (the module does not add the stages).

Special Reserve is one annual bottling with a page per year (2024, 2025, 2026 — a blend of 7/10/9 casks, 112.5 /
116.3 / 119.9 proof). Pages are listed oldest first so the newest supplies the facts (`_dedupe` keeps the last);
the catalog's "Cask Finish Series" row (112.5 = the 2024 page) is that release filed as its own bottling and is
merged into Special Reserve by hand afterwards. A blend of straight bourbons is a straight bourbon here, not
`blend` (High West lesson): class_raw carries the label class, the finish is carried separately.

The Toasted page is the old Crossroads (its own cocktail and award images are named Crossroads): the page
states "Finished with two types of toasted French oak staves" and 100 proof, same as both Crossroads rows in the
catalog. The product photo is the last bare `<img src=...>` before the Technical Details block (the nav carries
the other products' bottle shots on every page, so og:image — there is none — and page-wide scans are wrong).
"""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Blue Note"
DELAY = 10  # robots.txt Crawl-delay: 10
SITEMAP = "https://www.bluenotebourbon.com/page-sitemap.xml"
IMAGE_PREFIX = "https://www.bluenotebourbon.com/"
CATALOG_FAMILIES = ["Blue Note"]
PRODUCER_BY_FAMILY = {}

KY_BOURBON = "Kentucky Straight Bourbon Whiskey"
TN_BOURBON = "Tennessee Straight Bourbon Whiskey"
BOURBON = "Straight Bourbon Whiskey"
KY_RYE = "Kentucky Straight Rye Whiskey"
RYE = "Straight Rye Whiskey"

# page slug → (expression, [catalog names it answers to], class statement, finish).
# The Special Reserve pages are listed oldest year first (see the docstring).
PAGES = {
    "rye-whiskey": ("Rye", [], KY_RYE, None),
    "toasted": ("Toasted", ["Blue Note Crossroads", "Blue Note Crossroads, Toasted French Oak", "Blue Note Crossroads Toasted"], BOURBON, "Toasted French Oak"),
    "juke-joint": ("Juke Joint", [], KY_BOURBON, None),
    "uncut": ("Uncut", [], KY_BOURBON, None),
    "blue-note-wheated-bourbon-101": ("Wheated Bourbon 101", ["Blue Note Wheated Bourbon"], KY_BOURBON, None),
    "honey-rye": ("Honey Rye Cask", ["Blue Note Honey Cask Rye", "Blue Note Honey Rye", "Blue Note Honey Rye Whiskey"], RYE, "Honey Cask"),
    "honey-bourbon": ("Honey Bourbon Cask", ["Blue Note Honey Bourbon"], BOURBON, "Honey Cask"),
    "single-barrel-rye": ("Single Barrel Rye", [], RYE, None),
    "las-notas": ("Las Notas", [], KY_BOURBON, "Las Notas French Oak"),
    "premium-small-batch": ("Premium Small Batch", [], TN_BOURBON, None),
    "2024-special-reserve": ("Special Reserve", ["Blue Note Special Reserve Cask Finish Series"], BOURBON, None),
    "2025-blue-note-special-reserve": ("Special Reserve", [], BOURBON, None),
    "2026-blue-note-special-reserve": ("Special Reserve", [], BOURBON, None),
    # No stated proof and no catalog row: crawled so the dry run says so, never added.
    "single-barrel-reserve": ("Single Barrel Reserve", [], KY_BOURBON, None),
    "17-year": ("17 Year", [], TN_BOURBON, None),
}
# Dedupe keeps the last record per expression, so oldest-first ordering matters.
ORDER = ["rye-whiskey", "toasted", "juke-joint", "uncut", "blue-note-wheated-bourbon-101", "honey-rye", "honey-bourbon",
         "single-barrel-rye", "las-notas", "premium-small-batch", "single-barrel-reserve", "17-year",
         "2024-special-reserve", "2025-blue-note-special-reserve", "2026-blue-note-special-reserve"]
CORE = {"Rye", "Toasted", "Juke Joint", "Uncut", "Wheated Bourbon 101"}  # the site's "Current Releases"
RARITY = [(r"special reserve|las notas|honey|single barrel|premium small batch|17 year", "limited"), (r".", "shelf")]
MASH_BILLS = {}

LABELS = r"AGED|PRODUCT TYPE|MASH BILL|PROOF\s*&\s*FILTRATION|FINISH|YIELD|AVAILABILITY|SENSORY NOTES|BUY NOW|PLEASE NOTE"


def list_urls(fetcher) -> list[str]:
    return [f"https://www.bluenotebourbon.com/products/{slug}/" for slug in ORDER]


def _flat(fragment: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _fields(own: str) -> dict[str, str]:
    """The Technical Details block as {label: value}."""
    i = own.lower().find("technical details")
    if i < 0:  # the 2026 Special Reserve page has no heading, just the labelled fields after its cask list
        m = re.search(r"\bAGED\s*:", own)
        if not m:
            return {}
        i = m.start()
    block = own[i:]
    out: dict[str, str] = {}
    pat = re.compile(rf"(?:•\s*)?({LABELS})\s*:\s*\|?\s*(.*?)(?=\|?\s*(?:•\s*)?(?:{LABELS})\s*:|\|\s*(?:Sensory Notes|BUY NOW|Awards)\b|$)", re.I)
    for m in pat.finditer(block):
        k = re.sub(r"\s+", " ", m.group(1).upper())
        out.setdefault(k, re.sub(r"\s*\|\s*", " ", m.group(2)).strip(" |"))
    return out


def _proof(value: str | None) -> float | None:
    if not value:
        return None
    m = re.match(r"\s*(\d{2,3}(?:\.\d+)?)\s*(?:/|proof)", value, re.I)
    return float(m.group(1)) if m else None


def _mash(value: str | None) -> str | None:
    if not value or not re.search(r"\d\s*%", value):
        return None
    t = re.sub(r",?\s+and\s+", ", ", value)
    t = re.sub(r"(%\s*[A-Za-z ]+?)\s+(\d{1,2}\s*%)", r"\1, \2", t)  # "21% Wheat 9% Malted Barley"
    return re.sub(r"\s+", " ", t).strip(" ,")


# The 2026 Special Reserve page has no Technical Details heading and wraps its bottle shot differently; the file
# below is that page's own bottle photo, used only while it is still on the cached page.
IMAGE_FALLBACK = {"2026-blue-note-special-reserve": "https://www.bluenotebourbon.com/wp-content/uploads/2026/03/SPCLRSRV_BOTTLE_RETOUCH-prod.png"}


def _image(page: str, slug: str = "") -> str | None:
    fb = IMAGE_FALLBACK.get(slug)
    if fb and fb in page:
        return fb
    i = page.lower().find("technical details")
    if i < 0:
        return None
    bare = re.findall(r'<img src="(https://www\.bluenotebourbon\.com/wp-content/uploads/[^"]+)" alt="" />', page[:i])
    return bare[-1] if bare else None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[slug]
    name = f"Blue Note {expression}"
    own = _flat(page)
    f = _fields(own)
    proof = _proof(f.get("PROOF & FILTRATION"))
    years, label = (None, None)
    if slug != "las-notas" and f.get("AGED"):
        years, label = age("aged " + f["AGED"])
    mash_raw = None if expression == "Special Reserve" else _mash(f.get("MASH BILL"))  # a blend of three recipes
    rye = class_raw.endswith("Rye Whiskey")
    return BottlingRecord(
        brand_family="Blue Note", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw,
        mash_style="rye" if rye else None, finish=finish, image_url=_image(page, slug),
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
