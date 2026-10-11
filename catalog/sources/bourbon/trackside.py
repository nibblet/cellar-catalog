"""siptrackside.com (Trackside Distilling Company, Oldham County KY; site copyright "Just A Distiller Enterprises LLC",
the company Breaking Bourbon's review names). The Breaking Bourbon review's "Official Website" link is the way in:
tracksidedistillery.com is a different business (a craft distillery in Wetaskiwin, Alberta: gin, vodka, seltzer) and
trackside.com redirects to a raceway.

The site is a five-page WordPress/Divi brochure (wp-sitemap: home, our-story, gallery, trackside-locations, contact)
with one bourbon on it. What it states: "A Four-Grain Masterpiece with Chocolate Malt" (mash-bill section, no
percentages), "seven barrel types, three mash bills and various entry proofs", and "Trackside Founder Release Bourbon".
What it does NOT state, anywhere in the text of any page: a proof, an ABV, an age or a year. The bottle is not
shown in a text-readable form either (label photos are not read). So the only fact the maker's pages give that the
catalog lacks is the four-grain recipe, and the page cannot confirm the seed's 93 proof (Breaking Bourbon, from the press
release) or its NAS (the press release says four years, which is not on the maker's own pages).

Outcome: the record has no proof, so the writer inserts nothing and confirms nothing, and the seed row (a 2025 release
label, which the diff never claims) keeps its seed source. This module exists so a re-crawl notices if the site starts
stating a proof; until then the row needs TTB COLA (Phase 2) or a person with the bottle.

The home page opens an 18+/21+ overlay in markup ("Are you over 21 years of age?") but the product copy is in the HTML
the server sends to any client; no gate is passed, clicked or scripted. robots.txt allows everything, sets no Crawl-delay."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Trackside"
DELAY = 6
SITEMAP = "https://siptrackside.com/wp-sitemap.xml"
IMAGE_PREFIX = "https://siptrackside.com/"
CATALOG_FAMILIES = ["Trackside"]
PRODUCER_BY_FAMILY = {}

HOME = "https://siptrackside.com/"
STORY = "https://siptrackside.com/our-story/"
RARITY = [(r".", "allocated")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [HOME, STORY]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def parse(url: str, page: str) -> BottlingRecord | None:
    if url != HOME:
        return None  # the story page only names the release; the home page carries the bottle's copy
    flat = _flat(page)
    if "Founder" not in flat and "Our Bourbon" not in flat:
        return None
    style = "four_grain" if re.search(r"four-grain", flat, re.I) else None
    return BottlingRecord(
        brand_family="Trackside", expression="Founder Release", name="Trackside Founder Release", source_url=url, proof=None,
        class_raw="Kentucky Bourbon Whiskey", mash_raw="four-grain blend with chocolate malt", mash_style=style,
        aliases=["Trackside Bourbon Whiskey, Founder Release 2025", "Trackside Founder Release 2025"], is_core_range=False,
    )
