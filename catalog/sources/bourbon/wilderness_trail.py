"""wildernesstraildistillery.com (Wilderness Trail Distillery, Danville KY — Campari). WordPress, one page per
whiskey under /whiskeys/. Re-checked 2026-10-11 after being parked ("no proof/age/mash anywhere"): the
three product pages still state nothing numeric (flavor profile, awards, and a MASHBILL block that is just
an image, `percent_0N.png` — never OCR'd), but the brand's own copy elsewhere does:

  /faq/          "Our core whiskeys adhere to rigorous criteria to be considered 'bottled in bond' ...
                 aged ... for a minimum of four years, and bottled at exactly 100 proof or 50% ABV", and
                 "What whiskeys does Wilderness Trail make? ... Wheated Bourbon, High Rye Bourbon, and
                 Rye Whiskey" — the three, so the statement covers exactly them;
  /our-process/  "Wilderness Trail's small-batch bottled-in-bond whiskeys are all ... bottled at exactly
                 100 proof";
  /whiskeys/     "Wilderness Trail's core offerings ... bottled-in-bond ... bottled on-site at precisely 100 proof".

That is a brand-level statement for all three (the same shape as Daviess County's "like all variants ...
is 96 proof"), and Bottled-in-Bond is a federal definition of exactly 100 proof besides. So each product
page's record takes its proof from the FAQ's statement, read at parse time: `parse()` of /faq/ (listed
first by `list_urls`) sets `_BIB_PROOF` when the sentence is present, and a product page parsed after it
uses it — with the FAQ missing or reworded the records carry no proof and are neither confirmed nor
added. Age is NOT read: "a minimum of four years" is the Bottled-in-Bond Act's floor, not a bottling's
age (the same trap as Starlight's boilerplate). Mash stays unread (image). The 100-105 "entry proof" the
Rye page mentions is the barrel-entry proof, never the bottling's.

`class_raw` carries "Bottled in Bond" because the brand states the whole core lineup is — `flags()` then
sets `bottled_in_bond` — and the wheated page says so itself ("the first bottled-in-bond wheated sweet
mash bourbon released since Prohibition"). The bottle photo is the hero `Group-22N.webp` carried in the
page's lazy-load `data-imgsrc`; the product pages have no og:image."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Wilderness Trail"
DELAY = 6
SITEMAP = "https://www.wildernesstraildistillery.com/sitemap.xml"
IMAGE_PREFIX = "https://www.wildernesstraildistillery.com/"
CATALOG_FAMILIES = ["Wilderness Trail"]
PRODUCER_BY_FAMILY = {}

BASE = "https://www.wildernesstraildistillery.com"
EVIDENCE = ["faq"]
# slug → (expression, aliases, class statement, image file stem)
REFILE = {
    "wheated-bourbon": ("Wheated Bourbon", ["Wilderness Trail Kentucky Straight Wheated Bourbon", "Wilderness Trail Wheated Bourbon Bottled in Bond"], "Kentucky Straight Wheated Bourbon Whiskey Bottled in Bond", "Group-225"),
    "high-rye-bourbon": ("High Rye Bourbon", ["Wilderness Trail Kentucky Straight High Rye Bourbon", "Wilderness Trail High Rye Bourbon Bottled in Bond"], "Kentucky Straight Bourbon Whiskey Bottled in Bond", "Group-224"),
    "rye-whiskey": ("Rye Whiskey", ["Wilderness Trail Kentucky Straight Rye Whiskey", "Wilderness Trail Rye Whiskey Bottled in Bond"], "Kentucky Straight Rye Whiskey Bottled in Bond", "Group-226"),
}
CORE = {"Wheated Bourbon", "High Rye Bourbon", "Rye Whiskey"}
RARITY = [(r".", "shelf")]
MASH_BILLS = {}

_BIB_PROOF: float | None = None


def list_urls(fetcher) -> list[str]:
    return [f"{BASE}/{s}/" for s in EVIDENCE] + [f"{BASE}/whiskeys/{s}/" for s in REFILE]


def _flat(fragment: str) -> str:
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    global _BIB_PROOF
    slug = url.rstrip("/").split("/")[-1]
    if slug in EVIDENCE:
        own = _flat(page)
        m = re.search(r"core whiskeys.{0,300}?bottled at exactly (\d{2,3}) proof", own, re.I)
        _BIB_PROOF = float(m.group(1)) if m else None
        return None
    if slug not in REFILE:
        return None
    expression, aliases, cls, imgstem = REFILE[slug]
    own = _flat(page)
    desc = re.search(r"Learn about our [^|]+\|\s*(.*?)\|\s*MASHBILL", own)
    desc = re.sub(r"\s*\|\s*", " ", desc.group(1)).strip() if desc else None
    img = re.search(r'data-imgsrc="(https://[^"]*?/' + re.escape(imgstem) + r'\.webp)"', page)
    return BottlingRecord(
        brand_family="Wilderness Trail", expression=expression, name=f"Wilderness Trail {expression}",
        source_url=url, proof=_BIB_PROOF, age_years=None, age_label=None, class_raw=cls, mash_raw=None,
        description=desc, image_url=img.group(1) if img else None, aliases=sorted(set(aliases)),
        is_core_range=expression in CORE,
    )
