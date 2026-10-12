"""journeyman.com (Journeyman Distillery, Three Oaks, Michigan and Valparaiso, Indiana; journeymandistillery.com 301s
here). WordPress with a custom `spirits` post type (spirits-sitemap.xml). robots.txt is Yoast's allow-all but opens
with `Crawl-delay: 10`, so DELAY is 10. Every page opens with an "Are you over 21 years of age?" overlay in its static
HTML; the product copy is served regardless and nothing here clicks through it.

Journeyman also makes gin, vodka, rum, brandy, tequila, absinthe, liqueurs, an amaro, an eggnog and four RTD
cocktails. None of those is whiskey and none is imported: the list is the 30 whiskey pages of the "Whiskey & Bourbon"
index (spirits_type/whiskey), not the sitemap.

Facts live in a bulleted block after the "Back To Spirits" link and before the footer, in two page layouts:
"PRODUCT INFORMATION | - Single-distillation from 70% organic corn / 25% organic wheat / 5% organic rye | - 45% abv /
90 proof" (the original lineup) and "• 52.5% ABV | 105 Proof | • 5% Rye | 70% Corn | 25% Wheat | • 7-Year, Single
Barrel, Bourbon" (Freedom Series and newer). Proof, age, mash and finish are read from that block only: the brand-story
paragraph above it quotes component ages ("rye whiskeys aged 8.5, 7, and 6 years") and a sibling's name. A page with
no number in the block states no proof; "Cask Strength" is not a number (Corsets, Whips & Whiskey, Farm Bourbon, Farm
Rye, High Rye Bourbon, Popcorn Bourbon), so those keep their seed proof and are not confirmed.

The seed 'Corsets, Whips & Whiskey' (120.1 proof, filed as a rye, its specs say bourbon) is a Watch Hill Proper store pick
whose barrel was dated 2019; the maker's page is the cask-strength release, a single-grain 100% wheat whiskey. The
importer corrects the spirit type to wheat whiskey and leaves the pick's proof alone (the page states none).

Not imported, and why:
- Orchard Peach Bourbon Whiskey (70 proof, peach-flavored) and Corsets, Whips & Honey Whiskey (70 proof, honey): flavored
  whiskeys, not the class this catalog tracks.
- Emancipation Corn Whiskey (Freedom Series): "Un-Aged Corn Whiskey", raw spirit, not an aged whiskey (Cedar Ridge's
  Clown's Iowa Shine precedent). W.R. White Whiskey: the unaged white whiskey of the lineup.
- Farm Bourbon, Farm Rye, High Rye Bourbon, Popcorn Bourbon, Corsets, Whips & Whiskey (new row), Old Gold Rye,
  Cherrywood Smoked Single Malt: the page states no proof. No catalog row exists for any of them, so a proof-less
  record would be reported and never added; they are not crawled.
- 'Distillery Featherbone': the seed's alias, kept.

Judgments carried here so a re-run reproduces them:
- Foundational's "3-Year American Peated Malt Barrel Finished" is the finishing cask's age, not the whiskey's; no age.
- Ravenswood 13 and Expansion blend different spirits (bourbon + rye + wheat): class "Blended Whiskey". Winston A. Fox blends
  six ryes, which is a rye (High West lesson).
- Opportunity's page title says "Straight Bourbon Bourbon"; the expression drops the repeat.
- 70% corn / 25% wheat / 5% rye (Featherbone, Depression, Opportunity, Kissing Cousins) is filed as normalize.mash_style()
  reads it, traditional (the rye is present); the maker never calls it wheated. The mash bill itself is stored.
- Election Day Rye "aged for four summers" and Kissing Cousins' "6 months" in wine barrels are copy, not an age field:
  no age, the finish is carried (Kissing Cousins only).
- Featherbone's seeded 2-year age is not stated anywhere on the maker's page; the writer never clears a seeded age, so
  it is listed in the hand-off for the owner's NAS decision.

Journeyman prints no Nose/Palate/Finish block: where a page describes how the whiskey smells or tastes it is a sentence or two
inside the brand-story copy. `tasting_notes` is only those sentences ("notes of ...", "on the palate", "the finish is ..."), taken
from the copy between the accolades and the "Back To Spirits" link, never the spec bullets or the Freedom Series intro."""
from __future__ import annotations

import html
import re
import unicodedata

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Journeyman"
DELAY = 10
SITEMAP = "https://www.journeyman.com/spirits-sitemap.xml"
IMAGE_PREFIX = "https://www.journeyman.com/"
CATALOG_FAMILIES = ["Journeyman"]
PRODUCER_BY_FAMILY = {}
BASE = "https://www.journeyman.com/spirits/"

BOURBON = "Bourbon Whiskey"
STRAIGHT_BOURBON = "Straight Bourbon Whiskey"
RYE = "Rye Whiskey"
STRAIGHT_RYE = "Straight Rye Whiskey"
WHEAT = "Wheat Whiskey"
BLEND = "Blended Whiskey"

# slug → (expression, [catalog names it answers to], class statement, finish)
PAGES = {
    # the lineup
    "featherbone-bourbon": ("Featherbone", ["Journeyman Featherbone Bourbon", "Featherbone Bourbon"], BOURBON, None),
    "last-feather-rye": ("Last Feather Rye", [], RYE, None),
    "buggy-whip-wheat": ("Buggy Whip Wheat", [], WHEAT, None),
    "silver-cross-four-grain": ("Silver Cross Four Grain", ["Journeyman Silver Cross Four Grain Whiskey"], "Four Grain Whiskey", None),
    "three-oaks-single-malt": ("Three Oaks Single Malt", ["Journeyman Three Oaks Single Malt Whiskey"], "Single Malt Whiskey", None),
    "corsets-whips-whiskey": ("Corsets, Whips & Whiskey", [], WHEAT + " Cask Strength", None),
    # annual / collaboration releases
    "not-a-king": ("Not a King Rye", ["Journeyman Not a King Rye Whiskey"], RYE, None),
    "election-day-rye-one-term": ("Election Day Rye", ["Journeyman Election Day Rye - One Term"], RYE, None),
    "kissing-cousins-whiskey": ("Kissing Cousins", ["Journeyman Kissing Cousins Whiskey"], "Whiskey", "Red & White St. Julian Barrels"),
    "double-oaked-rye-whiskey": ("Double Oaked Rye", ["Journeyman Double Oaked Rye Whiskey"], RYE, "Double Oaked"),
    "eaves-blind-special-release": ("Eaves Blind", ["Journeyman Eaves Blind Special Release"], BOURBON, None),
    "ravenswood13": ("Ravenswood 13", ["Journeyman Ravenswood 13 Anniversary Whiskey"], BLEND, None),
    "winston-a-fox-2": ("Winston A. Fox Chapter 2", ["Journeyman Winston A. Fox"], RYE, None),
    "high-rye-500": ("Conor Daly High Rye 500", [], "High Rye Bourbon Whiskey", None),
    # Freedom Series (seven releases; Emancipation is raw unaged corn whiskey and is left out)
    "foundational-straight-bourbon-whiskey": ("Freedom Series: Foundational", ["Journeyman Foundational Straight Bourbon Whiskey"], STRAIGHT_BOURBON, "American Peated Malt Barrel"),
    "revolutionary-straight-rye-whiskey": ("Freedom Series: Revolutionary", ["Journeyman Revolutionary Straight Rye Whiskey"], STRAIGHT_RYE, "Rum Barrel"),
    "expansion-blended-straight-whiskey": ("Freedom Series: Expansion", ["Journeyman Expansion Blended Straight Whiskey"], "Blended Straight Whiskey", None),
    "modernization-straight-rye-whiskey": ("Freedom Series: Modernization", ["Journeyman Modernization Straight Rye Whiskey"], STRAIGHT_RYE, "Barrel Stave"),
    "depression-straight-bourbon-whiskey": ("Freedom Series: Depression", ["Journeyman Depression Straight Bourbon Whiskey"], STRAIGHT_BOURBON, None),
    "opportunity-straight-bourbon-bourbon": ("Freedom Series: Opportunity", ["Journeyman Opportunity Straight Bourbon"], STRAIGHT_BOURBON, None),
}
CORE = {"Featherbone", "Last Feather Rye", "Buggy Whip Wheat", "Silver Cross Four Grain", "Three Oaks Single Malt"}
RARITY = [(r"freedom series|eaves|ravenswood|winston|conor daly|election day|not a king|double oaked|kissing|buggy whip", "limited"),
          (r"corsets", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _items(own: str) -> list[str]:
    """The bullet lines of the spec block: after 'Back To Spirits', before the footer's CONTACT."""
    i = own.find("Back To Spirits|")
    if i < 0:
        return []
    block = own[i + len("Back To Spirits|"):]
    j = block.find("CONTACT|")
    block = block[:j] if j > 0 else block
    block = block.replace("PRODUCT INFORMATION|", "")
    return [s.strip(" |") for s in re.split(r"\s*[•–]\s*|(?:^|\s)-\s", block) if s.strip(" |")]


def _mash(items: list[str]) -> str | None:
    for s in items:
        if re.search(r"abv|proof", s, re.I) or "%" not in s:
            continue
        s = re.sub(r"Single-distillation from\s*", "", s)
        s = re.sub(r"\b(organic|Michigan-grown|Michigan|Heirloom Red)\s+", "", s, flags=re.I)
        s = re.sub(r"\s+Whiskey\b", "", s)
        s = re.sub(r"\s*[/|]\s*", ", ", s).strip(" ,|")
        if re.search(r"\d\s*%", s) and not re.search(r"popcorn", s, re.I):
            return s
    return None


TASTE_CUE = re.compile(r"\bnotes? of\b|\bflavou?rs? of\b|\bhints? of\b|\bwhisper of\b|\bpalate\b|\bnose\b|\bfinish\b(?!\s+line)|\bcitrus notes\b", re.I)
NOT_TASTE = re.compile(r"%|\bproof\b|\baged\b|\bFreedom Series\b|\bjournal\b|\bpoints?\b", re.I)


def _tasting_notes(own: str) -> str | None:
    """The sentences of the copy (after "BRAND STORY", else after "SHOP NOW", up to "Back To Spirits") that describe taste."""
    start = own.find("BRAND STORY|")
    start = start + len("BRAND STORY|") if start >= 0 else own.find("SHOP NOW|") + len("SHOP NOW|")
    end = own.find("Back To Spirits|")
    if start < len("SHOP NOW|") or end < start:
        return None
    copy = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", own[start:end].replace("|", " "))).strip()  # NFKC: the page's "toﬀee" ligature
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", copy) if TASTE_CUE.search(x) and not NOT_TASTE.search(x)]
    return " ".join(sentences)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[slug]
    name = f"Journeyman {expression}"
    own = _flat(page)
    items = _items(own)
    spec = " | ".join(items)

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof\b", spec, re.I)
    proof = float(pm.group(1)) if pm else None

    # an age only from an age line ("Aged 7 years", "7-Year, Single Barrel, Bourbon"); "3-Year ... Barrel Finished" is the cask's
    years, label = age(" | ".join(s for s in items if re.search(r"\b\d{1,2}[- ]?years?\b|\baged\b", s, re.I) and not re.search(r"finish", s, re.I)))

    mash_raw = _mash(items)
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    return BottlingRecord(
        brand_family="Journeyman", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw,
        finish=finish, tasting_notes=_tasting_notes(own), image_url=html.unescape(og.group(1)) if og else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
