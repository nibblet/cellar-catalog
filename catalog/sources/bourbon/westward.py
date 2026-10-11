"""westwardwhiskey.com (Westward Whiskey, Portland, Oregon — Diageo-owned since 2021). A Shopify storefront; robots.txt
sets no Crawl-delay (DELAY 6) and allows /products. Every rendered page opens a client-side "legal drinking age" modal, so the
crawl never loads the rendered HTML: it reads Shopify's own `/products.json` listing and each product's `.json` endpoint,
whose `body_html` carries the same copy (the Rabbit Hole precedent). The rendered page is only named as the source_url.

SCOPE. Westward makes American Single Malt, not bourbon: the home page calls the brand "American Single Malt whiskey" and the
product copy says "our American Single Malt" (Double Dark, PX Sherry Cask). The catalog's bourbon type already holds
`american_single_malt` rows (Journeyman Three Oaks, High West, the 20 Westward seeds), so this module is scoped to the
whiskeys on the shop's own list that correspond to those seeds, filed as "American Single Malt Whiskey" (the maker's brand-level
statement; individual pages do not repeat it). The Two Malts bottles (barley malt blended with malted rye) are filed as
"Malt Whiskey" (spirit type `other`, as seeded). Reported and NOT imported: the 40-odd other Library / club releases without a
seed row (Agave, Tokaji, Smoked, Trinity of Casks, Triple-Distilled, Wayward Odyssey, Milestone No. 3 and No. 4, the retail
Single Barrel and pick bottles, the Ken's Artisan sourdough and Krogstad aquavit-cask whiskeys), the Old Grad bottle, and every
non-whiskey product (cocktail kits, tasting sets and bundles, barware, honey, club memberships, hidden shop-fee products).
The writer makes every new row browsable, so a limited release with no seed is left out on purpose.

Judgments carried here so a re-run reproduces them:
- CORE is the standing lineup that is not a club release: Original, Cask Strength, Pinot Noir Cask, Stout Cask. Everything else is
  an annual or club-exclusive release, matched to its seed, confirmed from the page and left hidden.
- "Westward American Single Malt" (the BB-era name) is Westward Whiskey Original: same 90 proof, and the shop's Original
  page is the only standing 90-proof Westward. The seed names are kept as aliases on every renamed row.
- A page's age is never read. Prose gives component ages ("5 to 12 years" in Trinity of Casks, "5.5 to 6 years" for Double
  Dark's base) or a bonded floor, none of which is a bottle's age statement. The Bottled-in-Bond series is one row on the
  latest edition (Edition No. 2, 2026: "bottled at exactly 100 proof"), which also says "matured for nine years"; that is one
  edition's figure on a rolling series, so no age is stored.
- Proof is the first "N proof" after "Bottled at" ("Pinot Noir Cask: 90 proof (*Awarded at 125 proof)" is 90). Seeds written
  from older releases are corrected to the page that is listed now (the annual releases are re-issued under the same name).
- The retail "Westward Whiskey Milestone, Edition No. 1 - 2023" (86 proof) and "Edition No. 2" (97 proof) are kept as the
  separate rows the seeds already are (the shop lists them separately).
- Milestone, Elements and the Two Malts pages do not state a class; they are filed with the brand's.
- The Two Malts row keeps the series name as its expression; the page title "Two Malts Rye - 2023" would make normalize.spirit_type()
  read the name's "Rye" and file a malt whiskey blended with 12% malted rye as a straight rye.
"""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Westward Whiskey"
DELAY = 6
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["Westward"]
PRODUCER_BY_FAMILY = {}
LIST_URL = "https://westwardwhiskey.com/products.json?limit=250"
PRODUCT_URL = "https://westwardwhiskey.com/products/{}.json"
PAGE_URL = "https://westwardwhiskey.com/products/{}"

ASM = "American Single Malt Whiskey"
MALT = "Malt Whiskey"
SEED = "Westward American Single Malt"

# handle → (expression, [catalog names it answers to], class statement, finish)
REFILE = {
    "westward-whiskey-original": ("Original", [SEED, "Westward Whiskey Original", "Westward Whiskey American Single Malt"], ASM, None),
    "westward-whiskey-cask-strength": ("Cask Strength", [SEED + " Cask Strength", "Westward Whiskey Cask Strength"], ASM + " Cask Strength", None),
    "westward-whiskey-pinot-noir-cask": ("Pinot Noir Cask", [SEED + " Pinot Noir Cask", "Westward Whiskey Pinot Noir Cask"], ASM, "Pinot Noir Casks"),
    "westward-whiskey-stout-cask": ("Stout Cask", [SEED + " Stout Cask", "Westward Whiskey Stout Cask"], ASM, "Stout Casks"),
    "westward-whiskey-chardonnay-cask-2022": ("Chardonnay Cask", [SEED + " Chardonnay Cask", "Westward Whiskey Chardonnay Cask"], ASM, "Chardonnay French Oak Casks"),
    "westward-whiskey-elements-high-desert-to-klamath-basin-2022": ("Elements: High Desert to Klamath Basin", [SEED + " Elements: High Desert to Klamath Basin", "Westward Whiskey Elements: High Desert to Klamath Basin"], ASM, "Garryana Oak Casks"),
    "westward-whiskey-two-malts-bridgeport-brewing-co-2021": ("Two Malts Bridgeport Brewing Co.", ["Westward American Two Malts Bridgeport Brewing Co.", "Westward x BridgePort Brewing Co. Two Malts"], MALT, None),
    "westward-whiskey-bottled-in-bond-2026": ("Bottled In Bond American Single Malt", ["Westward Whiskey Bottled-In-Bond"], ASM + " Bottled in Bond", None),
    "westward-whiskey-cognac-cask-2023": ("Cognac Cask", ["Westward Cognac Casks Single Malt", "Westward Whiskey Cognac Cask"], ASM, "Cognac Casks"),
    "westward-whiskey-double-dark-2025": ("Double Dark", ["Westward Double Dark Single Malt", "Westward Whiskey Double Dark"], ASM, "French Acacia Casks"),
    "westward-whiskey-sauternes-cask": ("Sauternes Cask", ["Westward Grand Cru Sauternes Cask Single Malt", "Westward Whiskey Sauternes Cask"], ASM, "Sauternes Casks"),
    "westward-whiskey-milestone-edition-no-2": ("Milestone Edition No. 2", ["Westward Milestone Edition No. 2 Single Malt"], ASM, None),
    "westward-whiskey-milestone": ("Milestone Edition No. 1", ["Westward Milestone Single Malt"], ASM, None),
    "westward-whiskey-oloroso-sherry-cask-2024": ("Oloroso Sherry Cask", ["Westward Oloroso Sherry Cask Single Malt"], ASM, "Oloroso Sherry Casks"),
    "westward-whiskey-px-sherry-cask-2026": ("PX Sherry Cask", ["Westward PX Sherry Cask Single Malt"], ASM, "Pedro Ximenez Sherry Casks"),
    "westward-whiskey-cask-strength-reserve-pinot-noir-cask-2026": ("Reserve Pinot Noir Cask", ["Westward Reserve Pinot Noir Cask Single Malt"], ASM + " Cask Strength", "Pinot Noir Casks"),
    "westward-whiskey-two-malts-rye-2023": ("Two Malts", ["Westward Two Malts Rye", "Westward Whiskey Two Malts Rye"], MALT, None),
    "westward-whiskey-vienna-malt-2024": ("Vienna Malt", ["Westward Vienna Malt Single Malt"], ASM, None),
    "westward-whiskey-vintners-cuvee-2024": ("Vintner's Cuvée", ["Westward Vintner's Cuvée Single Malt"], ASM, "Mixed Wine Casks"),
    "westward-x-fort-george-brewery-stout-cask-2025": ("x Fort George Brewery Stout Cask", ["Westward x Fort George Brewery Stout Cask Single Malt"], ASM, "Matryoshka Stout Barrels"),
}
CORE = {"Original", "Cask Strength", "Pinot Noir Cask", "Stout Cask"}
RARITY = [(r"milestone", "allocated"), (r"original|^westward (cask strength|pinot noir cask|stout cask)$", "shelf"), (r".", "limited")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    handles = {p["handle"] for p in json.loads(fetcher.get(LIST_URL)).get("products", [])}
    return [PRODUCT_URL.format(h) for h in REFILE if h in handles]


def _flat(body_html: str | None) -> str:
    body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", body_html or "", flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", body)).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1].removesuffix(".json")
    if handle not in REFILE:
        return None
    expression, aliases, class_raw, finish = REFILE[handle]
    name = f"Westward {expression}"
    data = json.loads(page)["product"]
    own = _flat(data.get("body_html"))

    pm = re.search(r"bottled at[^.]*?(\d{2,3}(?:\.\d+)?)\s*[- ]?proof", own, re.I) or re.search(r"(\d{2,3}(?:\.\d+)?)\s*[- ]?proof\b", own, re.I)
    proof = float(pm.group(1)) if pm else None
    images = data.get("images") or []
    img = images[0].get("src") if images else (data.get("image") or {}).get("src")
    return BottlingRecord(
        brand_family="Westward", expression=expression, name=name, source_url=PAGE_URL.format(handle), proof=proof,
        age_years=None, age_label=None, class_raw=class_raw, finish=finish, image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
