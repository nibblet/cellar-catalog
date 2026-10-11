"""breckenridgedistillery.com (Breckenridge Distillery, Colorado — the family is the maker's own). WordPress;
spirits-sitemap.xml lists about forty spirits, of which roughly fifteen are whiskey (the rest: vodkas,
gin, aquavit, bitter, rums, tequila, seltzers, non-alcoholic Mock One, and the flavored Honey / Peach /
Spiced whiskeys, which are out of scope). Each page prints "43% ALC/VOL | 86 PROOF" right after the
title; the product's own copy runs from "VIEW ALL PRODUCTS|" to the first "FIND NEAR ME|" / "HOME DELIVERY|"
and everything after that is a carousel of *other* spirits (so a match there belongs to a sibling).
Gotchas: the proof line is sometimes printed "46%% ALC/VOL" (a templating typo, harmless), Single Barrel
prints a range ("100.4-118.1 PROOF", "Proof varies per barrel selection") which is never a fact, and
several finishes (Double Barrel, Jamaican Rum Cask, Sexy Motor Oil) never say what the base spirit is, so
their class is left as plain "Whiskey" instead of guessing bourbon. Collectors Art Series #6 and Patriotic
Reserve don't say what they are and are skipped. Most pages carry no og:image."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Breckenridge"
DELAY = 6
SITEMAP = "https://breckenridgedistillery.com/spirits-sitemap.xml"
CATALOG_FAMILIES = ["Breckenridge"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class)
REFILE = {
    "breckenridge-bourbon": ("Bourbon", ["Breckenridge Bourbon Whiskey"], "Bourbon Whiskey"),
    "breckenridge-rye-whiskey": ("Rye", ["Breckenridge Rye Whiskey"], "Rye Whiskey"),
    "breckenridge-distillers-high-proof": ("Distillers High Proof", [], "Blended Bourbon Whiskey"),
    "breckenridge-single-barrel": ("Single Barrel", [], "Bourbon Whiskey"),
    "limited-edition-single-barrel": ("Broncos Single Barrel", ["Breckenridge Limited Edition Single Barrel"], "Single Barrel Bourbon Whiskey"),
    "breckenridge-double-barrel": ("Double Barrel", [], "Whiskey"),
    "breckenridge-whiskey-port-cask-finish": ("Port Cask Finish", [], "Bourbon Whiskey"),
    "breckenridge-whiskey-px-cask-finish": ("PX Cask Finish", [], "Bourbon Whiskey"),
    "breckenridge-rum-cask-finish": ("Rum Cask Finish", [], "Bourbon Whiskey"),
    "breckenridge-whiskey-finished-in-cognac-casks": ("Cognac Cask Finish", [], "Bourbon Whiskey"),
    "breckenridge-whiskey-jamaican-rum-cask": ("Jamaican Rum Cask", [], "Whiskey"),
    "breckenridge-whiskey-powder-hound": ("Powder Hound", [], "Blended Bourbon Whiskey"),
    "breckenridge-peat-fetish": ("Peat Fetish", [], "American Single Malt Whiskey"),
    "breckenridge-dark-arts-whiskey-distilled-from-malt-mash": ("Dark Arts", ["Breckenridge Dark Arts: Whiskey Distilled from Malt Mash"], "American Single Malt Whiskey"),
    "breckenridge-two-drams-blended-whiskey": ("Two Drams", [], "Blended Whiskey"),
    "breckenridge-sexy-motor-oil": ("Sexy Motor Oil", [], "Whiskey"),
    "specialty-releasebreckenridge-buddy-pass-imperial-stout-cask": ("Imperial Stout Cask", ["Breckenridge Whiskey Imperial Stout Cask", "Breckenridge Buddy Pass Imperial Stout Cask"], "Whiskey"),
    "specialty-release-broncos-bourbon": ("Broncos Bourbon", [], "Bourbon Whiskey"),
}
CORE = {"Bourbon", "Rye", "Distillers High Proof", "Single Barrel", "Port Cask Finish", "PX Cask Finish", "Rum Cask Finish", "Dark Arts", "Peat Fetish", "Double Barrel"}
RARITY = [(r"broncos|sexy motor|powder hound|imperial stout|jamaican|cognac|two drams", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = re.findall(r"<loc>([^<]+/spirits/([^</]+)/)</loc>", fetcher.get(SITEMAP))
    return sorted({u for u, slug in urls if slug in REFILE})


def _text(page: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"Breckenridge {expression}"
    text = _text(page)
    start = text.find("VIEW ALL PRODUCTS|")
    own = text[start + 18:] if start >= 0 else text
    cut = [i for i in (own.find("FIND NEAR ME|"), own.find("HOME DELIVERY|"), own.find("Home Delivery|")) if i > 0]
    own = own[:min(cut)] if cut else own[:1500]

    proof = None
    m = re.search(r"\|\s*(\d{2,3}(?:\.\d+)?)(-\d+(?:\.\d+)?)?\s*PROOF", own)
    if m and not m.group(2):  # a range (Single Barrel) is not a bottling proof
        proof = float(m.group(1))

    years = label = None
    if slug == "breckenridge-bourbon":
        years, label = age("aged for a minimum of three years")
    elif slug == "breckenridge-peat-fetish":
        years, label = age("aged for over four years")

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    desc = re.sub(r"^[^|]*\|[^|]*PROOF\s*\|\s*", "", own).strip(" |") or None
    desc = re.sub(r"\s*\|\s*", " ", desc)[:600] if desc else None

    return BottlingRecord(
        brand_family="Breckenridge", expression=expression, name=name, source_url=url,
        proof=proof, age_years=years, age_label=label, class_raw=class_raw,
        description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
