"""middlewestspirits.com (Middle West Spirits, Columbus, Ohio). A server-side age gate answers every URL with a
136-character "Yes, I am 21 years of age or older" page, so `crawl.py` cannot fill this cache. With the owner's
explicit approval (2026-10-13: "we should click through") the gate's own confirmation button was clicked in the app's
browser pane and each whiskey page was READ BY HAND (a normal browser at human pace; nothing was scripted, spoofed or
automated) and the main-content text saved into the cache under the page's URL (cache/mw), as was done for
Jefferson's. `Fetcher.get` serves cached text, so this module parses it like a crawled page; a re-read means
refreshing those files by hand the same way.

Every page has a SPECIFICATIONS block with `ABV 61.1% (122.20 proof)`, a MINIMUM MATURATION TIME (a floor, never an
age) and a MASH BILL that lists grains without percentages. Age is read only where the copy says "is/It's aged N
years" (the Sherry, Ported Rye and Napoleon Calvados finishes); "aged over five years" (Vino de Naranja) and a bare
minimum (the cask strengths, the 96 rye, Oloroso) state none. The two seeded Sherry rows (97.2 and 97.3, both 6 year)
are one bottle, 97.25 proof on the page. Not imported: Bourbon Cream and the unaged White Rye (less than one day)."""
from __future__ import annotations

import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Middle West Spirits"
DELAY = 6
SITEMAP = "https://middlewestspirits.com/sitemap.xml"
CATALOG_FAMILIES = ["Middle West"]
PRODUCER_BY_FAMILY = {}

BASE = "https://middlewestspirits.com/spirits/whiskey/"
BOURBON = "Straight Wheated Bourbon Whiskey"
# slug → (expression, name, aliases, class, finish, core)
PAGES = {
    "middle-west-spirits-bourbon/": ("Michelone Reserve", "Middle West Spirits Michelone Reserve",
                                     ["Michelone Reserve", "Middle West Spirits Bourbon, Michelone Reserve"], BOURBON, None, True),
    "cask-strength-straight-wheated-bourbon/": ("Cask Strength Straight Wheated", "Middle West Spirits Cask Strength Straight Wheated",
                                                [], BOURBON, None, False),
    "cask-strength-dark-pumpernickel-rye-whiskey/": ("Dark Pumpernickel Cask Strength Rye", "Middle West Spirits Dark Pumpernickel Cask Strength Rye",
                                                     [], "Straight Rye Whiskey", None, False),
    "cask-strength-straight-wheat-whiskey/": ("Straight Wheat Whiskey Cask Strength", "Middle West Spirits Straight Wheat Whiskey Cask Strength",
                                              [], "Straight Wheat Whiskey", None, False),
    "middle-west-spirits-dark-pumpernickel-rye-whiskey/": ("Dark Pumpernickel Rye", "Middle West Spirits Dark Pumpernickel Rye",
                                                           [], "Dark Pumpernickel Rye Whiskey", None, True),
    "middle-west-spirits-straight-wheat-whiskey/": ("Straight Wheat Whiskey", "Middle West Spirits Straight Wheat Whiskey",
                                                    [], "Straight Wheat Whiskey", None, True),
    "mws-sherry-finished-bourbon-whiskey/": ("Double Cask Collection: Sherry Cask-Finished", "Middle West Spirits Double Cask Collection: Sherry Cask-Finished",
                                             ["Middle West Spirits 6 Year Sherry Cask Finished"], "Sherry Finished Bourbon Whiskey", None, True),
    "mws-ported-pumpernickel-rye-whiskey/": ("Double Cask Collection: Ported Pumpernickel Rye", "Middle West Spirits Double Cask Collection: Ported Pumpernickel Rye",
                                             [], "Ported Pumpernickel Rye Whiskey", "Tawny Port Casks", False),
    "mws-oloroso-wheat-whiskey/": ("Double Cask Collection: Oloroso Wheat", "Middle West Spirits Double Cask Collection: Oloroso Wheat",
                                   [], "Oloroso Wheat Whiskey", "Oloroso Sherry Casks", False),
    "double-cask-collection-vino-de-naranja-cask-finished-whiskey/": ("Vino De Naranja", "Middle West Spirits Vino De Naranja",
                                                                      [], "Cask-Finished Whiskey", None, False),
    "double-cask-collection-napoleon-calvados-cask-finished-whiskey/": ("Double Cask Collection: Napoleon Calvados Cask-Finished",
                                                                         "Middle West Spirits Double Cask Collection: Napoleon Calvados Cask-Finished",
                                                                         [], "Cask-Finished Whiskey", None, False),
}
CORE = {v[0] for v in PAGES.values() if v[5]}
RARITY = [(r"cask strength|double cask|vino|ported|oloroso|napoleon", "limited"), (r".", "shelf")]
MASH_BILLS = {}
NUMBER = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def list_urls(fetcher) -> list[str]:
    return [BASE + slug for slug in PAGES]


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.replace(BASE, "")
    if slug not in PAGES:
        return None
    expression, name, aliases, class_raw, finish, _core = PAGES[slug]
    copy = page.split("SPECIFICATIONS", 1)[0]
    m = re.search(r"\(\s*(\d{2,3}(?:\.\d+)?)\s*proof\s*\)", page, re.I)
    proof = float(m.group(1)) if m else None
    years = label = None
    a = re.search(r"\baged (one|two|three|four|five|six|seven|eight|nine|ten) years\b", copy, re.I)  # "aged over five years" is a floor
    if a:
        years = float(NUMBER[a.group(1).lower()])
        label = f"{int(years)} yr"
    desc = re.sub(r"\s+", " ", copy).strip() or None
    return BottlingRecord(
        brand_family="Middle West", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, finish=finish, description=desc,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
