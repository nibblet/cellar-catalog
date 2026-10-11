"""burksspringbourbon.com (Burks Spring Bourbon, a Squarespace site run by the brand's owner, Dick Burks; robots.txt is
Squarespace's template — it disallows named AI crawlers (not this fetcher's own CellarCatalog UA, which falls under `*`),
/config, /search, /account, /api and the `?format=` / `?tag=` query forms, none of which are used — and sets no
Crawl-delay, so DELAY is the project's usual 6). burksspring.com is a parked GoDaddy lander (HTTP 200 whose body is a
script redirect to /lander); burksspringbourbon.com is the maker's.

The brand is a non-distiller bourbon: the site's own news posts name Kentucky Artisan Distillery (Crestwood, KY) as the
production partner. The seed's specs say "Maker's Mark" (the Burks family's old site is now under Maker's Mark) — that is
wrong as a producer and is left for the owner; the producer text this importer writes is "Burks Spring".

What the site has: a home page, History, Locations, Contact and a News blog. There is NO product page and no shop. The only
place the maker states the bottle's strength is its own press release, "Over 100 years of bourbon history being brought
back to life with 'Burks Spring Bourbon' by descendent of original distiller" (/news/blog-press-release, dated March 14,
2024, the launch announcement): "Burks Spring Bourbon is a high rye bourbon bottled at 100 proof and will be sold in 750ml
bottles." That is the maker's own text for this bottling (it launched as the brand's single expression), so it is read.
Judgment call, flagged for the owner: a press release is not a product page; if the owner prefers product pages only, drop
this module and the row stays a seed.

What is NOT read (decided here, so a re-run reproduces it):
  - The news page also reposts third-party articles ("via The Whiskey Wash", "via Business First", BourbonVEACH,
    Oldham Era). They call it "Bottled-in-Bond", "aged a little less than six years" and "60/25/15"; those are the
    publishers' words on the maker's site, not the maker's statement, so no BiB flag, no age and no mash bill is taken.
    The seed's NAS stands. The maker's own sentence says only "high rye", so mash_style is high_rye with no percentages.
  - The Select 7 Year Reserve (news post of Dec 18, 2025): the post names the bottling and "7 Year" but states no proof
    for it; the 100-proof sentence is the brand boilerplate. Not a record (it would also be a proof-less addition).
  - og:image is the Burks Spring logo on every page, not a bottle: no image is taken.
Family is "Burks Spring"; the bottling is the family flagship (expression None), named "Burks Spring" to match the seed."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import proof as parse_proof

PRODUCER = "Kentucky Artisan Distillery"  # owner decision 2026-10-13: Burks Spring is distilled there
DELAY = 6
BASE = "https://www.burksspringbourbon.com/"
IMAGE_PREFIX = "https://images.squarespace-cdn.com/"
CATALOG_FAMILIES = ["Burks Spring"]
PRODUCER_BY_FAMILY = {}

LAUNCH = BASE + "news/blog-press-release"
# Evidence only (cached so the "no product page / no proof elsewhere" findings can be re-read): no records come from them.
EVIDENCE = [BASE + p for p in ("home", "history", "locations", "news/blog-press-release-km52y-6eymb-y3mrm-xryh8-jwpyj")]
CORE = {None}
RARITY = [(r".", "allocated")]  # the seed's rarity; a fill only, never overwrites
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [LAUNCH, *EVIDENCE]


def _text(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", body)).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    if url != LAUNCH:
        return None
    t = _text(page)
    start = t.find("Written By")
    end = t.find(" Previous ", start)
    post = t[start:end] if 0 <= start < end else t
    m = re.search(r"Burks Spring Bourbon is an? (?:[\w ]+? )?bourbon bottled at (\d{2,3}(?:\.\d)?) proof", post, re.I)
    proof = parse_proof(m.group(1) + " proof") if m else None
    return BottlingRecord(
        brand_family="Burks Spring", expression=None, name="Burks Spring", source_url=url, proof=proof,
        age_years=None, age_label=None, class_raw="Bourbon Whiskey", mash_raw=None, mash_style="high_rye",
        image_url=None, aliases=["Burks Spring Bourbon"], is_core_range=True,
    )
