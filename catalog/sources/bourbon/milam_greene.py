"""milamandgreenewhiskey.com (Milam & Greene Whiskey Co., Blanco, Texas; milamandgreene.com 301s here). The brand's own
Shopify storefront; robots.txt is Shopify's template (public product pages are crawlable; its comment block asks
automated *shoppers* to use a UCP/MCP checkout endpoint, which concerns buying - nothing here touches a cart, checkout or
the AJAX endpoints it disallows) and sets no Crawl-delay, so DELAY is the project's 6. The product pages are open (no
age gate); each is read through its Shopify `.json` endpoint, whose `body_html` is the whole copy shown on the page (the
rendered page was compared for Triple Cask: nothing more).

Scope: Milam & Greene is partly a sourcing brand (the Single Barrel and Port Rye pages say the whiskey is "selected from
Milam & Greene's growing sourced collection" / "brought from Indiana"; the Triple Cask, Unabridged and Wildlife Collection
blend and age Kentucky, Tennessee and Texas whiskey). Only bottlings the maker's own site lists are imported, and nothing
is inferred about who distilled what.

Proof: pages state it as "ABV: 47.0%" (US labels: proof is twice the ABV, which is what normalize.proof() does), "Proof: 94",
"Bottled at 121.6 proof" or "117.2 Proof". A sibling's strength can appear in the copy (the Triple Cask Cask Strength page
says "You've met Triple Cask at 94 proof"), so an explicit "N proof" is read as the LAST one on the page and an explicit
"Proof: N" before it. Age is read only from an "Aged:" line ("6 years, 11 months" = 6.92); "for over 4 years" on the Bottled
in Bond and "Age: 5 Years" on the two-bottle experiment set are not bottle statements (see below).

What is a row (decided here, so a re-run reproduces it):
  - Unabridged is a numbered annual series (Volume 2 ... 5 are all still on sale, at 117.6, 118, 118.4 and 121.6 proof). It is
    ONE row on the LATEST volume's proof (Volume 5, 121.6) like Booker's; it drifts when Volume 6 appears. The seed (Volume 2,
    117.6) is corrected to it. The volume pages for 2, 3 and 4 are cached as evidence and not parsed. Class is the straight
    bourbon the blend is made of ("A Blend of Straight Bourbon Whiskeys"): a blend of one straight whiskey is that whiskey.
  - Single Barrel has two product pages (an older Tennessee lot and the current Kentucky lot, both ABV 47.0%): one row, the
    current page. The seeded 86 proof was one barrel pick; the standing product is 94.
  - Wildlife Collection (2026): Live Oak (123.4 proof, 6 years 11 months) and Bluebonnet (113.5 proof, 5 years 7 months) are two
    different single-lot releases, each its own row, not core. Triple Cask Cask Strength (117.2) is a distillery-only
    limited, not core.
  - Not imported: "The Answer" (a two-bottle 2 x 350 ml experiment set; the page states neither proof nor a per-bottle
    statement), the Blender's Reserve / Provisions / Top Selling Duo / Unabridged Series bundles and the glassware sets.
  - Seeds with no page on the site stay seeds: the flagship 'Milam & Greene' (94 proof, 4 yr) and The Castle Hill Series.
Mash: Triple Cask, Wildlife (and the Bluebonnet / Answer copy) print "70% corn, 22% malted rye, 8% barley"; rye at 20 percent or
more is high_rye (the shared mash_style() does not read "22% malted rye", so this module sets the style). Very Small Batch
blends a Kentucky and a Tennessee mash bill (two recipes), so none is stored.
Class: the Provisions page names no class beyond 'Bourbon', so class_raw is 'Bourbon Whiskey' (the shop's own product type).
`tasting_notes` is the copy's own Nose (or Aroma) / Palate / Finish lines, which print as "Nose: text", "Nose: | text" or
"NOSE | text" depending on the page; the Color line, the blurb's prose and the award lines are not notes."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import proof as parse_proof

PRODUCER = "Milam & Greene"
DELAY = 6
BASE = "https://milamandgreenewhiskey.com/products/"
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["Milam & Greene"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Milam & Greene"

SB = "Straight Bourbon Whiskey"
# handle → (expression, [catalog names it answers to], class statement, finish)
PAGES = {
    "milam-and-greene-triple-cask-straight-bourbon-whiskey": ("Triple Cask", ["Milam & Greene Triple Cask Straight Bourbon Whiskey"], SB, None),
    "milam-and-greene-provisions-bourbon": ("Provisions", ["Milam & Greene Provisions Bourbon"], "Bourbon Whiskey", None),
    "milam-greene-single-barrel-straight-bourbon-whiskey": ("Single Barrel", ["Milam & Greene Single Barrel Straight Bourbon Whiskey"], SB, None),
    "milam-greene-bottled-in-bond-straight-bourbon-whiskey": ("Bottled in Bond", ["Milam & Greene Bottled in Bond Straight Bourbon Whiskey"],
                                                              "Bottled in Bond " + SB, None),
    "milam-greene-very-small-batch-straight-bourbon-whiskey-finished-with-charred-french-oak-staves": (
        "Very Small Batch", ["Milam & Greene Very Small Batch Straight Bourbon Whiskey"], SB, "Charred French Oak Staves"),
    "milam-and-greene-straight-rye-whiskey-finished-in-port-wine-casks": (
        "Finished in Port Wine Casks Rye", ["Milam & Greene Straight Rye Whiskey Finished in Port Wine Casks", "Milam & Greene Port Finished Rye"],
        "Straight Rye Whiskey", "Port Wine Casks"),
    "milam-and-greene-unabridged-volume-5-straight-bourbon-whiskey": (
        "Unabridged", ["Milam & Greene Unabridged Volume 5", "Milam & Greene Unabridged Volume 2", "Milam & Greene Unabridged Volume 5 Blend of Straight Bourbon Whiskeys"],
        SB, None),
    "milam-and-greene-live-oak": ("Wildlife Collection: Live Oak", ["Milam & Greene Live Oak", "Milam & Greene Cask-Strength 2026 Wildlife Collection: Live Oak Straight Bourbon"], SB, None),
    "milam-and-greene-wildlife-bluebonnet": ("Wildlife Collection: Bluebonnet", ["Milam & Greene Bluebonnet", "Milam & Greene 2026 Wildlife Collection: Bluebonnet Straight Bourbon"], SB, None),
    "triple-cask-cask-strength": ("Triple Cask Cask Strength", ["Milam & Greene Triple Cask Cask Strength Straight Bourbon Whiskey"], SB, None),
}
# Cached as evidence only (no records): the older Single Barrel page, Unabridged Volumes 2-4, The Answer.
EVIDENCE = ["milam-and-greene-single-barrel-straight-bourbon-whiskey", "milam-greene-unabridged-volume-2-a-blend-of-straight-bourbon-whiskies",
            "milam-and-greene-unabridged-volume-3-straight-bourbon-whiskey", "milam-and-greene-unabridged-volume-4-straight-bourbon-whiskey",
            "milam-and-greene-the-answer"]

DISCONTINUED_BY_MAKER = set()
CORE = {"Triple Cask", "Provisions", "Single Barrel", "Bottled in Bond", "Very Small Batch", "Finished in Port Wine Casks Rye"}
RARITY = [(r"wildlife|cask strength", "limited"), (r"unabridged", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + h + ".json" for h in [*PAGES, *EVIDENCE]]


def _text(body_html: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " | ", body_html or "")).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t).strip(" |")


def _proof(text: str) -> float | None:
    m = re.search(r"\bProof:\s*\|?\s*(\d{2,3}(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    found = re.findall(r"(\d{2,3}(?:\.\d+)?)\s*proof", text, re.I)
    if found:
        return float(found[-1])
    a = re.search(r"ABV:\s*\|?\s*(\d{2}(?:\.\d+)?)\s*%", text)
    return parse_proof(a.group(1) + "% ABV") if a else None


def _aged(text: str) -> tuple[float | None, str | None]:
    m = re.search(r"Aged:\s*\|?\s*(\d{1,2}) years?,? (?:and )?(\d{1,2}) months?", text, re.I)
    if not m:
        return None, None
    years = round(int(m.group(1)) + int(m.group(2)) / 12, 2)
    return years, f"{years} yr"


def _mash(text: str) -> tuple[str | None, str | None]:
    """The page's mash statement and the style it implies (rye at 20 percent or more is high_rye)."""
    m = re.search(r"Mash ?bill:?\s*\|?\s*(\d{1,2}% Corn, \d{1,2}% (?:Malted )?Rye, \d{1,2}% (?:Malted )?Barley)", text, re.I) \
        or re.search(r"is (\d{1,2}% corn, \d{1,2}% malted rye, and \d{1,2}% (?:malted )?barley)", text, re.I) \
        or re.search(r"mash bill for both our Texas and Kentucky distillates is (\d{1,2}% corn, \d{1,2}% malted rye, and \d{1,2}% barley)", text, re.I)
    if not m:
        return None, None
    raw = m.group(1).replace(", and ", ", ")
    rye = re.search(r"(\d{1,2})% (?:malted )?rye", raw, re.I)
    return raw, ("high_rye" if rye and int(rye.group(1)) >= 20 else "traditional")


def _notes(text: str) -> str | None:
    """Each Nose / Aroma / Palate / Finish label owns one `|` cell: either inline ("Nose: Mixed...") or the next cell."""
    toks = [t.strip() for t in text.split("|") if t.strip()]
    got: dict[str, str] = {}
    for k, tok in enumerate(toks):
        m = re.fullmatch(r"(Nose|NOSE|Aroma|Palate|PALATE|Finish|FINISH)\b\s*:?\s*(.*)", tok)
        if not m:
            continue
        label = {"nose": "Nose", "aroma": "Nose", "palate": "Palate", "finish": "Finish"}[m.group(1).lower()]
        value = m.group(2) or (toks[k + 1] if k + 1 < len(toks) else "")
        if value and label not in got:
            got[label] = value.strip().rstrip(".")
    if "Palate" not in got:  # a lone stray word is not a tasting block
        return None
    return " ".join(f"{label}: {got[label]}." for label in ("Nose", "Palate", "Finish") if label in got)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.replace(BASE, "").removesuffix(".json")
    if handle not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[handle]
    prod = json.loads(page)["product"]
    text = _text(prod.get("body_html"))
    years, label = _aged(text)
    mash_raw, style = _mash(text)
    img = (prod.get("images") or [{}])[0].get("src")
    name = f"{FAMILY} {expression}"
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=BASE + handle, proof=_proof(text),
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=style, finish=finish,
        tasting_notes=_notes(text), image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
