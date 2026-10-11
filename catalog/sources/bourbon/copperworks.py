"""copperworksdistilling.com (Copperworks Distilling Co., Seattle and Kenmore WA — a Square Online / Weebly shop; the
bare domain 301s to www). robots.txt asks for `Crawl-delay: 5` and disallows only search, cart, checkout and the
whiskey-club-access area, so DELAY is 6. The shop is a single-page app: category pages (/shop/whiskey, /whiskey-archives,
/whiskey-club-releases) hold no text in their static HTML, but every product page carries its whole description, specs
included, in `og:description` (HTML-escaped twice), and `og:title` / `og:image` are per product. The list is therefore the
product pages of sitemap.xml that are whiskey; nothing on the category pages is read.

SCOPE. Copperworks is a single-malt house, not a bourbon maker: nothing it sells is bourbon or rye. The catalog's bourbon type
already holds American single malt (Journeyman, Three Oaks, Starlight precedents) and the 13 seed rows are all American
single malt plus Kilt Lifter, so the module covers Copperworks' American single malts and the Kilt Lifter whiskey. NOT
imported: the gins (Small Batch, Cask, Plum, tonic-barrel and cask-finished releases), vodka, the Plum 75 / cocktail,
beer, merchandise, tickets and experiences, and the unlabelled "Archive Whiskey" / "Farmsmith 1" / "Peatsmith & Coke" pages
(no text). The archive-sale remnants Release No. 001 / 006 / 024 / 040, Single Cask No. 236, Whitney's Whiskey Cask 119-2 and
Hulagan Exclusive 2022 are old single casks with no catalog row and are not added.

Facts, read from the description:
- Strength: "700ml, 50% ABV" (maltsmith, peatsmith, farmsmith, kilt lifter, color cask, ...), "50% ABV (100 proof)",
  "61.6% ABV (123.2 Proof)", "62.95% ABV" (Craft Malt Month 2025). Proof is the stated "(N proof)" else ABV x 2. The Amaro Cask
  page prints no strength anywhere in its description, so it is listed, not confirmed (the seed's 100 stays).
- Age: only a total the page states for the whiskey in the bottle: "matured for four years and nine months" (CMM 2025),
  "five years and three months" (Farmsmith), "Seven years and two months later" (Scotch Cask), "aged this whiskey for five
  years" (Single Cask 160-2), "5 years and 9 months" (CMM 2026), "total maturation of eight years" (St. George) and the
  name "11 Year Old". NOT read, because they are floors, "just under/over" figures, a first stage or components: "just under 5
  years" (Color Cask), "over six years" (Red Wine Cask), "over seven years ... over six months" (Pondera), "more than five
  years" (Kilt Lifter), "just under 3 and a half years" (Peatsmith, an initial release), "seven years and eight months ...
  after only a month of finishing" (Amaro, a stage), the two-stage Arette (5y7m + 1y9m), Urban Family (three-and-a-half years
  + ten months) and Hair of the Dog ("a little over 3 years" + 8 months). Seeded ages the maker never states are listed in the
  hand-off for an owner NAS decision.
- Mash bill: none is stated as percentages ("brewer-style recipe of pale and caramelized malts", "Five Malt"), so no mash
  bill is stored; the style is single malt.

Judgments carried here so a re-run reproduces them:
- Craft Malt Month is an annual single cask (2025 = Single Cask No. 484 at 62.95%, 4y9m; 2026 = No. 488 at 63.2%, 5y9m). The
  seed (125.9 proof, 4.75 yr) is the 2025 cask, so it claims the 2025 page; 2026 is a different cask and is a new row,
  "Craft Malt Month 2026 American Single Malt". They are not folded into one.
- CORE is the standing lineup the seeds already mark: Maltsmith (the "flagship") and Peatsmith. Farmsmith is a recurring
  single-farm series whose barley changes each release, so it stays non-core with the seed.
- The seed 'Amaro Cask America Single Malt' is a typo of "American"; it claims the page by that name and is renamed (the
  typo stays as an alias).
- Kilt Lifter is "an American Whiskey distilled from an unhopped version of Pike's Kilt Lifter scotch-style ale": it states no
  single-malt claim, so class_raw is "American Whiskey" (spirit_type other, as seeded).
- Whiskey Club Exclusives (Amaro, Arette, Red Wine, St. George) and one-cask releases are limited; the shelf bottles are
  Maltsmith, Peatsmith and Kilt Lifter.
- Added (no seed row, current 700 ml releases with a stated strength): 11 Year Old, Arette Tequila Cask, Craft Malt Month 2026,
  St. George Apple Brandy Cask, Urban Family Barleywine Cask, Hair of the Dog Adam and Matt cask finishes."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Copperworks Distilling Co."
DELAY = 6
BASE = "https://www.copperworksdistilling.com/product/"
SITEMAP = "https://www.copperworksdistilling.com/sitemap.xml"  # not crawled; list_urls is fixed
IMAGE_PREFIX = "https://152526200.cdn6.editmysite.com/"
CATALOG_FAMILIES = ["Copperworks"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Copperworks"
ASM = "American Single Malt Whiskey"

# product path -> (expression, catalog names it answers to, class statement, finish, age phrase)
# age phrase: regex over the description whose groups are (years[, months]); None = no age is read
PAGES = {
    "copperworks-maltsmith-american-single-malt-whiskey-700ml-/5": (
        "Maltsmith American Single Malt", ["Copperworks Maltsmith American Single Malt Whiskey"], ASM, None, None),
    "copperworks-peatsmith-american-single-malt-whiskey-700ml-/42": (
        "Peatsmith American Single Malt", ["Copperworks Peatsmith American Single Malt Whiskey"], ASM, None, None),
    "copperworks-farmsmith-american-single-malt-whiskey-700ml-/10": (
        "Farmsmith American Single Malt", ["Copperworks Farmsmith American Single Malt Whiskey"], ASM, None,
        r"for (\w+) years and (\w+) months"),
    "copperworks-kilt-lifter-whiskey-700ml-/NJU36J2CRUPKAGTLT4J3NBPE": (
        "Kilt Lifter", ["Copperworks Kilt Lifter Whiskey", "Pike Kilt Lifter Whiskey"], "American Whiskey", None, None),
    "copperworks-color-cask-american-single-malt-whiskey-700ml-/70": (
        "Color Cask American Single Malt", ["Copperworks Color Cask American Single Malt Whiskey"], ASM, None, None),
    "copperworks-scotch-cask-american-single-malt-whiskey-700ml-/ZCU4WCOKWPNVMZDYZTH2YPJT": (
        "Scotch Cask American Single Malt", ["Copperworks Scotch Cask American Single Malt Whiskey"], ASM, None,
        r"(\w+) years and (\w+) months later"),
    "copperworks-amaro-cask-american-single-malt-whiskey-700ml-/BC7F4CHCRELPBIIJ43GBFTV6": (
        "Amaro Cask American Single Malt", ["Copperworks Amaro Cask American Single Malt Whiskey", "Copperworks Amaro Cask America Single Malt"], ASM, "Amaro Cask", None),
    "copperworks-craft-malt-month-2025-american-single-malt-whiskey-700ml-/VNS64Q2N3CEQUYZCUUQMCXT5": (
        "Craft Malt Month American Single Malt", ["Copperworks Craft Malt Month 2025 American Single Malt Whiskey"], ASM, None,
        r"matured for (\w+) years and (\w+) months"),
    "copperworks-american-single-malt-whiskey-single-cask-no-160-2-700ml-/W2YAQM6WGI7ODKER2RXQTQWW": (
        "Single Cask No. 160-2 Single Malt", ["Copperworks American Single Malt Whiskey Single Cask No. 160-2"], ASM, None,
        r"aged this whiskey for (\w+) years"),
    "copperworks-pondera-cabernet-cask-american-single-malt-whiskey-700ml-/MKL3SY4K5UGZNGGVRQPACDDJ": (
        "Special Release Pondera Cabernet Cask Single Malt", ["Copperworks Pondera Cabernet Cask American Single Malt Whiskey"], ASM,
        "Pondera Cabernet Sauvignon Cask", None),
    "copperworks-red-wine-cask-american-single-malt-whiskey-700ml-/115": (
        "Special Release Red Wine Cask Single Malt", ["Copperworks Red Wine Cask American Single Malt Whiskey"], ASM, None, None),
    # no seed row
    "copperworks-11-year-old-american-single-malt-whiskey-700-ml-/IY4BFJCR74A3LHMOPVNKXREB": (
        "11 Year Old American Single Malt", ["Copperworks 11 Year Old American Single Malt Whiskey"], ASM, None, "TITLE"),
    "copperworks-arette-tequila-cask-american-single-malt-whiskey-700ml-/NX2J2LFGY2ORJBZ5ZHFHSCVZ": (
        "Arette Tequila Cask American Single Malt", ["Copperworks Arette Tequila Cask American Single Malt Whiskey"], ASM, "Arette Tequila Cask", None),
    "copperworks-craft-malt-month-2026-american-single-malt-whiskey-700-ml-/6SNNANXCMM4XZZYZPXKBB5FJ": (
        "Craft Malt Month 2026 American Single Malt", ["Copperworks Craft Malt Month 2026 American Single Malt Whiskey"], ASM,
        "Previously Used Rye Whiskey Cask", r"for (\w+) years and (\w+) months before we bottled"),
    "copperworks-st-george-apple-brandy-cask-finished-american-single-malt-whiskey-700ml-/35PUU6C2R5I24W7GGCVDDGCA": (
        "St. George Apple Brandy Cask American Single Malt", ["Copperworks St. George Apple Brandy Cask Finished American Single Malt Whiskey"], ASM,
        "St. George Apple Brandy Cask", r"total maturation of (\w+) years"),
    "copperworks-urban-family-barleywine-cask-finished-american-single-malt-whiskey-700ml-/ABTK5DV4GPRKMA3MONGLNZLI": (
        "Urban Family Barleywine Cask American Single Malt", ["Copperworks Urban Family Barleywine Cask Finished American Single Malt Whiskey"], ASM,
        "Urban Family Barleywine Cask", None),
    "copperworks-hair-of-the-dog-adam-cask-finish-whiskey/KK6WUVILCRKYGROKWE6JA2MZ": (
        "Hair of the Dog Adam Cask American Single Malt", ["Copperworks Hair of the Dog Adam Cask Finish Whiskey"], ASM,
        "Hair of the Dog Adam Ale Bourbon Cask", None),
    "copperworks-hair-of-the-dog-matt-cask-finish-whiskey/AV3QRDABYNTOLVCGBXNRYMDN": (
        "Hair of the Dog Matt Cask American Single Malt", ["Copperworks Hair of the Dog Matt Cask Finish Whiskey"], ASM,
        "Hair of the Dog Matt Ale Bourbon Cask", None),
}
CORE = {"Maltsmith American Single Malt", "Peatsmith American Single Malt"}
DISCONTINUED_BY_MAKER: set[str] = set()
RARITY = [(r"maltsmith|peatsmith|kilt lifter", "shelf"), (r".", "limited")]
MASH_BILLS = {}

_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def list_urls(fetcher) -> list[str]:
    return [BASE + p for p in PAGES]


def _n(w: str) -> int | None:
    return int(w) if w.isdigit() else _NUM.get(w.lower())


def _description(page: str) -> str:
    og = re.search(r'property="og:description" content="([^"]*)"', page)
    d = html.unescape(html.unescape(og.group(1))) if og else ""
    d = d.replace("\xa0", " ").replace("’", "'")
    d = re.sub(r"\s+", " ", d)
    i = d.rfind("-----")
    if i >= 0:
        d = d[i + 5:]  # drop the shipping-state notice that opens most pages
    j = d.find("WA Tax Information")
    return (d[:j] if j >= 0 else d).strip()


def _proof(desc: str) -> float | None:
    m = re.search(r"\((\d{2,3}(?:\.\d+)?)\s*proof\)", desc, re.I) or re.search(r"bottled at (\d{2,3}(?:\.\d+)?) proof", desc, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*%\s*(?:ABV|Alc)", desc, re.I)
    return round(float(m.group(1)) * 2, 1) if m else None


def _age(desc: str, title: str, phrase: str | None) -> tuple[float | None, str | None]:
    if phrase == "TITLE":
        m = re.search(r"\b(\d{1,2}) Year Old\b", title)
        return (float(m.group(1)), f"{m.group(1)} yr") if m else (None, None)
    if not phrase:
        return None, None
    m = re.search(phrase, desc, re.I)
    if not m:
        return None, None
    y = _n(m.group(1))
    mo = _n(m.group(2)) if m.lastindex and m.lastindex >= 2 else 0
    if y is None or mo is None:
        return None, None
    years = round(y + mo / 12, 2)
    return years, f"{y} yr" + (f" {mo} mo" if mo else "")


def parse(url: str, page: str) -> BottlingRecord | None:
    path = url.replace(BASE, "")
    if path not in PAGES:
        return None
    expression, aliases, class_raw, finish, phrase = PAGES[path]
    name = f"{FAMILY} {expression}"
    desc = _description(page)
    tm = re.search(r'property="og:title" content="([^"]*)"', page)
    title = html.unescape(tm.group(1)) if tm else ""
    years, label = _age(desc, title, phrase)
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=_proof(desc),
        age_years=years, age_label=label, class_raw=class_raw, finish=finish,
        image_url=html.unescape(og.group(1)) if og else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE)
