"""wyomingwhiskey.com (Wyoming Whiskey, Kirby, Wyoming — a hand-built static site; robots.txt is a 404, so no Crawl-delay is
stated and DELAY is 6). There is no sitemap: the list is the `/our-whiskey/` page's tiles ("Ready to Ship", "Store Exclusives",
"Whiskey Archive"), mapped to slugs in PAGES below. Every page opens with an "Are you of legal drinking age?" overlay that is a
client-side div in the served HTML; the product copy is in the same response and nothing here clicks through it or sets a
cookie (the Journeyman precedent).

Each product page carries one structured block, `product-overview__details`, in the page's own markup:
`Aged <span>5</span> years` / `<span>50</span> ALC/VOL` / `<span>100</span> proof` / `<span>750</span> ml`. Proof and age
are read from that block only (the prose elsewhere repeats a "minimum of 5 years" floor on Small Batch that the field states
as 5). Class comes from the page's own words (see PAGES); the image is the first picture in the page's
`product-overview__media` carousel, whose alt text is "<name> Bottle Image 1" (page markup, not OCR). `og:image` is the same
site logo on every page and is not used.

What is imported: the four standing bottles of "Ready to Ship" (Small Batch, Double Cask, Outryder Whiskey, Single Barrel —
CORE) and the limited / store-exclusive releases the catalog already holds as seed rows (National Parks No. 1-5, Acadia, Buffalo
Bill Cody, Barrel Strength, 10 Year Anniversary). Those are matched to their seeds and confirmed from the maker's page; they
stay hidden because they are not core. The writer makes every NEW row browsable, so a limited release with no seed row is
deliberately not parsed and not added: Moran, Old Faithful, Wilderness (Yellowstone exclusive, 84 proof), Queen of the Tetons,
Independence Rock, The Grand Barrel 2623 / 2641 / 2707, Steamboat, 1872 and Statesman. Their pages were crawled and state proof
and age; adding them as hidden rows needs a writer option, not a module change.

Judgments carried here so a re-run reproduces them:
- The maker renames two seeds: "Double Cask Limited Edition" is "Double Cask" on the maker's Ready-to-Ship list (not limited);
  "National Parks Limited Edition" (92 proof) is "National Parks No. 1" and "National Parks: Acadia Edition" is "Acadia
  National Park". The old names stay as aliases.
- National Parks No. 2, No. 3 and Acadia name no class in their copy (No. 1, No. 4 and No. 5 say bourbon); they are filed as
  bourbon with the series, which is also what the seeds say.
- Outryder is "Straight American Whiskey" (stray high-rye bourbon blended with rye whiskey), so its spirit type is `other`.
  The seeded "Outryder Limited Edition" (2021, 100 proof) has no page of its own; it stays a seed and may be the same bottle
  as Outryder Whiskey (owner call, not merged).
- Double Cask is "a bourbon" for five years, then finished in Pedro Ximenez sherry casks: class is bourbon, finish carried.
- Barrel Strength is listed at 8 years / 122.4 proof; the seed (a 2024 batch review) said 10 years / 121. The maker's current
  page wins, like Booker's: the row drifts with each release.
- No page states a mash bill; none is stored.
- `tasting_notes` is the page's own Nose / Taste-or-Palate / Finish block (`product-overview__notes`; the Color line is left out).
  Five pages (Single Barrel, National Parks No. 1 and No. 2, Barrel Strength, 10 Year Anniversary) print the identical
  Single-Barrel-style block, at 92 to 122 proof, which is copy carried over from a sibling, so it is not taken as theirs."""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Wyoming Whiskey"
DELAY = 6
IMAGE_PREFIX = "https://wyomingwhiskey.com/"
CATALOG_FAMILIES = ["Wyoming Whiskey"]
PRODUCER_BY_FAMILY = {}
BASE = "https://wyomingwhiskey.com/"

STRAIGHT_BOURBON = "Straight Bourbon Whiskey"
BOURBON = "Bourbon Whiskey"

# slug → (expression, [catalog names it answers to], class statement, finish)
PAGES = {
    "small-batch": ("Small Batch", ["Wyoming Whiskey Small Batch Bourbon"], STRAIGHT_BOURBON, None),
    "double-cask": ("Double Cask", ["Wyoming Whiskey Double Cask Limited Edition"], BOURBON, "Pedro Ximenez Sherry Casks"),
    "outryder": ("Outryder Whiskey", [], "Straight American Whiskey", None),
    "single-barrel": ("Single Barrel", ["Wyoming Whiskey Single Barrel Bourbon"], BOURBON, None),
    "national-parks-no-1": ("National Parks No. 1", ["Wyoming Whiskey National Parks Limited Edition"], STRAIGHT_BOURBON, None),
    "national-parks-no-2": ("National Parks No. 2", ["Wyoming Whiskey National Parks Limited Edition No. 2"], STRAIGHT_BOURBON, None),
    "national-parks-no-3": ("National Parks No. 3", ["Wyoming Whiskey National Parks Limited Edition No. 3"], STRAIGHT_BOURBON, None),
    "national-parks-no-4": ("National Parks No. 4", [], STRAIGHT_BOURBON, None),
    "national-parks-no5": ("National Parks No. 5", [], BOURBON, None),
    "acadia-national-park": ("Acadia National Park", ["Wyoming Whiskey National Parks: Acadia Edition"], STRAIGHT_BOURBON, None),
    "buffalo-bill-cody": ("Buffalo Bill Cody", [], BOURBON, None),
    "barrel-strength": ("Barrel Strength", [], BOURBON, None),
    "10-year-anniversary": ("10 Year Anniversary Edition", [], BOURBON, None),
}
CORE = {"Small Batch", "Double Cask", "Outryder Whiskey", "Single Barrel"}
RARITY = [(r"national parks|acadia|buffalo bill|barrel strength|anniversary", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


REPEATED_NOSE = "browned butter, cola, black currant and dried dates"  # the block those five pages share


def _tasting_notes(page: str) -> str | None:
    """The product overview's note rows (`<h4>Nose</h4><p>...</p>`), minus Color; None for the block a sibling page repeats."""
    block = re.search(r'product-overview__notes">(.*?)<span class="mountain-range"', page, re.S)
    rows = re.findall(r"<h4[^>]*>(.*?)</h4>\s*<p[^>]*>(.*?)</p>", block.group(1), re.S) if block else []
    notes = [(_text(label).title(), _text(text)) for label, text in rows]
    notes = [(label, text) for label, text in notes if text and label in ("Nose", "Taste", "Palate", "Finish")]
    if any(label == "Nose" and text.lower() == REPEATED_NOSE for label, text in notes):
        return None
    return " ".join(f"{label}: {text.rstrip('.')}." for label, text in notes)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[slug]
    name = f"Wyoming Whiskey {expression}"

    details = re.search(r'<div\s+class="product-overview__details">(.*?)</div>', page, re.S)
    block = _text(details.group(1)) if details else ""  # "Aged 5 years 50 ALC/VOL 100 proof 750 ml"
    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof\b", block, re.I)
    proof = float(pm.group(1)) if pm else None
    years, label = age(re.sub(r"^(Aged)\s+(\d+)\s+years", r"\1 \2 years", block))

    media = re.search(r'product-overview__media">(.*?)</div>\s*</div>\s*<div\s+class="product-overview__content"', page, re.S)
    img = re.search(r'<img[^>]+src="([^"]+)"', media.group(1)) if media else None
    return BottlingRecord(
        brand_family="Wyoming Whiskey", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, finish=finish, tasting_notes=_tasting_notes(page),
        image_url=urljoin(url, img.group(1)) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
