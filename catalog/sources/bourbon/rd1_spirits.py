"""rd1spirits.com (RD1 Spirits, Lexington KY — the catalog files it as family 'RD One'; rdonespirits.com only
redirects to a lander). Shopify storefront whose bottle pages are Shopify *pages* (`/pages/<slug>`), not
products — the products collection is merch plus a sold-out 12-year decanter — so the bottle list is the
site's own Bourbon nav, hardcoded below, and pages are fetched as rendered HTML.

Each bottle page opens (after the breadcrumb) with one hero line: "98 proof, 49% ALC/VOL, 750 ML | Aged 4+
Years" (or "51% ALC/VOL, 102 PROOF 750 ML"); the first N-proof mention after the breadcrumb is the bottling's,
everything after it is award and review copy ("Nailed the proof on this", "(117- proof)"). "Aged 4+ Years"
is the maker's floor statement, read as 4 the way `normalize.age()` reads "at least 4 years" — it matches the
seeded 4.0. The traditional mash bill (70% corn, 21% rye, 9% malted barley) is printed only on the flagship
page; the finished expressions say only that they finish that same bourbon, so they state no mash bill.

Mizunara + French Oak is a blend of 5-year finished bourbon, 7-year bourbon and 8-year rye under the label
class "Kentucky Straight Whiskey": a cross-type blend, filed `blend` (High West convention) with no single age.

Not parsed: the 12-Year single-barrel decanter (the page states "Ranging from 121.1 to 127.3 proof", a range
is no statement — and the sold-out store product states nothing), the Limited Releases landing page (Hot
Honey, Pickle Barrel, Mongolian Oak … have no pages of their own and state no proof), the 200 ml flight and
Private Select program (a flight and a program), and the Wm. Tarr pages (a separate brand). `og:image` is one
box shot on every page, so the image is the first bottle/pour photo in the page body."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "RD1 Spirits"
DELAY = 6
SITEMAP = "https://rd1spirits.com/sitemap.xml"
IMAGE_PREFIX = "https://rd1spirits.com/"
CATALOG_FAMILIES = ["RD One"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Kentucky Straight Bourbon Whiskey"
BLEND = "Blend of Straight Bourbon and Straight Rye Whiskeys"
# slug → (expression, aliases, class, finish)
REFILE = {
    "kentucky-straight-bourbon": ("Small Batch", ["RD One Kentucky Straight Bourbon", "RD1 Kentucky Straight Bourbon"], BOURBON, None),
    "finished-with-french-oak": ("Finished with French Oak", [], BOURBON, "French Oak"),
    "finished-with-brazilian-amburana-wood": ("Finished with Brazilian Amburana Wood", [], BOURBON, "Brazilian Amburana Wood"),
    "double-finished-in-oak-and-maple-barrels": ("Double Finished in Oak and Maple Barrels", [], BOURBON, "French Oak and Maple"),
    "ten-year-amburana-finish": ("10 Year Amburana Finish", [], BOURBON, "Brazilian Amburana Wood"),
    "mizurana-and-french-oak-finish": ("Finished with Japanese Mizunara and French Oak", [], BLEND, "Japanese Mizunara and French Oak"),
}
CORE = {"Small Batch", "Finished with French Oak", "Finished with Brazilian Amburana Wood", "Double Finished in Oak and Maple Barrels"}
RARITY = [(r"10 year|mizunara", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
BOILERPLATE_IMG = re.compile(r"Inc\._5000|Artboard|RD_One_Secondary|logo", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"https://rd1spirits.com/pages/{slug}" for slug in REFILE]


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _text(fragment: str | None) -> str | None:
    t = re.sub(r"\s+", " ", (fragment or "").replace("|", " ")).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw, finish = REFILE[slug]
    name = f"RD One {expression}"
    flat = _flatten(page)
    own = flat.split("Home| ›|", 1)[-1]  # past the nav, which lists every sibling bottle
    own = own.split("Quick Links|", 1)[0]

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", own, re.I)
    proof = float(pm.group(1)) if pm else None

    hero = own[:400]
    am = re.search(r"Aged\s+(\d{1,2})\+?\s*Years", hero, re.I)
    years, label = (float(am.group(1)), f"{am.group(1)} yr") if am else (None, None)

    mm = re.search(r"mash bill of (\d+%\s*corn,\s*\d+%\s*rye\s*and\s*\d+%\s*malted barley)", own, re.I)
    mash_raw = re.sub(r"\s+and\s+", ", ", mm.group(1)) if mm else None

    em = re.search(r"The Experience:[^|]*\|\s*(.*?)\|\s*If traditional", own)
    desc = _text(em.group(1)) if em else None

    img = None
    for src in re.findall(r'(?:src|data-src)="((?:https?:)?//rd1spirits\.com/cdn/shop/files/[^"?\s]+\.(?:jpg|jpeg|png))', page):
        if not BOILERPLATE_IMG.search(src):
            img = ("https:" + src) if src.startswith("//") else src
            break

    return BottlingRecord(
        brand_family="RD One", expression=expression, name=name, source_url=f"https://rd1spirits.com/pages/{slug}",
        proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, description=desc,
        image_url=img, finish=finish, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
