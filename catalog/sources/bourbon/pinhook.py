"""pinhookbourbon.com (Pinhook, Kentucky — a non-distiller producer: it sources barrels, blends and proofs them).
Shopify store, rendered HTML. robots.txt allows product pages (it disallows cart/checkout/AJAX only and points
agents at a UCP/MCP commerce endpoint for *buying*; this importer only reads product pages, never a cart). The
page carries an "Are you old enough to drink whiskey?" overlay in its static HTML — the product copy is served
regardless and nothing here clicks through or alters it.

Shopify's `body_html` carries only the marketing blurb; the numbers live in the rendered page's last
"Details" block ("Corn | 75% | Rye | 15% | Malted Barley | 10% | Proof | 100"), because the page also has an
earlier "Details" block about the racehorse the release is named for ("Foaled ... Bred by ..."). The proof is
read from the *last* block only, and only a plain "Proof | N" (Artist Series No. 3 prints "Batch #1 Proof /
Batch #2 Proof" and is skipped as ambiguous).

Pinhook names every annual vintage after a racehorse and gives each vintage its own product page
(Bohemian Bourbon, Bourbon Heist, Bourbon Resolve ... are all vintages of the one Straight Bourbon). A vintage
is not a bottling: the flagship Straight Bourbon, Straight Rye, High Proof Bourbon / Rye and Cask Strength
Bourbon each fold every vintage page into one record, listed oldest to newest so the newest page supplies the
facts (`_dedupe` keeps the last). The Vertical Series is different — a new age each year, a different title and a
different proof — so each age is its own bottling ("Vertical Series Bourbon 7 Year"). The racehorse names stay
on as aliases of the seed rows ("Pinhook War Vertical Series - 7 Year", "Pinhook Tiz Rye Time Vertical Series
- 4 Year", "Pinhook Bohemian") so each existing row claims its page by name.

Not imported (and why):
- True Single Barrel / Single Barrel / "The Big Horse" pages: a barrel selection, a different barrel and
  proof every year (a program, not a bottling), and half of them print no proof at all.
- Collaboration Series No. 3 (Starward Australian single malt — not American whiskey).
- Artist Series No. 3 (two batch proofs; only the cask-strength batch is sold, but the page does not label
  which proof is which in words the importer should trust).
- The five bundle pages (a bundle is not a bottling).

A decimal rye share ("20.5% Rye") defeats `normalize.mash_style()` (see `parse`), so the style is computed
from the Details grains here: rye share >= 20% is high-rye, otherwise traditional (rye whiskeys take their style
from the spirit type).

Age is read from the product's own title and opening blurb only (up to "Add to cart" / "No Longer Available" /
"Find a location near you"): every flagship page ends with a disclaimer naming "our 5yr Cask Strength Bourbon",
and the Vertical Series copy explains the series "as they age from four to sixteen years", neither of which is
that bottling's age. "Aged more than 4 years" is the maker's stated age (4); "an average age of three years
and four months" is not read; the Collaboration No. 5 blend ("3 years in one barrel then 3 more in another")
and No. 4's "aged 6 years" sit below the blurb and are not read, so those rows keep whatever age they have."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Pinhook"
DELAY = 6
SITEMAP = "https://pinhookbourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://pinhookbourbon.com/"
CATALOG_FAMILIES = ["Pinhook"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Straight Bourbon Whiskey"
RYE = "Straight Rye Whiskey"
PLAIN_BOURBON = "Bourbon Whiskey"
PLAIN_RYE = "Rye Whiskey"
BLEND = "Blend of Straight Bourbon and Rye Whiskeys"

# expression → (class statement, seed names it answers to, [product handles, oldest vintage first]).
BOTTLINGS = {
    "Straight Bourbon": (BOURBON, ["Pinhook Bohemian"], [
        "bourbon-country", "bohemian-bourbon", "bourbon-heist", "flagship-bourbon", "flagship-bourbon-1",
        "flagship-bourbon-2", "straight-bourbon", "straight-bourbon-2026"]),
    "Straight Rye": (RYE, ["Pinhook Munny Rye"], [
        "bourbon-n-rye", "rye-humor", "ryed-on", "hard-rye-guy", "flagship-rye", "flagship-rye-1",
        "straight-rye", "straight-rye-2026"]),
    "High Proof Bourbon": (BOURBON, ["Pinhook Bourbondini"], [
        "bohemian-bourbon-high-proof", "bourbon-heist-high-proof", "high-proof-bourbon", "high-proof-bourbon-1"]),
    "High Proof Rye": (RYE, [], ["high-proof-hard-rye-guy", "high-proof-rye"]),
    "Cask Strength Bourbon": (BOURBON, ["Pinhook Cask Strength Bourbon Bourbon Breeze"], [
        "bourbon-country-cask-strength", "cask-strength-bourbon-5-yr", "cask-strength-bourbon-5-year", "cask-strength-bourbon"]),
    "Cask Strength Rye": (RYE, [], ["rye-humor-cask-strength"]),
    "Vertical Series Bourbon 4 Year": (BOURBON, ["Pinhook Bourbon War"], ["bourbon-war-vertical-series-4-year"]),
    "Vertical Series Bourbon 5 Year": (BOURBON, ["Pinhook War Vertical Series - 5 Year"], ["bourbon-war-vertical-series-5-year"]),
    "Vertical Series Bourbon 6 Year": (BOURBON, ["Pinhook War Vertical Series - 6 Year"], ["bourbon-war-vertical-6-year"]),
    "Vertical Series Bourbon 7 Year": (BOURBON, ["Pinhook War Vertical Series - 7 Year"], ["vertical-series-bourbon"]),
    "Vertical Series Bourbon 8 Year": (BOURBON, ["Pinhook War Vertical Series - 8 Year"], ["vertical-series-bourbon-1"]),
    "Vertical Series Bourbon 9 Year": (BOURBON, ["Pinhook War Vertical Series - 9 Year"], ["vertical-series-bourbon-2"]),
    "Vertical Series Bourbon 10 Year": (BOURBON, ["Pinhook War Vertical Series - 10 Year"], ["vertical-series-bourbon-10-year"]),
    "Vertical Series Bourbon 11 Year": (BOURBON, [], ["vertical-series-bourbon-11-year"]),
    "Vertical Series Rye 4 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 4 Year"], ["tiz-rye-time-vertical-series-4-year"]),
    "Vertical Series Rye 5 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 5 Year"], ["tiz-rye-time-vertical-series-5-year"]),
    "Vertical Series Rye 6 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 6 Year"], ["vertical-series-rye-1"]),
    "Vertical Series Rye 7 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 7 Year"], ["vertical-series-rye-7yr"]),
    # The two pages below have their handles swapped against their titles (…/vertical-series-rye is the 8 Year,
    # …/vertical-series-rye-8-year is the 9 Year); the seed's proofs (108.4, 111.2) agree with the page titles.
    "Vertical Series Rye 8 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 8 Year"], ["vertical-series-rye"]),
    "Vertical Series Rye 9 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 9 Year"], ["vertical-series-rye-8-year"]),
    "Vertical Series Rye 10 Year": (RYE, ["Pinhook Tiz Rye Time Vertical Series - 10 Year"], ["vertical-series-rye-10-year"]),
    "Collaboration Series No. 1 André Mack": (PLAIN_BOURBON, [], ["collaboration-series"]),
    "Collaboration Series No. 2 Garrett Oliver": (PLAIN_BOURBON, [], ["collaboration-series-2"]),
    "Collaboration Series No. 4 Neal Bodenheimer Rye": (PLAIN_RYE, [], ["collaboration-series-no-4"]),
    "Collaboration Series No. 5 Donald Link and Stephen Stryjewski": (PLAIN_BOURBON, [], ["collaboration-series-no-5"]),
    "Artist Series No. 1 Accidental Marriage": (BLEND, [], ["no-1-accidental-marriage"]),
    "Artist Series No. 2 Whiskey Nicking": (BLEND, [], ["2021-artist-series-no-2"]),
}
REFILE = {h: expr for expr, (_c, _a, handles) in BOTTLINGS.items() for h in handles}
CORE = {"Straight Bourbon", "Straight Rye", "Cask Strength Bourbon"}
RARITY = [(r"vertical series|collaboration|artist series|high proof|cask strength", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://pinhookbourbon.com/products/{h}" for h in REFILE]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _text(fragment: str | None) -> str | None:
    t = re.sub(r"\s*\|\s*", " ", fragment or "").strip()
    return re.sub(r"\s+", " ", t) or None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    expression = REFILE.get(handle)
    if expression is None:
        return None
    _cls, seed_names, _handles = BOTTLINGS[expression]
    class_raw = _cls
    name = f"Pinhook {expression}"
    own = _flat(page)
    body = own.split("Log in|", 1)[-1]
    head = re.split(r"No Longer Available|Add to cart|Currently unavailable|Find a location near you", body)[0]

    # The product's own title is the first element after the optional "SPECIAL RELEASE" / year pills.
    parts = [p.strip() for p in head.split("|") if p.strip()]
    parts = [p for p in parts if not re.fullmatch(r"SPECIAL RELEASE|\d{4}", p)]
    title = parts[0] if parts else ""
    years, label = age(title)
    if years is None and label is None:
        years, label = age(_text(head))

    # Last "Details" block that starts with a grain or Proof row (the racehorse "Details" block precedes it).
    blocks = re.findall(r"Details\s*\|\s*((?:Corn|Rye|Wheat|Malted Barley|Proof)\s*\|.*?)(?=\| Explore our other|$)", body)
    block = blocks[-1] if blocks else ""
    pm = re.search(r"(?:^|\|)\s*Proof\s*\|\s*(\d{2,3}(?:\.\d+)?)\b", block)
    proof = float(pm.group(1)) if pm else None
    grains = re.findall(r"(Corn|Rye|Wheat|Malted Barley)\s*\|\s*(\d+(?:\.\d+)?)%", block)
    mash_raw = ", ".join(f"{pct}% {g}" for g, pct in grains) if grains and class_raw != BLEND else None
    # `normalize.mash_style()` reads "20.5% Rye" as "5% rye" (its percentage pattern takes no decimals), which
    # turns the Vertical Series' 20.5%-rye bourbon into "traditional"; the share is computed here instead.
    style = None
    if mash_raw and "Rye Whiskey" not in class_raw:
        rye_pct = next((float(pct) for g, pct in grains if g == "Rye"), None)
        style = None if rye_pct is None else ("high_rye" if rye_pct >= 20 else "traditional")

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]

    return BottlingRecord(
        brand_family="Pinhook", expression=expression, name=name,
        source_url=f"https://pinhookbourbon.com/products/{handle}", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style=style, description=_text(head)[:600] if _text(head) else None,
        image_url=html.unescape(img) if img else None, aliases=sorted(set(seed_names) - {name}),
        is_core_range=expression in CORE,
    )
