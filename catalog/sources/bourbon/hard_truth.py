"""hardtruth.com (Hard Truth Distilling Co., Nashville, Indiana — hardtruthdistilling.com 301s here;
hardtruthdistillery.com is an unrelated parked Namecheap placeholder). WordPress with a custom `spirits` post type
(spirits-sitemap.xml); robots.txt is Yoast's allow-all with no Crawl-delay, so DELAY is the project's usual 6.
Every page opens with an "Are you over the age of 21?" overlay in its static HTML — the product copy is served
regardless and nothing here clicks through it.

The list is the maker's own "Our Spirits" index (/spirits/): the Sweet Mash Whiskey core six, the Limited Edition
Reserve Collection (Barrel Finish Reserve, Master Distiller's Reserve, 7 Year, the single-barrel releases) and the
craft spirits. The craft spirits (rum, vodka, gin, creams, peanut-butter whiskey, McCabe's Irish) are not in scope.
The sitemap also holds older pages the index no longer links (Sipes' bourbon/rye/smoked, Schoonover, Indiana Rye,
Harvest Rye) — history, not a listing — they are not crawled except where the catalog already has a row for the
Mellencamp collaboration they belong to.

Facts live in each page's "Spirit Specs" block (one line per fact, between "Spirit Specs" and "Appearance"):
"Bottled at 100 proof (50% ABV)", "Cask strength at 108.4 proof", "Barrel Strength: 106.1 Proof", "Aged 7
years", "Made with 94% Rye, 6% Malted Barley", "Mash bill: 51% rye, 38% corn, 11% chocolate malted barley". Proof
and age are read from that block only: the intro prose quotes the Bottled-in-Bond explainer ("aged at least four
years") and a sibling's number. Proof is a number only; "Bottled at cask strength", "barrel proof" state none
(Maple Brulee Rye, the 7 Year trio, Sweet Mash Rye, Wheated Mizunara, Double Oak Sweet Mash Rye), and Bottled-in-
Bond without a printed number (American Odd) is listed, not confirmed. Those rows keep their seed proof and
source. A blend of two named mash bills (BW-1 + BW-5, RW-3 + RW-4) states no single recipe, so mash is left
null for it.

Not imported, and why (a program, not a bottling, or no proof to state):
- Barrel Strength Bourbon, French Oak Sweet Mash Rye, Amburana Finished Bourbon: store-pick single barrels, a
  table of barrel numbers and per-barrel proofs; Amburana Finished Bourbon Single Barrel and the two single-barrel
  Master Distiller's Reserve Malt Ryes (Toasted, Roasted) state "cask strength" or one barrel's proof.
- Master Distiller's Reserve 2024 Blend: "bottled at cask strength", no number; the seed 'Master Distiller's
  Reserve Blend Sweet Mash Rye' (115, 4 yr) is not claimed — it may be an earlier year's blend.
- Single-barrel Schoonover: barrel proof, no number.

`tasting_notes` is the page's own Aroma / Taste / Finish lines (not the maker quote after them, the intro or the
recipes); Dark Roast Rye's page has none, so it stays None.

Naming: bar-order expressions follow the catalog's seed where the seed is a faithful short form ('Barrel Finish
Reserve: French Oak'); the maker's longer title is an alias."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Hard Truth"
DELAY = 6
SITEMAP = "https://hardtruth.com/spirits-sitemap.xml"
IMAGE_PREFIX = "https://hardtruth.com/"
CATALOG_FAMILIES = ["Hard Truth"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Straight Bourbon Whiskey"
BIB_BOURBON = "Bottled in Bond Straight Bourbon Whiskey"
RYE = "Straight Rye Whiskey"
BIB_RYE = "Bottled in Bond Straight Rye Whiskey"
BLEND = "Blend of Straight Bourbon and Rye Whiskeys"

# slug → (expression, [catalog names it answers to], class statement, finish)
BASE = "https://hardtruth.com/spirits/"
PAGES = {
    # Sweet Mash Whiskey — the core six
    "sweet-mash-bourbon": ("Sweet Mash Bourbon", ["Hard Truth Sweet Mash"], "Bourbon Whiskey", None),
    "sweet-mash-wheated-bourbon": ("Sweet Mash Wheated Bourbon", ["Hard Truth Wheated Bourbon Bottled in Bond"], BIB_BOURBON, None),
    "sweet-mash-four-grain-bourbon": ("Sweet Mash Four Grain Bourbon", ["Hard Truth Four Grain", "Hard Truth Four Grain Bottled in Bond"], BIB_BOURBON, None),
    "sweet-mash-rye-whiskey": ("Sweet Mash Rye", [], "Rye Whiskey", None),
    "high-road-rye-whiskey": ("High Road Rye", [], "Rye Whiskey", None),
    "master-distillers-reserve-dark-roast-rye": ("Dark Roast Rye", ["Hard Truth Master Distiller's Reserve Dark Roast Rye"], BIB_RYE, None),
    # 7 Year
    "7-year-straight-bourbon": ("7 Year Straight Bourbon", ["Hard Truth 7 Year"], BOURBON, None),
    "7-year-sweet-mash-rye-whiskey": ("7 Year Sweet Mash Rye", ["Hard Truth 7 Year Sweet Mash Rye Whiskey"], RYE, None),
    "7-year-wheated-bourbon": ("7 Year Wheated Bourbon", ["Hard Truth 7 Year Wheated"], BOURBON, None),
    # Master Distiller's Reserve (2023, second release; Batch #001 seeds are folded in by hand)
    "chocolate-malt-sweet-mash-rye-whiskey-2023": ("Chocolate Malt Rye", ["Hard Truth Chocolate Malt Sweet Mash Rye", "Hard Truth Master Distiller's Reserve Chocolate Malt Sweet Mash Rye (RW-3)"], RYE, None),
    "caramel-malt-sweet-mash-rye-whiskey-2023": ("Caramel Malt Rye", ["Hard Truth Master Distiller's Reserve Caramel Malt Sweet Mash Rye (RW-4)"], RYE, None),
    "malted-rye-sweet-mash-rye-whiskey-2023": ("Malted Rye", ["Hard Truth Sweet Master Distiller's Reserve Malted Rye Sweet Mash Rye (RW-6)", "Hard Truth Master Distiller's Reserve Malted Rye Sweet Mash Rye (RW-6)"], RYE, None),
    # Barrel Finish Reserve
    "barrel-finish-reserve-straight-bourbon-finished-on-french-oak": ("Barrel Finish Reserve: French Oak", ["Hard Truth Barrel Finish Reserve Straight Bourbon Finished on French Oak"], BOURBON, "Toasted French Oak"),
    "barrel-finish-reserve-straight-wheated-bourbon-finished-with-mizunara": ("Barrel Finish Reserve: Mizunara Finished Wheated", ["Hard Truth Barrel Finish Reserve Straight Wheated Bourbon Finished On Mizunara"], BOURBON, "Mizunara Oak"),
    "barrel-finish-reserve-double-oak-sweet-mash-rye": ("Barrel Finish Reserve: Double Oaked Rye", ["Hard Truth Barrel Finish Reserve Double Oak Sweet Mash Rye"], RYE, "Double Oaked"),
    "double-oaked": ("Barrel Finish Reserve: Double Oaked Sweet Mash Rye", ["Hard Truth Double Oak Sweet Mash Rye"], RYE, "Double Oaked"),
    "double-oaked-bourbon": ("Barrel Finish Reserve: Double Oak Bourbon", ["Hard Truth Double Oak Bourbon"], BOURBON, "Double Oaked"),
    "mizunara": ("Barrel Finish Reserve: Mizunara Finished Sweet Mash Rye", ["Hard Truth Mizunara Finished Sweet Mash Rye"], RYE, "Mizunara Oak"),
    "maple-brulee-rye": ("Maple Brulee Rye", ["Hard Truth Maple Brûlée Rye"], RYE, "Maple Brûlée Barrels"),
    "barrel-finish-reserve-smr-sauternes": ("Barrel Finish Reserve: Sauternes Finished Sweet Mash Rye", ["Hard Truth Sweet Mash Rye Finished in Sauternes Wine Barrels"], RYE, "Sauternes Wine Barrels"),
    "barrel-finish-reserve-smr-px-sherry": ("Barrel Finish Reserve: PX Sherry Finished Sweet Mash Rye", ["Hard Truth Sweet Mash Rye Finished in PX Sherry Barrels"], RYE, "PX Sherry Barrels"),
    "barrel-finish-reserve-smr-px-brandy": ("Barrel Finish Reserve: PX Brandy Finished Sweet Mash Rye", ["Hard Truth Sweet Mash Rye Finished in PX Brandy Barrels"], RYE, "PX Brandy Barrels"),
    "barrel-finish-reserve-smr-cognac": ("Barrel Finish Reserve: Cognac Finished Sweet Mash Rye", ["Hard Truth Sweet Mash Rye Finished in French Oak Cognac Barrels"], RYE, "French Oak Cognac Barrels"),
    "barrel-finish-reserve-2024-blend": ("Barrel Finish Reserve: 2024 Blend", ["Hard Truth Barrel Finish Reserve 2024 Blend"], RYE, "Toasted French Oak"),
    # Mellencamp Whiskey Co. collaboration (numbered, four releases)
    "harvest-rye": ("Harvest Rye", ["Hard Truth Mellencamp Harvest Rye"], RYE, None),
    "farmers-reserve": ("Farmer's Reserve", ["Hard Truth MWC Release #2"], BLEND, "Amburana Oak"),  # Chocolate Malt Rye + Sweet Mash Bourbon
    "french-oak-harvest-rye": ("French Oak Harvest Rye", [], RYE, "French Oak"),
    "american-odd-bourbon": ("American Odd", ["Hard Truth American Odd Bourbon"], BIB_BOURBON, None),
    # Listed on the index, no proof stated and no catalog row (never added; the dry run says so)
    "master-distillers-reserve-2024-blend": ("Master Distiller's Reserve 2024 Blend", [], RYE, None),
    "master-distillers-reserve-toasted-malt-rye": ("Toasted Malt Rye", [], RYE, None),
    "master-distillers-reserve-roasted-malt-rye": ("Roasted Malt Rye", [], RYE, None),
}
# Dedupe keeps the last record per expression key; nothing here repeats an expression, so order only keeps the report tidy.
CORE = {"Sweet Mash Bourbon", "Sweet Mash Wheated Bourbon", "Sweet Mash Four Grain Bourbon", "Sweet Mash Rye", "High Road Rye", "Dark Roast Rye"}
RARITY = [(r"mizunara|amburana|2024 blend|7 year|barrel finish reserve|harvest|farmer|american odd|chocolate|caramel|malted rye|maple|roasted|toasted malt", "limited"),
          (r"dark roast", "allocated"), (r".", "shelf")]
MASH_BILLS = {}

SPEC_START = "Spirit Specs|"
GRAINS = (r"Corn|Rye|Wheat|[Mm]alted [Bb]arley|[Mm]alted [Rr]ye|[A-Za-z]+ [Mm]alted [Bb]arley|[A-Za-z]+ [Mm]alt [Bb]arley|[Mm]alt [Bb]arley")


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _specs(own: str) -> list[str]:
    i = own.find(SPEC_START)
    if i < 0:
        return []
    block = own[i + len(SPEC_START):]
    for end in ("Appearance|", "Filter by Spirit"):
        j = block.find(end)
        if j > 0:
            block = block[:j]
            break
    return [s.strip() for s in block.split("|") if s.strip()]


def _notes(own: str) -> str | None:
    """The page's own Aroma / Taste / Finish lines — one token each after the label — never the quote or recipes below."""
    i = own.find("Appearance|")
    if i < 0:
        return None
    block = own[i:]
    j = block.find("Filter by Spirit")
    toks = [t.strip() for t in (block[:j] if j > 0 else block).split("|") if t.strip()]
    parts = [f"{toks[k]}: {toks[k + 1].rstrip('. ')}." for k in range(len(toks) - 1) if toks[k] in ("Aroma", "Taste", "Finish")]
    return " ".join(parts)[:900] or None


def _mash(specs: list[str], own: str) -> str | None:
    if any(len(re.findall(r"\b(?:BW|RW)-\d", s)) >= 2 for s in specs):
        return None  # a blend of two named mash bills states no single recipe
    parts: list[str] = []
    for s in specs:
        parts += [f"{pct}% {g.title()}" for pct, g in re.findall(rf"(\d{{1,2}}(?:\.\d+)?)%\s+({GRAINS})\b", s, re.I)]
    if not parts:
        m = re.search(r"features (\d{1,2}) percent (rye|corn|wheat) and (\d{1,2}) percent (malted barley)", own)  # Sweet Mash Rye's intro
        if m:
            parts = [f"{m.group(1)}% {m.group(2).title()}", f"{m.group(3)}% {m.group(4).title()}"]
    return ", ".join(parts) or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[slug]
    name = f"Hard Truth {expression}"
    own = _flat(page)
    specs = _specs(own)
    spec_text = " | ".join(specs)

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*[- ]?proof\b", spec_text, re.I)
    proof = float(pm.group(1)) if pm else None

    years, label = age(" | ".join(s for s in specs if re.search(r"\baged\b", s, re.I)))
    if years is None and slug == "american-odd-bourbon":
        am = re.search(r"aged for (\d{1,2}) years", own)  # the intro states it; the BiB floor is the same number but unstated here
        if am:
            years, label = float(am.group(1)), f"{am.group(1)} yr"

    mash_raw = _mash(specs, own)
    rye = "rye whisk" in class_raw.lower() and "blend" not in class_raw.lower()
    if re.search(r"cask strength|barrel strength", spec_text, re.I):
        class_raw += " Cask Strength"

    og = re.search(r'property="og:image" content="([^"]+)"', page)
    img = html.unescape(og.group(1)) if og else None

    return BottlingRecord(
        brand_family="Hard Truth", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw,
        mash_style="rye" if rye else None, finish=finish, tasting_notes=_notes(own), image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
