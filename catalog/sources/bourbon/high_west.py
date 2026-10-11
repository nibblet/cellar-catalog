"""highwest.com + ship.highwest.com (High West Distillery, Park City / Wanship, Utah — Constellation Brands).
highwest.com is a Shopify storefront whose own product catalogue is empty (`/products.json` is `[]`, the
sitemap lists no products; its shop buttons hand off to ship.highwest.com, High West's online store
"powered by Flaviar", also Shopify and also the maker's own host). Facts come from three places:

* ship.highwest.com `/products/<handle>` — one page per bottle on sale. A "Bottle Details" block gives
  `ABV: 46%` / `Proof: 92` (or just `ABV 49.3%`, `58.5 ABV`, or nothing for High Country and the Bonded
  Rye, whose proof is in the copy: "bottled at 100 proof"), a "Mash Bill" block (percentages per sourced
  component, sometimes empty) and a "Back Label Story". The store's `ABV-N` product *tags* are not read:
  the Cask Strength tag says ABV-49 on a 58.5 % bottle.
* highwest.com/pages/limited-releases — current limited releases with the age and ABV in the copy
  (Bourye, The Prisoner's Share, Bottled in Bond Bourbon).
* highwest.com/pages/product-information — the compliance list: one line per label, "<class statement>
  N% Alc/Vol". It supplies the proof for the bottles with no proof of their own (Noble Share, Yippee
  Ki-Yay, Valley Tan, Silver Western Oat, High Country) and is read, when cached, for the ship page that
  states none. Its "Barrel Select" and "Cask Collection" lines carry an unfilled "[INSERT barrel type]"
  placeholder — they are programs (store picks), not bottlings, and are skipped, as are the barrel-finished
  cocktails, Western Joe (RTD), Mountain Gin and 7000' (Oat Flavored) vodka.

Spirit type. High West blends. The importer's convention is that a label calling itself a blend is
`blend` — kept for the cross-type blends (Campfire: straight rye + straight bourbon + blended malt Scotch;
Bourye: straight bourbon + straight rye). A blend whose every component is the same straight whiskey
(Double Rye!, Rendezvous: blends of straight ryes; Bourbon, Cask Strength: blends of straight bourbons) is
legally that straight whiskey, and High West's own Bonded Rye line says "Straight Rye Whiskey", so
`CLASS` below names the straight class for them — otherwise the word "blend" would file the flagship
rye as `blend` and hide it from the Rye filter.  The Prisoner's Share is a conflict between two High West
pages: product-information says "A Blend of Straight Rye Whiskey finished in The Prisoner Red Blend wine
barrels", limited-releases says "a blend of straight bourbon and rye whiskeys". The compliance list is the
label, so it is filed rye; flagged for review.

Ages: the maker states a minimum for the blends ("aged a minimum of two years"), taken as the stated age;
ranges ("6–20 years", "4 to 10 years") are labels only; "10+" is a label. A copy line that restates the
Bottled-in-Bond Act ("Must be aged a minimum of 4 years") is the law's floor, not an age, and is stripped.
Cask Strength's ship page pastes the 2024 back-label ("bourbon and rye, 6–10 years") under the 2025
description; only the description (above "Bottle Details") is read for age and class."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "High West"
DELAY = 6
SITEMAP = "https://ship.highwest.com/sitemap.xml"
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["High West"]
PRODUCER_BY_FAMILY = {}

SHIP = "https://ship.highwest.com/products/"
INFO_URL = "https://highwest.com/pages/product-information"
LIMITED_URL = "https://highwest.com/pages/limited-releases"

# ship.highwest.com handle → (expression, aliases). expression None is the plain "High West" flagship, whose
# bar-order name is "High West Bourbon" (the renamed flagship keeps the old name as an alias).
# Left out on purpose: `high-west-cask-strength-bourbon-24` (the '24 bottling is the same row as the '25),
# the Huckberry and Cask Strength bundles, and the two barrel-finished cocktails.
REFILE = {
    "bourbon": (None, []),
    "rendezvous-rye": ("Rendezvous Rye", []),
    "double-rye": ("Double Rye", ["High West Double Rye!"]),
    "campfire": ("Campfire", []),
    "high-country-american-single-malt": ("High Country American Single Malt", []),
    "bottled-in-bond-rye": ("Bottled in Bond Rye", ["High West Bonded Rye"]),
    "hw-cask-strength-bourbon": ("Cask Strength", []),
    "a-midwinter-nights-dram-act-14": ("A Midwinter Night's Dram", ["High West A Midwinter Nights Dram Act 2.1 Rye"]),
}
NAME_OVERRIDE = {None: "High West Bourbon"}

# The class statement the bottle is filed under (see the docstring on blends).
CLASS = {
    None: "Straight Bourbon Whiskey",
    "Rendezvous Rye": "Straight Rye Whiskey",
    "Double Rye": "Straight Rye Whiskey",
    "Campfire": "Blend of Straight Rye Whiskey, Straight Bourbon Whiskey and Blended Malt Scotch Whisky",
    "High Country American Single Malt": "American Single Malt Whiskey",
    "Bottled in Bond Rye": "Straight Rye Whiskey Bottled in Bond",
    "Cask Strength": "Straight Bourbon Whiskey Cask Strength",
    "A Midwinter Night's Dram": "Straight Rye Whiskey",
    "Bourye": "Blend of Straight Bourbon and Straight Rye Whiskeys",
    "The Prisoner's Share": "Straight Rye Whiskey",
    "Bottled in Bond Bourbon": "Straight Bourbon Whiskey Bottled in Bond",
    "The Noble Share": "Straight Rye Whiskey",
    "Yippee Ki-Yay": "Straight Rye Whiskey",
    "Valley Tan": "Utah Whiskey",
    "Silver Western Oat": "Light Whiskey",
}
CORE = {None, "Rendezvous Rye", "Double Rye", "Campfire", "Bottled in Bond Rye"}
RARITY = [(r"midwinter|bourye|prisoner|noble share|yippee|cask strength|bottled in bond", "allocated"), (r".", "shelf")]
MASH_BILLS = {}

# info-page title → expression, for the bottles that page supplies (class and ABV from its label line).
INFO_BOTTLES = {
    "The Noble Share": "The Noble Share",
    "Yippee Ki-Yay": "Yippee Ki-Yay",
    "Valley Tan": "Valley Tan",
    "Western Oat": "Silver Western Oat",
}
# limited-releases heading → expression.
LIMITED_BOTTLES = {
    "BOURYE": "Bourye",
    "THE PRISONER'S SHARE": "The Prisoner's Share",
    "HIGH WEST BOTTLED IN BOND BOURBON": "Bottled in Bond Bourbon",
}

_FETCHER = None  # set by list_urls so a ship page that states no proof can read the cached info page


def list_urls(fetcher) -> list[str]:
    global _FETCHER
    _FETCHER = fetcher
    return [INFO_URL, LIMITED_URL] + sorted(SHIP + h for h in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _info_entries(page: str) -> dict[str, tuple[str, float | None]]:
    """product-information page → {title: (label text, proof from the ABV)}."""
    t = _flatten(page)
    start = t.find("Product Information|")
    end = t.find("| ABOUT US| VISIT US")
    t = t[start + len("Product Information|"):end if end > start else None]
    out: dict[str, tuple[str, float | None]] = {}
    for chunk in re.split(r"©\s*\d{4}\s*High West Distillery,\s*Park City,\s*UT\.?\s*\|?", t):
        m = re.match(r"\s*\|?\s*(.*?)\s*[-–]?\s*\|?\s*[-–]?\s*Sip Responsibly\.\s*(.*)$", chunk, re.S)
        if not m:
            continue
        title = m.group(1).strip(" |-–")
        label = re.sub(r"\s+", " ", m.group(2)).strip(" |")
        ab = re.search(r"(\d{2}(?:\.\d+)?)\s*%\s*alc", label, re.I)
        out[title] = (label, round(float(ab.group(1)) * 2, 1) if ab else None)
    return out


def _cached_info() -> dict[str, tuple[str, float | None]]:
    if _FETCHER is None:
        return {}
    p = _FETCHER._path(INFO_URL)
    return _info_entries(p.read_text(encoding="utf-8")) if p.exists() else {}


def _og_image(page: str) -> str | None:
    """The product's own photo: the first `"image":{"src":...}` in the page's product JSON (there is no og:image)."""
    m = re.search(r'"image":\{"src":"([^"]+)"', page)
    if not m:
        return None
    img = m.group(1).replace("\\/", "/")
    return ("https:" + img if img.startswith("//") else img).split("?")[0]


def _desc(text: str | None, n: int = 600) -> str | None:
    return text[:n].strip() if text else None


def _record(expression, source_url, proof, age_years, age_label, mash_raw, desc, image, finish=None, aliases=()):
    name = NAME_OVERRIDE.get(expression) or f"High West {expression}"
    return BottlingRecord(
        brand_family="High West", expression=expression, name=name, source_url=source_url, proof=proof,
        age_years=age_years, age_label=age_label, class_raw=CLASS[expression], mash_raw=mash_raw, description=desc,
        image_url=image, finish=finish, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )


def _parse_ship(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases = REFILE[handle]
    own = _flatten(page)
    start = own.find("Add to cart| Added|")
    end = own.find("BUNDLE 3")
    own = own[start + len("Add to cart| Added|"):end if end > start else None] if start >= 0 else own
    head, _, rest = own.partition("Bottle Details:")
    details, _, back = rest.partition("Back Label Story")
    head = re.sub(r"Fun Fact.*$", "", head)  # trivia, not a bottling statement

    # Proof: an explicit "Proof: N", else "N proof" in the bottle's copy, else the ABV.
    pm = re.search(r"Proof:\s*\|?\s*(\d{2,3}(?:\.\d+)?)", details) \
        or re.search(r"\bbottled at\s+(\d{2,3}(?:\.\d+)?)\s*proof", own, re.I) \
        or re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*proof\b(?! isn't)", head, re.I)
    proof = float(pm.group(1)) if pm else None
    if proof is None:
        am = re.search(r"ABV:?\s*(\d{2}(?:\.\d+)?)\s*%?", details) or re.search(r"(\d{2}(?:\.\d+)?)\s*ABV", details) \
            or re.search(r"Alcohol Content\s*\|?\s*(\d{2}(?:\.\d+)?)\s*(?:\||$)", details)
        proof = round(float(am.group(1)) * 2, 1) if am else None
    if proof is None:  # the compliance list has the ABV the store page leaves blank
        for title, (label, p) in _cached_info().items():
            if title.lower().startswith("high country") and expression and "High Country" in expression:
                proof = p
    if proof is not None and not 40 <= proof <= 200:
        proof = None

    # Age: the description first (Cask Strength's back-label is last year's), the back label if it has none.
    stripped = re.sub(r"Must be aged[^.]*\.", "", head)
    years, label = age(stripped)
    if label is None and expression != "Cask Strength":
        years, label = age(re.sub(r"Must be aged[^.]*\.", "", back))

    mm = re.search(r"Mash Bill\s*\|\s*(.*?)\s*\|\s*Technical Information", details + " | Technical Information", re.S)
    mash_raw = mm.group(1).strip(" |") if mm and re.search(r"\d\s*%", mm.group(1)) else None
    if not mash_raw:
        bm = re.search(r"(\d{2}%)\s*rye and (\d{2}%)\s*malted rye mash bill", head)
        mash_raw = f"{bm.group(1)} rye, {bm.group(2)} malted rye" if bm else None
    if mash_raw:
        mash_raw = re.sub(r"\s*\|\s*", " ", mash_raw)

    finish = "Port and Sherry Barrels" if expression == "A Midwinter Night's Dram" else None
    return _record(expression, f"{SHIP}{handle}", proof, years, label, mash_raw, _desc(head.strip(" |")), _og_image(page), finish, aliases)


def _parse_limited(page: str) -> list[BottlingRecord]:
    t = _flatten(page)
    heads = [(h, t.find(f"| {h}|")) for h in LIMITED_BOTTLES]
    stop = t.find("| ABOUT US| VISIT US")
    out = []
    for h, i in heads:
        if i < 0:
            continue
        later = [j for _, j in heads if j > i] + ([stop] if stop > i else [])
        block = t[i + len(h) + 3:min(later) if later else None]
        copy = block.split("SENSORY NOTES")[0]
        expression = LIMITED_BOTTLES[h]
        pm = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*proof\b", copy, re.I)
        proof = float(pm.group(1)) if pm else None
        if proof is None:
            am = re.search(r"(\d{2}(?:\.\d+)?)\s*%\s*ABV", copy)
            proof = round(float(am.group(1)) * 2, 1) if am else None
        years, label = None, None
        mo = re.search(r"Aged\s+(\d{1,2})\s*years?\s*(?:&|and)\s*(\d{1,2})\s*months", copy)
        plus = re.search(r"Aged\s+(\d{1,2})\+\s*years", copy)
        if mo:
            years, label = round(int(mo.group(1)) + int(mo.group(2)) / 12, 1), f"{mo.group(1)} yr {mo.group(2)} mo"
        elif plus:
            label = f"{plus.group(1)}+ yr"  # "Aged 10+ years": a floor, no single number to filter on
        else:
            years, label = age(copy)
        mash_raw = "High-Rye Mash Bill" if re.search(r"high[- ]rye", copy, re.I) else None
        rec = _record(expression, LIMITED_URL, proof, years, label, mash_raw, _desc(_text(copy.replace("|", " "))), None)
        if mash_raw:
            rec.mash_style = "high_rye"
        out.append(rec)
    return out


def _parse_info(url: str, page: str) -> list[BottlingRecord]:
    entries = _info_entries(page)
    out = []
    for title, expression in INFO_BOTTLES.items():
        if title not in entries:
            continue
        label, proof = entries[title]
        out.append(_record(expression, url, proof, None, None, None, label, None))
    return out


def parse(url: str, page: str):
    if url == INFO_URL:
        return _parse_info(url, page)
    if url == LIMITED_URL:
        return _parse_limited(page)
    return _parse_ship(url, page)
