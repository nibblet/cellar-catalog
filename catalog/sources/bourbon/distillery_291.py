"""distillery291.com (Distillery 291, Colorado Springs — WordPress + Yoast, sitemap_index.xml → page-sitemap;
robots.txt allows everything). One static page per whiskey; the product block sits between the nav's
"Select Page" and a trailing "ADDITIONAL SUGGESTIONS" / "EXPLORE MORE OF" carousel of OTHER products.

What a page states (and what it doesn't):
 - Proof: a structured "ABV: | 65.1% Alc. / 130.3 PROOF" line, or "101.7 proof / 50.8% ABV" in the copy; the
   first "N proof" in the product block wins. The XIV anniversary page carries a second, stale ABV block
   copied from XIII (137.2) after the real one — first match, not last. Barrel-proof pages say "Average 127
   proof" (the line varies barrel to barrel); the maker's own average is taken, the Michter's rule.
 - Age: almost never. Only the E series ("Age: Over 4 years" — a floor, read as 4, the Green River rule) and the
   two 2024 tasting-room releases ("matured ... for three years each"; a bare "for 14 years" in the XIV copy is the distillery's age, not the whiskey's) say a number; every other page says
   nothing and age stays unknown (never NAS, never from the 'N years' of 'fifteen years of 291').
 - Mash bill: percentages exist only on the Private Barrel Program page, for the barrel-proof single-barrel
   pair (rye 61% malted rye / 39% corn; bourbon 80% corn / 19% malted rye / 1% malt barley). Elsewhere only
   grain words ("high-rye", four-grain), which `normalize.mash_style()` reads or the page's own words give.
 - No og:image; the bottle is the first /content/uploads/ <img> after the logo ('new-handmade.jpg').

Judgment kept in the tables below:
 - Out of scope, deliberately not in REFILE: Fresh (un-aged, 'crafted to replace vodka, rum, or tequila') and
   White Dog (aged under two weeks) are new make, The Decc is a liqueur, /private-barrel/ is a program.
   The /whiskeys/ index is stale (it still prints HR Bourbon at 100 proof and Bad Guy 'approximately 120');
   it is not read.
 - A series is one bottling and the newest page wins the facts (pages are listed oldest first so the last one
   in `list_urls` is the current release): E Colorado Whiskey (Batches 12-15), the yearly Anniversary Release
   (XII-XV), Bad Guy (#9, #10). The earlier batches' titles are aliases.
 - 291 Big Horn was renamed 291 Ram Skull ("After a cease and desist letter ... Still the same recipe"); both pages
   are live. One bottling, Ram Skull, with Big Horn as an alias.
 - Good Guy's header says 'American Whiskey' but its copy says 'Good Guy Rye' and 'four-grain, wheated rye
   whiskey': rye. All Rye is '100% rye malt': a rye malt whiskey, read as rye. The class statement for the
   other pages is the page's own words ('Colorado Rye Whiskey', 'Colorado Bourbon Whiskey'); only the 2024 pair
   print 'Straight'.
 - The Aspen stave finish is on every page's header ('Finished with Aspen Wood Staves'); it is recorded as the
   finish, except the M (maple-syrup barrels) and the aspen-charcoal-mellowed American Whiskey."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Distillery 291"
DELAY = 6
SITEMAP = "https://distillery291.com/sitemap_index.xml"
IMAGE_PREFIX = "https://distillery291.com/"
CATALOG_FAMILIES = ["Distillery 291"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Distillery 291"

ASPEN = "Aspen Staves"
# slug → (expression, aliases, class statement, finish). Order matters inside a series: oldest first, newest last.
REFILE = {
    "colorado-rye-whiskey-small-batch-aspen-wood-staves": ("Colorado Rye Small Batch", [], "Colorado Rye Whiskey", ASPEN),
    "colorado-bourbon-whiskey-small-batch-aspen-wood-staves": ("Colorado Bourbon Small Batch", [], "Colorado Bourbon Whiskey", ASPEN),
    "colorado-rye-whiskey-barrel-proof-single-barrel": ("Colorado Rye Barrel Proof Single Barrel", [], "Colorado Rye Whiskey", ASPEN),
    "colorado-bourbon-whiskey-barrel-proof-single-barrel-finished-with-aspen-wood-staves": ("Colorado Bourbon Barrel Proof Single Barrel", [], "Colorado Bourbon Whiskey", ASPEN),
    "american-whiskey-aspen-charcoal-mellowed": ("American Whiskey", [], "American Whiskey", None),
    "colorado-straight-rye-whiskey-barrel-proof": ("Colorado Straight Rye Barrel Proof", [], "Straight Rye Whiskey", ASPEN),
    "colorado-straight-bourbon-whiskey-barrel-proof": ("Colorado Straight Bourbon Barrel Proof", [], "Straight Bourbon Whiskey", ASPEN),
    "m-colorado-whiskey": ("M Colorado Rye", ["Distillery 291 M Colorado Whiskey", "Distillery 291 “M” Colorado Whiskey", "Distillery 291 M Colorado Rye Whiskey"], "Colorado Rye Whiskey", "Maple Syrup Barrels"),
    "hr-bourbon-whiskey": ("HR Bourbon", ["Distillery 291 HR Bourbon Whiskey", "Distillery 291 High Rye Colorado Bourbon"], "Colorado Bourbon Whiskey", ASPEN),
    "product-291-big-horn-bourbon-whiskey": ("Ram Skull", ["Distillery 291 Big Horn", "Distillery 291 Big Horn Bourbon Whiskey"], "Colorado Bourbon Whiskey", ASPEN),
    "product-291-ram-skull-colorado-bourbon-whiskey": ("Ram Skull", ["Distillery 291 Ram Skull Colorado Bourbon Whiskey"], "Colorado Bourbon Whiskey", ASPEN),
    "product-291-all-rye-malt-colorado-whiskey": ("All Rye", ["Distillery 291 All Rye 100% Rye Malt Colorado Whiskey"], "Rye Malt Whiskey", ASPEN),
    "product-291-good-guy-american-whiskey": ("Good Guy", ["Distillery 291 Good Guy American Whiskey", "Distillery 291 Good Guy Rye"], "Rye Whiskey", ASPEN),
    "bad-guy-bourbon-whiskey": ("Bad Guy", ["Distillery 291 Bad Guy Batch 9", "Distillery 291 Bad Guy Bourbon Whiskey"], "Colorado Bourbon Whiskey", ASPEN),
    "bad-guy-bourbon-whiskey-10": ("Bad Guy", ["Distillery 291 Bad Guy Batch 10"], "Colorado Bourbon Whiskey", ASPEN),
    "291-e-colorado-whiskey": ("E Colorado Whiskey", ["Distillery 291 E Colorado Whiskey Batch 12"], "Colorado Bourbon Whiskey", ASPEN),
    "product-291-e-colorado-whiskey-batch-13": ("E Colorado Whiskey", ["Distillery 291 E Colorado Whiskey Batch 13"], "American Single Malt Whiskey", ASPEN),
    "product-291-e-colorado-whiskey-batch-14": ("E Colorado Whiskey", ["Distillery 291 E Colorado Whiskey Batch 14"], "Colorado Rye Whiskey", ASPEN),
    "product-291-e-colorado-whiskey-batch-15": ("E Colorado Whiskey", ["Distillery 291 E Colorado Whiskey Batch 15"], "Colorado Bourbon Whiskey", ASPEN),
    "product-xii-anniversary-colorado-whiskey": ("Anniversary Release", ["Distillery 291 XII Colorado Whiskey Anniversary Release"], "Colorado Rye Whiskey", ASPEN),
    "product-xiii-anniversary-colorado-whiskey": ("Anniversary Release", ["Distillery 291 XIII Colorado Whiskey Anniversary Release"], "Colorado Rye Whiskey", ASPEN),
    "product-xiv-anniversary-colorado-whiskey": ("Anniversary Release", ["Distillery 291 XIV Colorado Whiskey Anniversary Release"], "Colorado Rye Whiskey", ASPEN),
    "product-xv-anniversary-colorado-whiskey": ("Anniversary Release", ["Distillery 291 XV Colorado Whiskey Anniversary Release"], "Colorado Rye Whiskey", ASPEN),
}
CORE = {"Colorado Rye Small Batch", "Colorado Bourbon Small Batch", "Colorado Rye Barrel Proof Single Barrel",
        "Colorado Bourbon Barrel Proof Single Barrel", "American Whiskey"}
RARITY = [(r"small batch|american whiskey", "shelf"), (r".", "limited")]
# Percentages the Private Barrel Program page prints for the barrel-proof single-barrel pair.
MASH_BILLS = {
    "Colorado Rye Barrel Proof Single Barrel": "61% Malted Rye, 39% Corn",
    "Colorado Bourbon Barrel Proof Single Barrel": "80% Corn, 19% Malted Rye, 1% Malted Barley",
}
# Words the page uses for the grain bill where there are no percentages.
MASH_WORDS = {
    "Ram Skull": "High-Rye Mash Bill",
    "HR Bourbon": "High Rye Mash Bill",
}
FOUR_GRAIN = {"Bad Guy"}
_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def list_urls(fetcher) -> list[str]:
    return [f"https://distillery291.com/{slug}/" for slug in REFILE]


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _years(block: str) -> tuple[float | None, str | None]:
    m = re.search(r"\bAge:\s*(?:Over\s+|At least\s+)?(\d{1,2})\s*years?", block, re.I)
    if not m:
        m = re.search(r"\bfor\s+(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten)\s+years\s+each\b", block, re.I)
    if not m:
        return None, None
    raw = m.group(1).lower()
    y = float(raw) if raw.isdigit() else float(_NUM[raw])
    return y, f"{int(y)} yr"


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw, finish = REFILE[slug]
    name = f"Distillery 291 {expression}"

    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    own = html.unescape(re.sub(r"<[^>]+>", "|", body))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)
    # the product block: after the nav, before the carousel of other products
    start = own.find("Select Page|")
    block = own[start + 12:] if start >= 0 else own
    for stop in ("ADDITIONAL|", "EXPLORE MORE OF"):
        j = block.find(stop)
        if j > 0:
            block = block[:j]

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof\b", block, re.I)
    proof = float(pm.group(1)) if pm else None
    years, label = _years(block)

    mash_raw = MASH_BILLS.get(expression) or MASH_WORDS.get(expression)
    mash_style = None
    if "Rye" in class_raw:
        mash_style = "rye"
    elif expression in FOUR_GRAIN:
        mash_style = "four_grain"
        mash_raw = "Corn, Malted Wheat, Malted Rye, Beech Smoked Barley"

    img = None
    after_nav = body.split("Select Page", 1)[-1]
    for m in re.finditer(r'<img[^>]+src="(https://distillery291\.com/content/uploads/[^"]+)"', after_nav):
        if "new-handmade" not in m.group(1) and "Mockup" not in m.group(1):
            img = m.group(1)
            break

    desc = _text(re.split(r"SHOP NOW\||SOLD OUT\||SHOP WHISKEY\|", block, 1)[-1][:700].replace("|", " "))

    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name,
        source_url=f"https://distillery291.com/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style=mash_style, description=desc, finish=finish,
        image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
