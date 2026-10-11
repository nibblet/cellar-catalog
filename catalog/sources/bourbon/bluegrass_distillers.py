"""bluegrassdistillers.com (Bluegrass Distillers, Lexington / Midway, Kentucky — WordPress + Elementor +
Yoast; no robots Crawl-delay, no age gate). One page per bottling under /products/<slug>/, listed in
products-sitemap.xml, grouped on the site as Flagship Products / Limited Releases / Midway Distilling
Series / Distillery Exclusives. The page text is short marketing copy (Aroma / Taste / Finish / Summary)
and almost never prints a proof, so very little can be confirmed:

* Proof is read from the product's own heading or copy ("... 100 Proof Bourbon"), from the maker's own
  slug (`100-proof-mash-bill-1-bourbon`, which is also the file name of that page's bottle photo), or —
  as for Barton 1792 and Yellowstone — from the label's own Bottled-in-Bond claim (exactly 100 by law).
  Every other page (Elkwood Reserve "cask strength", the single barrels, the toasted-oak releases, the
  Midway ryes, the Tournament of Roses release) states no number and is listed, not confirmed.
* Age: "7-Year" in the 7 Year High Rye Blue Corn heading, "aged 4.5 years" in the Wheated Bottled-in-Bond
  summary, "15-year-old" and "9 year" in the Elkwood Reserve 15+ and Small Batch copy. Never read:
  the shared Mash Bill Series blurb "Barrel-aged for at least 3 years" (a minimum copied onto five pages,
  including the Bottled-in-Bond one whose legal floor is four), the Bottled-in-Bond "four years" floor,
  "featuring 15, 16, 17, 18, and 19-year aged bourbons" (a series note), a range ("9-11 year" Spanish
  Oaked), and the two generic Elkwood Reserve pages (their copy contradicts itself: "3 releases ... all
  9 year" vs a pasted "15-year-old single barrel").
* Mash bill is the stated "75% yellow/blue corn, 21% rye/wheat, 4% malted barley" of the series blurb.
* The catalog files the brand under two families: "Bluegrass Distillers" (five rows) and "Bluegrass"
  (the lone Tournament of Roses row). The Tournament of Roses record is keyed to "Bluegrass" so it
  matches that seed by name instead of surfacing as a stale row plus a proof-less addition.
* Skipped: Blue Dog Whiskey (a distillery-exclusive blue-corn whiskey "aged less than 30 days", no
  proof); the generic Elkwood Reserve and Elkwood Reserve Kentucky Straight Bourbon Whiskey pages.
"""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Bluegrass"
DELAY = 6
SITEMAP = "https://bluegrassdistillers.com/products-sitemap.xml"
IMAGE_PREFIX = "https://bluegrassdistillers.com/"
CATALOG_FAMILIES = ["Bluegrass Distillers"]  # the lone "Bluegrass" Tournament of Roses row was re-filed here 2026-10-12
PRODUCER_BY_FAMILY = {}

FAMILY = "Bluegrass Distillers"

# slug → (expression, aliases, class, family, name override).  expression is the part after the family.
REFILE = {
    "bluegrass-7-year-high-rye-blue-corn-100-proof-bourbon": ("7 Year High Rye Blue Corn", ["Bluegrass Distillers 7 Year High Rye Blue Corn Bourbon", "Bluegrass 7-Year High Rye Blue Corn 100 Proof Bourbon"], "Bourbon Whiskey", FAMILY, None),
    "100-proof-mash-bill-1-bourbon": ("Mash Bill #1 Small Batch", ["Bluegrass Distillers Mash Bill #1 Small Batch Bourbon"], "Bourbon Whiskey", FAMILY, None),
    "toasted-oak-small-batch-bourbon": ("Toasted Oak Small Batch", ["Bluegrass Distillers Toasted Oak Small Batch Bourbon"], "Bourbon Whiskey", FAMILY, None),
    "single-barrel-toasted-oak-bourbon": ("Single Barrel Toasted Oak", ["Bluegrass Distillers Single Barrel Toasted Oak Bourbon"], "Bourbon Whiskey", FAMILY, None),
    "wheated-bourbon-bottled-in-bond": ("Wheated Bottled-in-Bond", ["Bluegrass Distillers Wheated Bottled-in-Bond Bourbon", "Bluegrass Distillers Wheated Bourbon Bottled-in-Bond"], "Bourbon Whiskey Bottled-in-Bond", FAMILY, None),
    "blue-corn-bottled-in-bond": ("Blue Corn Bottled-in-Bond", ["Bluegrass Distillers Blue Corn Bottled-in-Bond Bourbon"], "Bourbon Whiskey Bottled-in-Bond", FAMILY, None),
    "mash-bill-1-bottled-in-bond-bourbon": ("Mash Bill #1 Bottled-in-Bond", ["Bluegrass Distillers Mash Bill #1 Bottled-in-Bond Bourbon"], "Bourbon Whiskey Bottled-in-Bond", FAMILY, None),
    "single-barrel-wheated-bourbon": ("Single Barrel Wheated", ["Bluegrass Distillers Single Barrel Wheated Bourbon"], "Bourbon Whiskey", FAMILY, None),
    "elkwood-reserve-15-year": ("Elkwood Reserve 15 Year Single Barrel", ["Bluegrass Distillers Elkwood Reserve 15+ Year"], "Kentucky Straight Bourbon Whiskey", FAMILY, None),
    "elkwood-reserve-small-batch": ("Elkwood Reserve Small Batch", [], "Kentucky Straight Bourbon Whiskey", FAMILY, None),
    "elkwood-reserve-spanish-oaked": ("Elkwood Reserve Spanish Oaked", [], "Kentucky Straight Bourbon Whiskey", FAMILY, None),
    "elkwood-reserve-french-oaked": ("Elkwood Reserve French Oaked", [], "Kentucky Straight Bourbon Whiskey", FAMILY, None),
    "elkwood-reserve-toasted-oaked": ("Elkwood Reserve Toasted Oaked", [], "Kentucky Straight Bourbon Whiskey", FAMILY, None),
    "tournament-of-roses-small-batch-toasted-oak-bourbon": ("Tournament of Roses Toasted Oak", ["Bluegrass Distillers Tournament of Roses Small Batch Toasted Oak Bourbon"], "Bourbon Whiskey", "Bluegrass Distillers", "Bluegrass Distillers Tournament of Roses Toasted Oak"),
    "colonel-francisco-rye-whiskey": ("Midway Colonel Francisco Rye", [], "Rye Whiskey", FAMILY, None),
    "dudley-gratz": ("Midway Dudley & Gratz Rye", [], "Rye Whiskey", FAMILY, None),
    "lees-branch": ("Midway Lee's Branch Rye", [], "Rye Whiskey", FAMILY, None),
    "midway-lot-25": ("Midway Lot 25 Rye", [], "Rye Whiskey", FAMILY, None),
    "reclaimed-recharred": ("Midway Reclaimed & Recharred Rye", [], "Rye Whiskey", FAMILY, None),
}
# The site's own "Flagship Products" category.
CORE = {"7 Year High Rye Blue Corn", "Mash Bill #1 Small Batch", "Toasted Oak Small Batch", "Single Barrel Toasted Oak",
        "Wheated Bottled-in-Bond", "Blue Corn Bottled-in-Bond"}
RARITY = [(r"elkwood|tournament|midway|bottled-in-bond|blue corn", "limited"), (r".", "shelf")]
MASH_BILLS = {}
# Pages whose copy is the only place an age may be read; everything else states none (see the docstring).
AGE_PAGES = {"bluegrass-7-year-high-rye-blue-corn-100-proof-bourbon", "wheated-bourbon-bottled-in-bond",
             "elkwood-reserve-15-year", "elkwood-reserve-small-batch"}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://bluegrassdistillers.com/products/{slug}/" for slug in REFILE)


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _own(page: str) -> str:
    """The product's own block: after the page header's nav, before 'Explore More ...' / the CTA tail."""
    t = _flatten(page)
    marker = "Book a Tour| Shop Online|"
    i = t.rfind(marker)
    t = t[i + len(marker):] if i >= 0 else t
    cut = [m.start() for m in (re.search(r"Explore More", t), re.search(r"Bring Home a Taste", t)) if m]
    return t[:min(cut)] if cut else t


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw, family, name_override = REFILE[slug]
    name = name_override or f"{family} {expression}"
    own = _own(page)
    bib = "Bottled-in-Bond" in expression

    pm = re.search(r"\b(\d{2,3}(?:\.\d)?)\s*proof\b", own, re.I)
    sm = re.search(r"(\d{2,3})-proof", slug)
    if pm:
        proof = float(pm.group(1))
    elif sm:
        proof = float(sm.group(1))
    elif bib:
        proof = 100.0  # the label's own Bottled-in-Bond claim; the page states no other figure
    else:
        proof = None

    years = label = None
    if slug in AGE_PAGES:
        text = re.sub(r"barrel-aged for at least \d+ years", " ", own, flags=re.I)
        text = re.sub(r"featuring[^|.]*?bourbons", " ", text, flags=re.I)
        years, label = age(text)

    mm = re.search(r"(\d{2})%\s+((?:yellow |blue )?corn),?\s+(\d{2})%\s+(rye|wheat),?\s+(?:and\s+)?(\d{1,2})%\s+malted barley", own, re.I)
    mash_raw = f"{mm.group(1)}% {mm.group(2).title()}, {mm.group(3)}% {mm.group(4).title()}, {mm.group(5)}% Malted Barley" if mm else None

    summary = own.split("Summary|", 1)[1] if "Summary|" in own else own
    desc = re.sub(r"\s*\|\s*", " ", summary).strip()[:600] or None
    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]

    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
