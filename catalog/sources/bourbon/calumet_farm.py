"""calumetbourbon.com (Calumet Farm Kentucky Straight Bourbon, a Squarespace site; robots.txt is Squarespace's
default — `*` may crawl everything but /config, /search, /api and the `?format=` / `?tag=` query forms, none of which are
used — and sets no Crawl-delay, so DELAY is the project's usual 6). NOT calumetfarm.com: that is the Lexington
thoroughbred farm's own site ("standing one stallion") and carries no bourbon; calumetfarmbourbon.com is a parked
redirect to /lander. The FAQ names the maker: "Western Spirits Beverage Company produces Calumet Farm Bourbon and it is
bottled by Three Springs Bottling Company, both in Bowling Green" — a non-distiller producer (NDP) bottling a purchased
Kentucky reserve with one mash bill (74% corn, 18% rye, 8% malted barley) under licence from the horse farm. The
catalog's producer stays "Calumet Farm" (the owner's call; flagged in the hand-off).

The lineup is the site nav: "Legacy" (16, 15, 12, 10 Year, Small Batch, 8 Year) and "Centennial" releases; discontinued
bottlings sit on "Out to Pasture" with their own pages. Every Legacy product page has a spec table — "Potency | 106 Proof
(53% Alc/Vol)", "Mash Bill | 74% Corn, 18% Rye, 8% Malted Barley", "Batch Size", "Bottled By" — and no age field: the age is
the maker's own name for the bottle, read from the page <title> ("16 Year Old - Single Rack Black"). The Small Batch is a
blend of 17- and 7-year bourbons; the page states those components and no age for the bottle, so none is taken (the seed's
NAS stands). Tile and hero images are the product photos named by their alt text.

What is a row (decided here, so a re-run reproduces it):
  - One row per bottling, never per release. The Small Batch has been re-blended (15+8 earlier, 17+7 now, both 86 proof) and
    Breaking Bourbon titled one review "Legacy Release 2022"; that is the same SKU, so it stays the one 'Small Batch' row and
    the review title stays an alias. No release_label is set on anything.
  - Two different 12 Year bourbons are on the site and must not be one row: the current 12 Year (102 proof, barreled 2014,
    numbered batches 12A-12G, nav page /12-year-old) and the discontinued 12 Year Single Rack Black (94 proof, page
    /12yo-singlerackblack, "Out to pasture - Discontinued"). The seed 'Single Rack Black' (94 proof, 12 yr) is the old one and is
    refiled as '12 Year Single Rack Black'.
  - The seed flagship row 'Calumet Farm' (no expression, 96.2 proof, 14 yr) is the discontinued 14 Year Single Rack Black: its
    curated proof and age equal that page's ("Potency | 96.2 Proof", "14 Year Old") and no other Calumet bottle states 96.2.
    It is refiled as '14 Year'; the old name stays an alias.
  - Out-to-pasture bottlings that have no catalog row (the 10 Year Single Rack Black at 92 proof, the 10 Year Single Barrel, the
    earlier Small Batch) are not added: nothing in the catalog asks for them and 10 Year is the verified Bull Lea row.
  - The Centennial Release line (2025): 17 Year, 18 Year, Rye (91% rye / 9% malted barley), Origin Bottle and the ceramic
    decanters. Their proofs appear only in "Stat Stack" images and the footer's range ("43%-59% Alc./Vol."), so no page states
    a proof; the parsed records carry age and mash and are reported "no proof stated — will not be added". The one exception is
    the Centennial Bottled-in-Bond: Bottled in Bond is 100 proof by law (the rule the project allows), so it is read as 100 and
    its page's "aged for a minimum of 4 years" (the Act's floor) is NOT read as an age.
  - What the maker itself calls discontinued ("Out to pasture - Discontinued": the 14 Year and the old 12 Year Single Rack
    Black) is DISCONTINUED_BY_MAKER. The shared writer reads that set (write.py `_gone`) and writes `discontinued = true` for
    those expressions instead of the usual `false`, so a re-run reproduces it. Rows the pages do not list stay as seeds.
Availability on each page ("High", "Low/Rare") drives RARITY.
tasting_notes is the spec table's own Nose / Taste / Finish rows (Color is a look, not a taste); the Centennial Rye, which has no
table, gives its two flavor sentences."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Calumet Farm"
DELAY = 6
BASE = "https://www.calumetbourbon.com/"
SITEMAP = BASE + "sitemap.xml"  # not crawled (list_urls is fixed); scripts/bourbon_write.py reads its host
IMAGE_PREFIX = "https://images.squarespace-cdn.com/"
CATALOG_FAMILIES = ["Calumet Farm"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Calumet Farm"

KSB = "Kentucky Straight Bourbon Whiskey"
# slug → (expression, [catalog names it answers to], class statement)
PAGES = {
    # Legacy series — the nav's current lineup
    "16-year-old-citation": ("16 Year", ["Calumet Farm 16 Year Old Straight Bourbon", "Calumet Farm 16 Year Old", "Calumet Farm 16 Year Old Single Rack Black"], KSB),
    "15-year-old-whirlaway": ("15 Year", ["Calumet Farm 15 Year Old", "Calumet Farm 15 Year Old Single Rack Black"], KSB),
    "12-year-old": ("12 Year", ["Calumet Farm 12 Year Old", "Calumet Farm 12 Year Old Bourbon"], KSB),
    "10-year-old-bull-lea": ("10 Year", ["Calumet Farm 10 Year Old", "Calumet Farm 10 Year Old Bull Lea Edition"], KSB),
    "smallbatch": ("Small Batch", ["Calumet Farm Small Batch Bourbon (Legacy Release 2022)", "Calumet Farm Small Batch Bourbon"], KSB),
    "8yo": ("8 Year", ["Calumet Farm 8 Year Old"], KSB),
    # Out to Pasture — discontinued, but matching a seed row the catalog already holds
    "14yo-singlerackblack-bti-gold": ("14 Year", ["Calumet Farm", "Calumet Farm 14 Year Old", "Calumet Farm 14 Year Old Single Rack Black"], KSB),
    "12yo-singlerackblack": ("12 Year Single Rack Black", ["Calumet Farm Single Rack Black", "Calumet Farm 12 Year Old Single Rack Black"], KSB),
    # Centennial release (2025)
    "centennial-bottled-in-bond": ("Centennial Bottled in Bond", ["Calumet Farm Bottled in Bond Centennial Release"], "Bottled in Bond Kentucky Straight Bourbon Whiskey"),
    "centennial-18yearold-trophydecanter": ("Centennial 18 Year", [], KSB),
    "centennial-17yearold-glassdecanter": ("Centennial 17 Year", [], KSB),
    "centennial-rye-whiskey": ("Centennial Rye", [], "Rye Whiskey"),
    "centennial-origin-bottle-release": ("Centennial Origin Bottle", [], KSB),
}
# Pages cached as evidence only (no records): the active lineup, Out to Pasture, FAQ (who makes it), Pedigree, Legacy nav.
EVIDENCE = ["bourbons-active", "out-to-pasture-discontinued", "faq", "the-pedigree", "legacy"]

DISCONTINUED_BY_MAKER = {"14 Year", "12 Year Single Rack Black"}
CORE = {"16 Year", "15 Year", "12 Year", "10 Year", "Small Batch", "8 Year"}
RARITY = [(r"single rack black|14 year|centennial", "limited"), (r"15 year|16 year", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + s for s in [*PAGES, *EVIDENCE]]


def _text(page: str) -> str:
    i, j = page.find("<main"), page.find("</main>")
    t = page[i:j] if 0 < i < j else page
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\s*\|\s*)+", " | ", t)


def _title(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else ""


def _mash(text: str) -> str | None:
    i = text.find("Mash Bill")
    if i < 0:
        i = text.find("mash bill")
    if i < 0:
        return None
    parts = re.findall(r"(\d{1,2}(?:\.\d)?)%\s*(Corn|Rye|Wheat|Malted Barley)", text[i:i + 140])
    return ", ".join(f"{p}% {g}" for p, g in parts) or None


# alt text that names *this* bottle's photo, never a spec graphic, pedigree art, a reviews strip or the carousel of
# sibling bottles each page ends with (the 12 Year page ends with the Centennial 17 Year tile)
_IMG_BAD = re.compile(r"Pedigree|Predigree|Details|Tasting|Mash|Review|Stat Stack|Glamor|Header|Batch Yield|Series Black|Illustration|Alcohol|Proof|Medal|Reserve|Dedication|Link|Centennial Release", re.I)


def _image(page: str, years: float | None, expression: str) -> str | None:
    if years:
        n = int(years)
        ident = re.compile(rf"(?:\b{n} Year Old|srb{n}\b)", re.I)
    elif expression == "Small Batch":
        ident = re.compile(r"Small ?Batch", re.I)
    else:
        return None
    i = page.find("<main")
    for m in re.finditer(r"<img[^>]*>", page[i:] if i > 0 else page):
        tag = m.group(0)
        alt = re.search(r'alt="([^"]*)"', tag)
        src = re.search(r'data-image="([^"]*)"', tag) or re.search(r'data-src="([^"]*)"', tag)
        if alt and src and ident.search(alt.group(1)) and not _IMG_BAD.search(alt.group(1)) and ("Centennial" in expression) == ("Centennial" in alt.group(1)):
            return html.unescape(src.group(1))
    return None


def _tasting(text: str) -> str | None:
    """`text` is _text(): the page's <main> with `|` between cells. The spec table repeats Nose (uncorking / breathing)."""
    parts = []
    for key, body in re.findall(r"\| (Nose|Taste|Finish) \| ([^|]+)", text):
        body = body.strip().rstrip(" ,;")
        if body:
            parts.append(f"{key}: {body}" + ("" if body.endswith((".", "!")) else "."))
    if parts:
        return " ".join(parts)[:900]
    flavor = [x for x in re.split(r"(?<=[.!])\s+", re.sub(r"\s*\|\s*", " ", text)) if re.search(r"undertones|notes of|flavors? of|flavor profile", x, re.I)]
    return " ".join(flavor)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").replace(BASE.rstrip("/"), "").strip("/")
    if slug not in PAGES:
        return None
    expression, aliases, class_raw = PAGES[slug]
    name = f"{FAMILY} {expression}"
    text = _text(page)

    proof = None
    m = re.search(r"Potency \| (\d{2,3}(?:\.\d+)?) Proof", text)
    if m:
        proof = float(m.group(1))
    elif "Bottled in Bond" in class_raw:
        proof = 100.0  # Bottled in Bond is 100 proof by law; the page prints the number only in an image

    years = label = None
    if "Bottled in Bond" not in class_raw:  # the Act's "minimum of 4 years" is a floor, not this bottle's age
        years, label = age(_title(page).split("—")[0])

    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=_mash(text), tasting_notes=_tasting(text), image_url=_image(page, years, expression),
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
