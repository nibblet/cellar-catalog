"""backbonebourbon.com (Backbone Bourbon Company, Indiana — a non-distilling producer that blends, finishes and
bottles sourced whiskey). WordPress with one page per product (wp-sitemap-posts-page-1.xml lists them; the site's own
nav, repeated on every page, is the lineup). robots.txt is WordPress's default with no Crawl-delay, so DELAY is the
project's usual 6. An age-gate plugin overlays the pages; the product copy is in the static HTML and nothing here
clicks through it.

Facts live in a labelled block under the blurb: "Mash Bill Or Blend:", "Distillation:", "Proof:", "Current Batch:",
"Cases Produced:". Proof is read from the "Proof:" label only (the blurbs also quote a sibling's number). The labels
state the CURRENT batch's proof; a page that carried a range or "barrel proof" with no number would state none.
Age is read from the product's own title only ("Old Bones Bourbon 10 Year Reserve", "Almost Old Bones 9 Year
Reserve", "Bone Snapper X-Ray 4 Year Reserve"): Backbone's other pages state no age. "Batches of Backbone Uncut are
typically between 5 and 6 years old" is a range for a vintage-to-vintage batch, "Bone Snapper ... around the 30 month
mark" is a bottling target, and The Forge / Decade Down quote the ages of their component barrels ("5 & 7 years old",
"between 5 and 7 years"): none is an age statement, so those rows have none. (Decade Down is "ten years since
the first batch of Uncut", not ten years old.)

Batches are not bottlings. Every page gives a "Current Batch" (Uncut #29, Prime #14, The Forge #3, Old Bones Bourbon
10 Year 9K, ...) and nothing here records it; the seeded 'Backbone Prime Blended' (Batch 4) is a batch of the Prime
flagship and is folded into it by hand (cellar.merge_product keeps the 'Batch 4' release label).

Blends state no single recipe: The Forge, Prime and Big Bash list their component mash bills or percentages by whiskey
type, so mash_raw is null for them (the Forge's straight-bourbon component is the same 75/21/4 as Uncut; the blend
as a whole is not). Decade Down's block prints "74% Corn, 21% & 5% Malted Barley" with the word Rye dropped; the
Whisky Advocate review quoted lower on the same page spells it "74% corn, 21% rye, and 5% malted barley", and the
module takes the recipe from that sentence.

Class: Backbone's own words are "blended bourbon" for The Forge and Prime ("at least 51% of the blend is Straight
Bourbon"), which normalize.spirit_type() reads as bourbon (the label class, not a cross-type blend); Big Bash states
no class and blends rye and bourbon mash bills, so it is "Blended Whiskey" → blend. Almost Old Bones prints neither
'bourbon' nor 'rye' (it is a 75% corn / Bardstown, Kentucky whiskey sold as "Almost" the Old Bones Bourbon label); it
is read as bourbon from that recipe and its siblings — an inference, listed for the owner. Old Bones Rye 10 and Bone
Snapper carry their rye in the name.

Not imported, and why:
- Bone Dry Gin and Auld Blow-In Scotch: not American whiskey.
- Old Bones Rye 15 Year Reserve: "Distilled just outside of Montreal ... Canada" — a Canadian rye, outside this
  catalog's scope. Listed in OUT_OF_SCOPE so a re-run reproduces the decision.
- /single-barrel-program/ and /old-bones-bourbon/ (a two-link landing page): a program and a folder, not bottlings.
- The seeded 'Uncut, Single Barrel' (118.4, 7 yr) is a single-barrel pick; the maker's Uncut is a 10-barrel batch at
  116.6 and the two do not match, so the seed stays as it is.

Decade Down: the page is titled "Decade Down Uncut" but the row is named 'Decade Down' (the maker's title is an alias)
because normalize.flags() reads the word "uncut" in a name as barrel proof, and Decade Down is bottled at a round 110
(55%), a proof the page never calls barrel strength. Uncut's own 116.6 is barrel strength by the 115-proof floor.

Naming: Backbone-labelled bottlings carry the family ('Backbone Bourbon Uncut'); the sub-brands Old Bones, Almost Old
Bones and Bone Snapper are named as the label reads. The seeds' names are aliases: 'Backbone Bourbon The Forge
Blended', 'Backbone Decade Down Anniversary Edition', 'Old Bones Reserve' (the seed is 110 proof / 10 years / bourbon:
Old Bones Bourbon 10 Year Reserve is the one Old Bones bottling that agrees on all three; Old Bones Rye 10 is rye)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Backbone Bourbon"
DELAY = 6
SITEMAP = "https://backbonebourbon.com/wp-sitemap-posts-page-1.xml"
IMAGE_PREFIX = "https://backbonebourbon.com/"
CATALOG_FAMILIES = ["Backbone Bourbon"]
PRODUCER_BY_FAMILY = {}

BASE = "https://backbonebourbon.com/"
BOURBON = "Bourbon Whiskey"
BLENDED_BOURBON = "Blended Bourbon Whiskey"
RYE = "Rye Whiskey"
# slug → (expression, name, [catalog names it answers to], class statement, single recipe?)
PAGES = {
    "backbone-bourbon-uncut": ("Uncut", "Backbone Bourbon Uncut", [], "Straight Bourbon Whiskey", True),
    "backbone-bourbon-prime": ("Prime", "Backbone Bourbon Prime", [], BLENDED_BOURBON, False),
    "backbone-bourbon-the-forge": ("The Forge", "Backbone Bourbon The Forge", ["Backbone Bourbon The Forge Blended"], BLENDED_BOURBON, False),
    "decade-down-uncut": ("Decade Down", "Backbone Bourbon Decade Down", ["Backbone Decade Down Anniversary Edition", "Backbone Bourbon Decade Down Uncut"], "Straight Bourbon Whiskey", True),
    "big-bash": ("Big Bash", "Backbone Bourbon Big Bash", [], "Blended Whiskey", False),
    "old-bones-bourbon-10-year-reserve": ("Old Bones Bourbon 10 Year Reserve", "Old Bones Bourbon 10 Year Reserve", ["Old Bones Reserve"], BOURBON, True),
    "old-bones-bourbon-15-year-reserve": ("Old Bones Bourbon 15 Year Reserve", "Old Bones Bourbon 15 Year Reserve", [], BOURBON, True),
    "almost-old-bones": ("Almost Old Bones 9 Year Reserve", "Almost Old Bones 9 Year Reserve", [], BOURBON, True),
    "old-bones-rye-10-year-reserve": ("Old Bones Rye 10 Year Reserve", "Old Bones Rye 10 Year Reserve", [], RYE, True),
    "bone-snapper-straight-rye-whiskey": ("Bone Snapper Straight Rye", "Bone Snapper Straight Rye Whiskey", [], "Straight Rye Whiskey", True),
    "bone-snapper-xray-4-year-reserve": ("Bone Snapper X-Ray 4 Year Reserve", "Bone Snapper X-Ray 4 Year Reserve", [], "Reserve Straight Rye Whiskey", True),
}
OUT_OF_SCOPE = {"old-bones-rye-15-year-reserve": "Canadian rye (distilled near Montreal)"}
# Backbone's permanent lineup: the flagship, Prime, The Forge and Bone Snapper. Old Bones, Almost Old Bones, Big Bash,
# Decade Down and the X-Ray reserve are limited or periodic ("only bottled when we find ...", "a new Decade Down every year").
CORE = {"Uncut", "Prime", "The Forge", "Bone Snapper Straight Rye"}
RARITY = [(r"old bones|almost old bones", "allocated"), (r"decade down|big bash|forge|x-ray", "limited"), (r".", "shelf")]
MASH_BILLS = {}
CLASS_BY_SLUG = {s: v[3] for s, v in PAGES.items()}

BARREL_STRENGTH = {"old-bones-bourbon-15-year-reserve"}  # "Proof: 107 (barrel strength)"


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _flat(region: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", region, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = t.replace("’", "'").replace("\xa0", " ")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def _recipe(chunk: str) -> str | None:
    """'Corn 75%, Rye 21% & Malted Barley 4%' / '95% Rye & 5% Malted Barley' → '75% Corn, 21% Rye, 4% Malted Barley'."""
    parts = []
    for seg in re.split(r"\s*(?:,|;|&|\band\b)\s*", chunk):
        m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%\s*([A-Za-z][A-Za-z ]*)", seg) or None
        if m:
            parts.append(f"{m.group(1)}% {m.group(2).strip().title()}")
            continue
        m = re.search(r"([A-Za-z][A-Za-z ]*?)\s*(\d{1,2}(?:\.\d+)?)\s*%", seg)
        if m:
            parts.append(f"{m.group(2)}% {m.group(1).strip().title()}")
    return ", ".join(parts) or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, name, aliases, class_raw, single = PAGES[slug]
    i, j = page.find('<div id="productWrap">'), page.find("<!--END WRAP-->")
    own = _flat(page[i:j] if 0 <= i < j else page)

    pm = re.search(r"\bProof\b[\s|:=]*(\d{2,3}(?:\.\d+)?)", own)  # the labelled field only, case-sensitive
    proof = float(pm.group(1)) if pm else None
    if slug in BARREL_STRENGTH:
        class_raw += " Barrel Strength"

    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", " ", h1.group(1))) if h1 else ""
    years, label = age(title)
    if years is None:
        am = re.search(r"\b(\d{1,2}) Year Reserve\b", own[:200])  # Almost Old Bones: the h1 is just the name
        if am:
            years, label = age(f"{am.group(1)} year old")

    mash_raw = None
    if single:
        if slug == "decade-down-uncut":  # the block drops the word Rye; the review quoted on the page spells it out
            rm = re.search(r"mashbill of ((?:\d{1,2}% [a-z]+(?: barley)?(?:, and |, | and )?)+)", own)
            mash_raw = _recipe(rm.group(1)) if rm else None
        else:
            mm = re.search(r"Mash[- ]?[Bb]ills?(?: [Oo]r [Bb]lend)?:?\s*\|?\s*:?\s*([^|]*(?:\d%|\d{1,2}\.\d%)[^|]*)", own)
            mash_raw = _recipe(mm.group(1)) if mm else None

    ig = re.search(r'<div id="subR">\s*<img src="([^"]+)"', page)
    img = html.unescape(ig.group(1)) if ig else None

    return BottlingRecord(
        brand_family="Backbone Bourbon", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
