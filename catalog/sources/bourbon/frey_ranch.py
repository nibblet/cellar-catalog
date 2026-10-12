"""freyranch.com (Frey Ranch Estate Distillery, Fallon, Nevada; a WordPress site) and shop.freyranch.com (the
distillery's own Shopify store, linked from every page). robots.txt on both allows everything and sets no Crawl-delay
(the store's carries Shopify's usual checkout/cart disallows and a note about agents), so DELAY is the project's 6.
Each page of the main site opens with an "ARE YOU 21 YEARS OF AGE OR OLDER?" overlay in its static HTML; the copy is
served regardless and nothing here clicks through it.

Two sources, because neither is complete. The main site has one page per standing bottling (Straight Bourbon, Straight
Rye, Farm Strength Uncut Bourbon) with a spec tile ("90 | PROOF"); it has no page for the single-grain whiskeys or the
Farm Strength Rye. The store carries those, as Shopify products read through their `.json` endpoint (the copy is the
`body_html`; the Rabbit Hole precedent). The store's bundles, merchandise, honey and one-barrel "Friends of Frey" / flavored
single-barrel pick listings are not bottlings and are not crawled.

What each page states, and what it does not:
  - Straight Bourbon: "90 | PROOF" and "Aged for 5 years, this 90-proof bourbon". The store's 375 ml page says "an average
    of five years"; the main page's plain statement is read (the seed said 4). A four-grain mash bill is named without
    percentages, so only the style (four_grain) is carried.
  - Bottled-in-Bond Straight Rye: "100 | PROOF", "Frey Ranch Bottled-In-Bond Straight Rye Whiskey ... 100% Winter Cereal
    Rye ... aged for a minimum of five years". Bottled in Bond is 100 proof; "a minimum of five years" is a floor, so no
    age is read (and it is not the legal four-year floor either). No catalog row existed; it is a new, core bottling.
  - Farm Strength Uncut Bourbon: the tile reads "120 - 132 PROOF" and the store says "Typically ranges from 120-132
    Proof": a range states no proof, so the row is listed and not confirmed (the seed's 124.6, from Batch 17, stays) and no
    age is stated (the seed's 4 yr stays; see the hand-off).
  - Farm Strength Uncut Rye (store: "Frey Ranch Farm Strength Rye"): "bottled straight from the barrel at 124.52 proof
    (batch dependent) ... Aged for six years ... 100% Cereal Winter Rye". The caveat is the maker's; the number is printed,
    so it is read (rounded to one decimal, 124.5 = the seed). Judgment call, flagged for the owner.
  - 100% Barley Whiskey (store, 375 ml "vault"): states neither proof nor age; the seed 'Single Grain Series 100% Barley'
    (110 proof, 4.67 yr) is listed, not confirmed. The mash bill is the page's ("100% two-row unmalted barley").
  - 100% Wheat Whiskey (store, 375 ml, sold out): "Aged for 4 years and 8 months at 120 proof ... an expression of the
    Single Grain Series" - stated, so a new limited row (not core). Named like the seeded barley row.
Not imported: Single Barrel whiskeys / the Single Barrel Program (a program, every barrel differs and no proof is
stated), the Harvester Series, Quad Malt, 100% Malted Corn, the American Single Malt and the Five Grain Single Barrel (no
page on either site: they stay seeds), flavored single barrels (#848 Cream Soda, #849 Buttered Popcorn), the one-off
"Friends of Frey" Terry Memorial barrel, 3L/bundles. The single-malt/malted-corn seeds are not claimed by anything here.

tasting_notes is the bottle's own nose / palate / finish copy: on the main site the tasting paragraph under the "Double
Distilled for a Higher Quality Whiskey." tile (its mash-bill sentence dropped), in the store the "Nose:/Palate:/Finish:" or
"Tasting Notes:" lines of the `body_html`. The Bottled-in-Bond Rye and Barley pages state none, so those stay None."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof as parse_proof

PRODUCER = "Frey Ranch"
DELAY = 6
BASE = "https://freyranch.com/"
SHOP = "https://shop.freyranch.com/products/"
IMAGE_PREFIX = "https://"
CATALOG_FAMILIES = ["Frey Ranch"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Frey Ranch"

FOUR_GRAIN = "Four-grain: non-GMO corn, winter cereal rye, winter wheat, two-row barley"
# key → (expression, [catalog names it answers to], class statement, mash statement)
MAIN = {
    "straight-bourbon-whiskey": ("Straight Bourbon", ["Frey Ranch Four Grain Straight Bourbon Whiskey", "Frey Ranch Straight Bourbon Whiskey"],
                                 "Straight Bourbon Whiskey", FOUR_GRAIN),
    "straight-rye-whiskey": ("Bottled in Bond Straight Rye", ["Frey Ranch Bottled-in-Bond Straight Rye Whiskey", "Frey Ranch Straight Rye"],
                             "Bottled in Bond Straight Rye Whiskey", "100% Winter Cereal Rye"),
    "farm-strength-uncut-bourbon": ("Farm Strength Uncut", ["Frey Ranch Farm Strength Uncut Bourbon"], "Straight Bourbon Whiskey", FOUR_GRAIN),
}
SHOPPED = {
    "frey-ranch-farm-strength-rye": ("Farm Strength Uncut Rye", ["Frey Ranch Farm Strength Rye"], "Straight Rye Whiskey", "100% Cereal Winter Rye"),
    "100-barley-375ml-vault": ("Single Grain Series 100% Barley", ["Frey Ranch 100% Barley Whiskey"], "Barley Whiskey", "100% two-row unmalted barley"),
    "100-wheat-whiskey-vault": ("Single Grain Series 100% Wheat", ["Frey Ranch 100% Wheat Whiskey"], "Wheat Whiskey", "100% Soft White Winter Wheat"),
}
# Cached as evidence only (no records): the Single Barrel pages and the store's Farm Strength Uncut and Bourbon/Rye pages.
EVIDENCE = [BASE + "single-barrel-whiskeys/", BASE + "single-barrel-program/", SHOP + "frey-ranch-farm-strength-uncut.json",
            SHOP + "frey-ranch-straight-bourbon-whiskey.json", SHOP + "frey-ranch-bottled-in-bond-straight-rye-whiskey.json"]

DISCONTINUED_BY_MAKER = set()
CORE = {"Straight Bourbon", "Bottled in Bond Straight Rye", "Farm Strength Uncut"}
RARITY = [(r"single grain|farm strength uncut rye", "limited"), (r"farm strength", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [*(BASE + s + "/" for s in MAIN), *(SHOP + h + ".json" for h in SHOPPED), *EVIDENCE]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _main_copy(flat: str) -> str:
    """The bottle's own block: from its title to the cocktail/footer tail."""
    start = flat.find("ALC/VOL")
    start = flat.rfind("CONTACT|", 0, start) if start > 0 else 0
    part = flat[start:]
    for stop in ("Farm Fresh Cocktails", "Frey|", "'Be Good to the Land"):
        j = part.find(stop)
        if j > 0:
            part = part[:j]
    return part


def _main_notes(own: str) -> str | None:
    """The tasting paragraph is the cell after the "Double Distilled ..." tile; its mash-bill sentence is not taste."""
    m = re.search(r"Higher Quality Whiskey\.\| ([^|]+)\|", own)
    if not m:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", m.group(1).strip())
    t = " ".join(x for x in sentences if not re.search(r"mash bill|grown|grains", x, re.I))
    return t if re.search(r"\b(?:aromas?|nose|palate|finish|notes of)\b", t, re.I) else None


def _shop_notes(body_html: str) -> str | None:
    """Nose / Palate / Finish (or a single "Tasting Notes:" line) from the product copy; each label is its own cell."""
    cells = [c.strip() for c in re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "|", body_html))).replace("’", "'").split("|") if c.strip()]
    got = []
    for label in ("Nose", "Palate", "Finish", "Tasting Notes"):
        i = next((k for k, c in enumerate(cells[:-1]) if c.rstrip(":").strip() == label and c.endswith(":")), None)
        if i is not None:
            got.append(f"{label}: {cells[i + 1]}")
    return " ".join(got)[:900] or None


def _image(page: str) -> str | None:
    for src in re.findall(r'<img[^>]+(?:data-src|src)="(https://freyranch\.com/wp-content/uploads/[^"]+\.(?:png|jpg|jpeg|gif|webp))"', page):
        if not re.search(r"yellow|btn|ascot|sticker|icon|award|medal|logo|competition|topper|sig", src, re.I):
            return src
    return None


def _months(text: str) -> tuple[float | None, str | None]:
    m = re.search(r"aged for (\d{1,2}) years? and (\d{1,2}) months?", text, re.I)
    if not m:
        return None, None
    years = round(int(m.group(1)) + int(m.group(2)) / 12, 2)
    return years, f"{years} yr"


def _shop(url: str, page: str) -> BottlingRecord | None:
    handle = url.replace(SHOP, "").removesuffix(".json")
    if handle not in SHOPPED:
        return None
    expression, aliases, class_raw, mash = SHOPPED[handle]
    prod = json.loads(page)["product"]
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", prod.get("body_html") or ""))).strip()
    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", text, re.I)
    proof = round(float(pm.group(1)), 1) if pm and not re.search(r"\d\s*[-–]\s*\d{2,3}\s*proof", text, re.I) else None
    years, label = _months(text)
    if years is None:
        years, label = age(text.replace("Aged for", "aged for")) if handle == "frey-ranch-farm-strength-rye" else (None, None)
    img = (prod.get("images") or [{}])[0].get("src")
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=f"{FAMILY} {expression}", source_url=SHOP + handle, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash, tasting_notes=_shop_notes(prod.get("body_html") or ""), image_url=img,
        aliases=sorted(set(aliases) - {f"{FAMILY} {expression}"}), is_core_range=expression in CORE,
    )


def parse(url: str, page: str) -> BottlingRecord | None:
    if url.startswith(SHOP):
        return _shop(url, page)
    slug = url.replace(BASE, "").strip("/")
    if slug not in MAIN:
        return None
    expression, aliases, class_raw, mash = MAIN[slug]
    own = _main_copy(_flat(page))

    tile = re.search(r"ALC/VOL\| ([\d.\s\-–]+)\| PROOF", own)
    proof = parse_proof(tile.group(1) + " proof") if tile else None  # "120 - 132" is a range: None

    years = label = None
    if slug == "straight-bourbon-whiskey":
        years, label = age(re.search(r"Aged for \d+ years", own).group(0)) if re.search(r"Aged for \d+ years", own) else (None, None)
    # Bottled-in-Bond Rye: "a minimum of five years" is a floor, never an age.

    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=f"{FAMILY} {expression}", source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash, tasting_notes=_main_notes(own), image_url=_image(page),
        aliases=sorted(set(aliases) - {f"{FAMILY} {expression}"}), is_core_range=expression in CORE,
    )
