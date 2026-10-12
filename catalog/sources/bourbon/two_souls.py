"""twosoulsspirits.com (Two Souls Spirits, Columbus OH — "Independent Craft Whiskey Bottlers": it buys single barrels from
other craft distilleries and sells each one as its own numbered release, "Featuring <distillery>"). The domain is the
bottler's own Shopify storefront. robots.txt is Shopify's template (no Crawl-delay, DELAY is the project's usual 6; its
comments ask agents to use the UCP/MCP endpoint for catalog and checkout, which concerns buying, and nothing here touches a
cart or checkout). Every product is fetched as its `.json` endpoint (Rabbit Hole precedent); `body_html` carries the
copy and a "The Nerdy Bits" block that states the barrel's own facts:
"Mash Bill: 64% red corn, 14% wheat, 14% rye, 8% malted barley ... Age: 8 years, 5 months, 2 days ... ABV: 50.5 Proof: 121".

Producer. The catalog was told to file this family under Watershed Distillery (maker id 5a206d20...), but Watershed is the
distillery of three of the 22 releases; the others are J. Henry & Sons, Yahara Bay, Finger Lakes, J. Carver, Wollersheim,
Rush Creek, High Wire, BlackFork, Middle West, Kozuba, Sutherland and Manifest. Attributing them all to Watershed would be
false, so PRODUCER is "Two Souls Spirits" (the bottler the site names) and the writer is run WITHOUT --maker (producer_id
stays null; the two seed rows that already carry Watershed / Finger Lakes producers keep them: the writer only fills nulls).

What a row is. One release = one single barrel = one bottling (the Breaking Bourbon seeds are one per release). All 19
seeds answer to a live product page, found by proof + age + mash bill, never by name alone:
  proof 128.58 Watershed double-barreled; 130.34 Manifest ProBear Rasslin'; 126.7 Middle West O-H-Rye-O; 137.4 Rush Creek;
  121 J. Henry Road's End; 125.28 J. Carver single malt; 127.68 J. Carver wheated; 128 J. Carver wheat whiskey; 105.30 Finger
  Lakes rye; 121.4 High Wire Jimmy Red; 124.32 BlackFork; 138.12 Sutherland maple ("Son of Ghost Barrel"); 123.48 Kozuba
  light whiskey; 105.66 Finger Lakes wheated; 114.86 Finger Lakes honey-finished rye; 123.04 Watershed; 147.18 Yahara Bay
  8 year rye; 126.22 Wollersheim maple rye; 118.4 Wollersheim "Wisconsin Waffles".
Each record carries the seed's own expression and name (PAGES), so nothing is renamed; the maker's title is an alias. The
seed names are the Breaking Bourbon titles ("Two Souls Spirits New York" is the 8 year wheated bourbon); tidying them is an
owner item, not an importer judgment.

Age. Read from the Nerdy Bits "Age:" field as years + months/12 (days dropped, two decimals: 6 years, 1 month = 6.08), which is
how the seeds were computed. Where the seed was a whole number and the page says "4 years, 4 months" (Watershed) or
"8 years, 2 months" (Yahara Bay) the importer corrects it; "Age: 6 years" (honey) stays whole.

Class. "Single Malt Whiskey" (J. Carver, Watershed), "Light Whiskey" (Kozuba), "Wheat Whiskey", "Rye Whiskey", "Straight
Bourbon Whiskey" / "Bourbon Whiskey" as the product type and title say. The four-grain statements ("4-grain mash bill",
"This 4-grain bourbon") set mash_style four_grain (normalize reads only "four-grain").

Not imported, and why:
- Retired and unseeded: 10-Year Wisconsin Rye in used Cabernet (147.28), 8-Year Wisconsin Rum Cask Rye (146.96), 5-Year
  Kentucky Triple Cask Rye (127.9), 6-Year California Ghost Barrel bourbon (126.82), 6-Year J. Henry & Sons Cigar Bourbon
  (121.14), 6-Year Ohio Apple Brandy single malt (114.8): real releases, each a sold-out single barrel with no catalog row.
  Adding six hidden-lineage one-offs as browsable rows is an owner decision; the handles are in the hand-off.
- Not whiskey: Yahara Bay 5- and 6-Year Honey Spirit (mead spirit), 7-Year Wisconsin Rum, the T-shirt.
- The store files 22 whiskeys under a "Retired Spirits" collection. The pages are still live and state full specs, so none is
  marked discontinued (DISCONTINUED_BY_MAKER is empty); whether the maker's "retired" shelf should set the flag is an owner
  decision.

Added: the two J. Henry & Sons 7-Year rum-cask releases (bourbon 115.32, rye 124.58), in stock now and in the "Inner Circle"
collection, have no seed row.

Nothing is core: every release is a one-off barrel.

`tasting_notes` is the barrel's own "Tasting Notes:" paragraph from `body_html` (read up to the end of that block, so the
sales copy and "The Nerdy Bits" that follow are never part of it)."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Two Souls Spirits"
DELAY = 6
SITEMAP = "https://twosoulsspirits.com/collections/available-spirits/products.json"  # not crawled; list_urls is fixed
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["Two Souls"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Two Souls"
PRODUCT_URL = "https://twosoulsspirits.com/products/{}.json"

BOURBON = "Bourbon Whiskey"
STRAIGHT_BOURBON = "Straight Bourbon Whiskey"
RYE = "Rye Whiskey"
STRAIGHT_RYE = "Straight Rye Whiskey"

# handle -> (seed expression, seed name, extra aliases, class statement, finish, mash style the page states)
PAGES = {
    "6-year-ohio-double-barreled-bourbon-whiskey-featuring-watershed-distillery": (
        "Double Barreled Bourbon Featuring Watershed Distillery", "Two Souls Double Barreled Bourbon Featuring Watershed Distillery",
        ["Two Souls 6-Year Ohio Double Barreled Bourbon Whiskey Featuring Watershed Distillery"], BOURBON, "Used Watershed Bourbon Barrel (double barreled)", None),
    "5-year-double-barreled-straight-bourbon": (
        "Double Barreled Bourbon Professional Bear Rasslin", "Two Souls Double Barreled Bourbon Professional Bear Rasslin",
        ["Two Souls 5-Year Double Barreled Straight Bourbon Featuring Manifest Distilling"], BOURBON, "J. Henry & Sons Road's End Barrel (double barreled)", "four_grain"),
    "5-year-ohio-pumpernickel-rye-whiskey-featuring-middle-west-spirits": (
        "Double Barreled Pumpernickel Rye Featuring Middle West Spirits O-H-Rye-O", "Two Souls Double Barreled Pumpernickel Rye Featuring Middle West Spirits O-H-Rye-O",
        ["Two Souls 5-Year Ohio Double Barreled Pumpernickel Rye Whiskey Featuring Middle West Spirits"], RYE, "Used Rye Barrel (YB1)", None),
    "6-year-illinois-straight-bourbon-whiskey-featuring-rush-creek-distilling": (
        "Featuring Rush Creek Distilling Bold Rush", "Two Souls Featuring Rush Creek Distilling Bold Rush",
        ["Two Souls 6-Year Illinois Straight Bourbon Whiskey Featuring Rush Creek Distilling"], STRAIGHT_BOURBON, None, None),
    "8-year-wisconsin-straight-bourbon-whiskey-featuring-j-henry-sons": (
        "J. Henry & Sons 8 Year Bourbon Road's End", "Two Souls J. Henry & Sons 8 Year Bourbon Road's End",
        ["Two Souls 8-Year Wisconsin Straight Bourbon Whiskey Featuring J. Henry & Sons"], STRAIGHT_BOURBON, None, "four_grain"),
    "6-year-minnesota-american-single-malt-finished-in-a-used-bourbon-barrel-featuring-j-carver-distillery": (
        "Minnesota American Single Malt Rich Mahogany", "Two Souls Minnesota American Single Malt Rich Mahogany",
        ["Two Souls 6-Year Minnesota American Single Malt Finished in a Used Bourbon Barrel Featuring J. Carver Distillery"], "Single Malt Whiskey", "Used Bourbon Barrel", None),
    "8-year-minnesota-straight-wheated-bourbon-whiskey-featuring-j-carver-distillery": (
        "Minnesota Straight Bourbon Give ‘Em the Wheater", "Two Souls Minnesota Straight Bourbon Give ‘Em the Wheater",
        ["Two Souls 8-Year Minnesota Straight Bourbon Whiskey Featuring J. Carver Distillery"], STRAIGHT_BOURBON, None, None),
    "8-year-minnesota-straight-wheat-whiskey-featuring-j-carver-distillery": (
        "Minnesota Straight Wheat Whiskey Packin' Wheat", "Two Souls Minnesota Straight Wheat Whiskey Packin' Wheat",
        ["Two Souls 8-Year Minnesota Straight Wheat Whiskey Featuring J. Carver Distillery"], "Straight Wheat Whiskey", None, None),
    "6-year-new-york-straight-rye-whiskey-featuring-finger-lakes-distilling-pre-order": (
        "New York Rye", "Two Souls New York Rye",
        ["Two Souls 6-Year New York Straight Rye Whiskey Featuring Finger Lakes Distilling"], STRAIGHT_RYE, None, None),
    "5-year-south-carolina-100-jimmy-red-bourbon-featuring-high-wire-distilling": (
        "South Carolina Straight Bourbon Notorious C.O.B.", "Two Souls South Carolina Straight Bourbon Notorious C.O.B.",
        ["Two Souls 5-Year South Carolina 100% Jimmy Red Bourbon Featuring High Wire Distilling"], STRAIGHT_BOURBON, None, None),
    "6-year-south-dakota-straight-bourbon-whiskey-featuring-blackfork-spirits": (
        "South Dakota Straight Bourbon The Black Queen", "Two Souls South Dakota Straight Bourbon The Black Queen",
        ["Two Souls 6-Year South Dakota Straight Bourbon Whiskey Featuring BlackFork Farms"], STRAIGHT_BOURBON, None, "four_grain"),
    "6-year-california-bourbon-finished-in-maple-bourbon-barrel-featuring-sutherland-distilling": (
        "Bourbon Son of Ghost Barrel", "Two Souls Spirits Bourbon Son of Ghost Barrel",
        ["Two Souls 7-Year California Bourbon Maple Cask Finished Bourbon Featuring Sutherland Distilling"], BOURBON, "Used Maple Bourbon Barrel", None),
    "3-year-florida-light-whiskey-featuring-kozuba-sons-distillery": (
        "Light Whiskey Red Light Green Light", "Two Souls Spirits Light Whiskey Red Light Green Light",
        ["Two Souls 3-Year Florida Light Whiskey Featuring Kozuba & Sons Distillery"], "Light Whiskey", "Watershed Bourbon Barrel", None),
    "8-year-new-york-wheated-bourbon": (
        "New York", "Two Souls Spirits New York",
        ["Two Souls 8-Year New York Wheated Bourbon Featuring Finger Lakes Distilling"], "Wheated Bourbon Whiskey", None, None),
    "7-year-new-york-rye-finished-in-a-used-honey-spirit-barrel-featuring-finger-lakes-distilling": (
        "New York Rye Finished in a Used Honey Spirit Barrel Five Golden Grains", "Two Souls Spirits New York Rye Finished in a Used Honey Spirit Barrel Five Golden Grains",
        ["Two Souls 7-Year New York Rye Finished in a Used Honey Spirit Barrel Featuring Finger Lakes Distilling"], RYE, "Used Honey Spirit Barrel", None),
    "ohio-straight-bourbon-whiskey": (
        "Watershed Distillery", "Two Souls Spirits Watershed Distillery",
        ["Two Souls 4-Year Ohio Straight Bourbon Whiskey Featuring Watershed Distillery"], STRAIGHT_BOURBON, None, None),
    "8-year-wisconsin-straight-rye-whiskey-featuring-yahara-bay-distillers": (
        "Wisconsin Rye", "Two Souls Spirits Wisconsin Rye",
        ["Two Souls 8-Year Wisconsin Straight Rye Whiskey Featuring Yahara Bay Distillers"], STRAIGHT_RYE, None, None),
    "6-year-wisconsin-rye-finished-in-a-maple-bourbon-barrel-featuring-wollersheim-distilling": (
        "Wisconsin Rye Shortstack", "Two Souls Spirits Wisconsin Rye Shortstack",
        ["Two Souls 6-Year Wisconsin Rye Maple Bourbon Finished Featuring Wollersheim Distilling"], RYE, "Used Maple Bourbon Barrel", None),
    "6-year-wisconsin-straight-rye-whiskey-featuring-wollersheim-distillery": (
        "Wisconsin Straight Rye Whiskey Featuring Wollersheim Distillery Wisconsin Waffles", "Two Souls Spirits Wisconsin Straight Rye Whiskey Featuring Wollersheim Distillery Wisconsin Waffles",
        ["Two Souls 6-Year Wisconsin Straight Rye Whiskey Featuring Wollersheim Distillery"], STRAIGHT_RYE, None, None),
    # in stock now, no seed row
    "j-henry-sons-7-year-rum-finished-bourbon": (
        "J. Henry & Sons 7 Year Rum Cask Finished Bourbon", "Two Souls J. Henry & Sons 7 Year Rum Cask Finished Bourbon",
        ["Two Souls J Henry & Sons 7-Year Rum-Cask Finished Bourbon"], BOURBON, "Rum Cask", None),
    "j-henry-sons-7-year-rum-cask-rye": (
        "J. Henry & Sons 7 Year Rum Cask Finished Rye", "Two Souls J. Henry & Sons 7 Year Rum Cask Finished Rye",
        ["Two Souls J Henry & Sons 7-Year Rum-Cask Finished Rye"], RYE, "Rum Cask", None),
}
CORE: set[str] = set()
DISCONTINUED_BY_MAKER: set[str] = set()
RARITY = [(r".", "limited")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [PRODUCT_URL.format(h) for h in PAGES]


def _flat(body_html: str | None) -> str:
    body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", body_html or "", flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", body)).replace("\xa0", " ").replace("’", "'").replace("​", "").replace("﻿", "")
    return re.sub(r"\s+", " ", t)


def _nerdy(own: str) -> str:
    i = own.find("Nerdy Bits")
    return own[i:] if i >= 0 else ""


def _field(nerdy: str, label: str) -> str | None:
    m = re.search(rf"\b{label}:\s*(.*?)(?=\s+(?:Mash Bill|Base|Fill Date|Transfer Date|Initial Transfer Date|Secondary Transfer Date|Finishing Time|Bottle Date|Age|Barrel #|Barrel Info|Barrel Char|Entry Proof|ABV|Proof|Yield|[A-Z][\w.]* (?:Barrel #|#))\b|$)", nerdy)
    return m.group(1).strip() if m else None


def _mash(nerdy: str) -> str | None:
    raw = _field(nerdy, "Mash Bill")
    if not raw or not re.search(r"\d", raw):
        return None
    raw = re.sub(r"\s+", " ", raw).strip(" .")
    if "%" not in raw:  # "64 Red Corn, 14 Wheat" -> "64% Red Corn, 14% Wheat"
        raw = re.sub(r"(\d+(?:\.\d+)?)\s+(?=[A-Za-z])", r"\1% ", raw)
    # normalize.mash_style() reads "100% Rye Malt" as "00% rye" (a 0% rye): say "Malted Rye", which it does not read as a rye grain
    return re.sub(r"(\d+%)\s+Rye Malt\b", r"\1 Malted Rye", raw)


def _age(nerdy: str) -> tuple[float | None, str | None]:
    """'Age: 8 years, 5 months, 2 days' -> (8.42, '8 yr 5 mo'); days are dropped, the seeds did the same."""
    m = re.search(r"\bAge:\s*(\d+)\s*years?(?:,\s*(\d+)\s*months?)?", nerdy)
    if not m:
        return None, None
    y, mo = int(m.group(1)), int(m.group(2) or 0)
    years = round(y + mo / 12, 2)
    label = f"{y} yr" + (f" {mo} mo" if mo else "")
    return years, label


def _tasting(body_html: str | None) -> str | None:
    m = re.search(r"Tasting Notes\s*:?(?:\s|&nbsp;|\xa0)*(.*?)(?:</p>|</div>|</li>|<br\s*/?>|<p[\s>]|<div[\s>])", body_html or "", re.S | re.I)
    if not m:
        return None
    text = re.sub(r"^:\s*", "", _flat(m.group(1))).strip()
    text = re.sub(r"^([A-Z]) (?=[a-z])", r"\1", text)  # a styled drop cap splits the first letter off ("C orn fritters")
    return text[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1].removesuffix(".json")
    if handle not in PAGES:
        return None
    expression, name, aliases, class_raw, finish, style = PAGES[handle]
    data = json.loads(page)["product"]
    own = _flat(data.get("body_html"))
    nerdy = _nerdy(own)

    pm = re.search(r"(?<!Entry )\bProof:\s*(\d{2,3}(?:\.\d+)?)", nerdy)
    proof = float(pm.group(1)) if pm else None
    years, label = _age(nerdy)
    mash = _mash(nerdy)
    img = (data.get("image") or {}).get("src") or ((data.get("images") or [{}])[0].get("src"))
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=f"https://twosoulsspirits.com/products/{handle}",
        proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash, mash_style=style, finish=finish,
        tasting_notes=_tasting(data.get("body_html")), image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=False)
