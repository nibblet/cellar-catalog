"""chattanoogawhiskey.com (Chattanooga Whiskey, Chattanooga, Tennessee — WordPress; wp-sitemap.xml lists a `product` post type;
robots.txt opens with `Crawl-delay: 10`, so DELAY is 10). Every page opens a "Over 21?" overlay that is a client-side div in
the served HTML; the product copy is in the same response and nothing here clicks through it.

Each `/product/<slug>/` page carries one spec block in the page's own markup: `Mash Bill:` / `Age:` / `Proof:` / `Style:` ...
Proof is read from `Proof:` (not `Entry Proof:`), class from the page's `Style:` line (see PAGES; the finishing subtitle is
carried as `finish`, never left in the class — the High West lesson), and the image is the `product-image` tile whose alt
text is the page's own tile name (every page carries a carousel of products and a tile list, so the alt picks this bottle's).

AGE. The maker states "Greater than N years" on nearly every page ("Age: Greater than 2 years" on the 91). That is a floor,
not an age statement, so no age is stored for any of them. The one exception is Batch 033 (Triple Peat), whose Age field is
"4 years, 2 mos" (the seed's 4.17). The seeded ages the maker never states are listed in the hand-off for an owner NAS decision.

SCOPE. The site lists ~100 products: every Experimental batch since 001 (many are liqueurs, gin liqueurs and infusions), the
yearly Single Barrel / Vault / Riverfront series (a program, not a bottle: no proof), the BiB vintages since Spring 2017, the
Founder's blends and the Barrel Finishing Series. The writer makes every new row browsable, so a limited bottling with no seed
row is deliberately not parsed and not added; only bottlings the catalog already holds as seeds (plus the standing lineup) are
in PAGES. Left out on purpose: Silver (the unaged "white" whiskey, 100 proof; no seed, and Journeyman's White Whiskey set the
precedent), Solera Full Proof (unproofed: no number, tour-only), Founder's 11th (no seed), the BiB vintages other than the
latest, all other Experimental batches, the single-barrel series pages, Ginger Infused (a bourbon seltzer, not whiskey).

Judgments carried here so a re-run reproduces them:
- The standing lineup (CORE) is the 91, Cask 111 and 99 Rye. The BiB vintages, Founder's blends, finishes and Experimental
  batches are limited and stay hidden when matched.
- The Bottled-in-Bond vintages are one row, "Bottled in Bond Bourbon Vintage Series", on the latest vintage listed (Fall 2022:
  100 proof, BiB by law); it drifts with every vintage.
- Founder's 10th is "a blend of 3 bourbon mash bills" (bourbon); the 11th-14th are "A Blend of Straight Whiskeys" (blend),
  so the seeded 12th (bourbon) is corrected. Triple Islay and Triple Peat are blends of straight whiskeys too, and the Moldovan
  Ice Wine is a 72% malt / 28% bourbon blend (that percentage is a blend ratio, not a mash bill, and is not stored).
- Cabernet Cask and the Single Pot Still are labelled "Straight Malt Whiskey" (no "single malt" on the label), so their spirit
  type reads `other`, not the seeded `american_single_malt`; the seeds' "Single Malt" names are dropped (aliased). Owner call.
- "99 Rye" is "Straight Rye Malt Whiskey" and reads as rye, like the seed.
- Mash bills are stored nowhere: the pages list grains and in-house recipe codes (SB091, R18025), never percentages of a bill."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Chattanooga Whiskey"
DELAY = 10
IMAGE_PREFIX = "https://chattanoogawhiskey.com/"
CATALOG_FAMILIES = ["Chattanooga Whiskey"]
PRODUCER_BY_FAMILY = {}
BASE = "https://chattanoogawhiskey.com/product/"

BOURBON = "Straight Bourbon Whiskey"
BLEND = "Blend of Straight Whiskeys"
MALT = "Straight Malt Whiskey"

# slug → (expression, [catalog names it answers to], class statement, finish, tile alt text)
PAGES = {
    "chattanooga-whiskey-91": ("91", [], BOURBON, None, "91"),
    "chattanooga-whiskey-111": ("111 Cask", ["Chattanooga Whiskey Cask 111"], BOURBON, None, "Cask 111"),
    "chattanooga-whiskey-99": ("99 Rye", [], "Straight Rye Malt Whiskey", None, "99 Rye"),
    # Bottled in Bond vintages: one row, oldest first so the latest vintage wins (see docstring)
    "bib-spring-2022": ("Bottled in Bond Bourbon Vintage Series", [], BOURBON + " Bottled in Bond", None, "BIB SPRING 2022"),
    "bib-fall-2022": ("Bottled in Bond Bourbon Vintage Series", [], BOURBON + " Bottled in Bond", None, "BIB FALL 2022"),
    "founders-10th-anniversary-blend": ("Founder's 10th Anniversary Blend", [], BOURBON, None, "FOUNDER'S 10th"),
    "founders-12th-anniversary-blend": ("Founder's 12th Anniversary Blend", [], BLEND, None, "Founder's 12th"),
    "founders-13th-anniversary-blend": ("Founder's 13th Anniversary Blend", [], BLEND, None, "Founder's 13th"),
    "founders-14th-anniversary-blend": ("Founder's 14th Anniversary Blend", [], BLEND, None, "Founder's 14th"),
    # Barrel Finishing Series
    "tawny-port-cask-finish": ("Tawny Port Cask Finish", [], BOURBON, "Tawny Port Barrels", "Tawny Port Cask"),
    "islay-scotch-cask-finish": ("Islay Scotch Cask Finish", [], BOURBON, "Islay Scotch Barrels", "Islay Scotch Cask"),
    "white-port": ("White Port Cask Finish", [], BOURBON, "White Port Casks", "White Port Cask"),
    "russian-river-pinot-cask": ("Russian River Pinot Cask Finished", [], BOURBON, "Russian River Pinot Noir Barrels", "Pinot Cask"),
    "triple-islay": ("Triple Islay Cask Finished", [], BLEND, "Islay Scotch Casks", "Triple Islay Cask"),
    "cabernet-cask": ("Silver Oak Cabernet Cask Finished", ["Chattanooga Whiskey Silver Oak Cabernet Cask Oak Finished Single Malt"], MALT, "Cabernet Sauvignon Casks", "Cabernet Cask"),
    "michigan-maple-syrup": ("Maple Syrup Cask Finished", [], BOURBON, "Michigan Maple Syrup Barrels", "Michigan Maple Syrup"),
    "moldovan-ice-wine": ("Moldovan Ice Wine Cask", [], BLEND, "Moldovan Ice Wine Barrels", "Moldovan Ice Wine"),
    # Experimental Distillery batches the catalog holds
    "batch-033": ("Experimental: Triple Peat", [], BLEND, "Islay Scotch Barrels", "Batch 033"),
    "batch-xxxv": ("Experimental: Centenary Cask", [], BOURBON, "Oloroso Sherry Puncheon", "Batch XXXV"),
    "batch-043": ("Experimental: Pre Prohibition Style", [], BOURBON, None, "Batch 043"),
    "batch-047": ("Experimental: Single Pot Still", ["Chattanooga Whiskey Experimental: Single Pot Still Single Malt"], MALT, None, "Batch 047"),
}
CORE = {"91", "111 Cask", "99 Rye"}
RARITY = [(r"whiskey (91|111 cask|99 rye)$", "shelf"), (r".", "limited")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("’", "'").replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish, alt = PAGES[slug]
    name = f"Chattanooga Whiskey {expression}"
    own = _flat(page)

    pm = re.search(r"(?<!Entry )Proof:\s*\|?\s*(\d{2,3}(?:\.\d+)?)\b", own)
    proof = float(pm.group(1)) if pm else None

    # "Greater than N years" is a floor, so only an exact "N years, M mos" counts
    am = re.search(r"\bAge:\s*\|?\s*(\d{1,2}) years?,?\s*(\d{1,2}) mos?\b", own)
    years = round(int(am.group(1)) + int(am.group(2)) / 12, 2) if am else None
    label = f"{years} yr" if years else None

    img = next((m.group(1) for m in re.finditer(r'<img (?:class="product-image" )?src="([^"]+)" alt="([^"]*)"', page)
                if html.unescape(m.group(2)).replace("\u2019", "'").lower() == alt.lower()), None)
    return BottlingRecord(
        brand_family="Chattanooga Whiskey", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, finish=finish,
        image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
