"""shortbarrelbourbon.com (Shortbarrel, Atlanta — shortbarrelwhiskey.com 301s here). A Shopify store whose
sitemap is the product index; robots.txt sets no Crawl-delay (DELAY 6 as for every Shopify source). One page
per release with a "Product Notes" block in the maker's own voice ("our flagship", "Our rye is our most
awarded product"). The store is a Shopify Collective front: checkout is fulfilled by a licensed third-party
retailer (Longhorn Wine & Spirits, Bottle Nexus network) and the products carry that retailer's tags, but the
text, photos and URLs are Shortbarrel's own on Shortbarrel's own domain, so they are the maker's page.
Proof is printed in prose or a "Proof:" line and is read only from the Product Notes ("Bottled at 92 proof",
"this 100-proof release", "Proof: 108.6"); Sapsquatch says "Proof: Batch-specific" (no number) and Cigar Batch
IV, Double Oaked, Tokaji Rye and Bees Knees VI state none, so those are listed, not confirmed. The Afterswarm
page covers two releases (Georgia Wildflower, 110.6, and II: Meadowfoam, 108.6): one record each, each with
its own proof. Age is read only where it is a plain floor ("aged a minimum of 5 years", "bourbons aged six
years and older", "all over 6 years old"); component ranges ("four-to-five-year-old", "6-8+ year", "typically
5-9 years", "10+ year-old rye is 40% of the blend") are not an age. Four Grain's page contradicts itself in a
carousel blurb ("a wheated bourbon" under a headline about four grains) and carries a stray editing note
("This stays aligned with the current page's claims ..."); the name and the body copy say four grain, which
is what is read. Skipped: the two Shortlist Barrel Pick pages (one-off barrels for a members program), the
ALW 8-Year single barrel and The Shortlist #2 (empty copy), Apple Brandy (brandy), O4D Honey Gin, The Shortlist
membership and merch.

`tasting_notes` is the page's own "Tasting Notes" section (Nose / Palate / Finish lines, or one paragraph) inside the Product
Notes. Most pages have none: Bees Knees' regional honey profiles and Afterswarm's Wildflower-versus-Meadowfoam comparison
describe several releases at once, so they are deliberately not taken as one bottle's notes."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Shortbarrel"
DELAY = 6
SITEMAP = "https://shortbarrelbourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://shortbarrelbourbon.com/"
CATALOG_FAMILIES = ["Shortbarrel"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Straight Bourbon Whiskey"
# handle → (expression, aliases, class_raw, finish, label). Several handles read the same spirit class; the
# class is the maker's own words ("Kentucky straight bourbons", "MGP rye barrels", "95/5 rye").
REFILE = {
    "shortbarrel-bourbon-four-grain-750ml": ("Four Grain", [], BOURBON, None),
    "shortbarrel-bourbon-toasted-barrel-kentucky-straight-bourbon-94-proof-750ml": ("Toasted", [], "Kentucky Straight Bourbon Whiskey", "Toasted Kelvin Barrels"),
    "shortbarrel-bourbon-rye-101-750ml": ("Rye 101", [], "Rye Whiskey", None),
    "shortbarrel-bourbon-afterswarm-ii-meadowfoam-750ml": (
        "Afterswarm II: Meadowfoam Rye", ["Shortbarrel The Afterswarm II: Meadowfoam Rye", "Shortbarrel Afterswarm II (Meadowfoam)"],
        "Rye Whiskey", "Honey-Conditioned Barrels"),
    "shortbarrel-bourbon-sapsquatch": ("Sapsquatch", [], "Bourbon Whiskey", "Maple Syrup-Conditioned Toasted Barrels"),
    "shortbarrel-bourbon-tokaji-rye": ("Tokaji Rye", ["Shortbarrel Tokaji Cask Finish Rye"], "Rye Whiskey", "Tokaji Casks"),
    "summer-solstice": ("Summer Solstice", [], "Bourbon Whiskey", "Orange Wine Casks"),
    "shortbarrel-cigar-batch-iv": ("Cigar Batch IV", [], "Bourbon Whiskey", None),
    "shortbarrel-double-oak-sb-6-collective": ("Double Oaked", [], "Bourbon Whiskey", "Double Oaked"),
    "shortbarrel-bourbon-bees-knees-5-honey-pot": ("Bees Knees VI: The Honey Pot", [], "Bourbon Whiskey", "Honey-Conditioned Barrels"),
}
CORE = {"Four Grain", "Toasted", "Rye 101"}  # the site's own "Core Releases" collection
RARITY = [(r"summer solstice|afterswarm|tokaji|sapsquatch|cigar batch|bees knees|double oak", "limited"), (r".", "shelf")]
MASH_BILLS = {}

# The second release on the Afterswarm page: "AFTERSWARM: GEORGIA WILDFLOWER ... Proof: 110.6".
AFTERSWARM_I = "shortbarrel-bourbon-afterswarm-ii-meadowfoam-750ml"


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://shortbarrelbourbon.com/products/{h}" for h in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _notes(page: str) -> str:
    """The product's own "Product Notes" block, flattened, up to the shared Shortlist/flagship promo tail."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("’", "'").replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\|\s*)+", "| ", t)
    i = t.find("Product Notes")
    if i < 0:
        return ""
    t = t[i + len("Product Notes"):]
    for stop in ("THE SHORTLIST: THIS IS FOR THE REAL ONES", "OUR AWARD WINNING FLAGSHIP", "They love us", "STAY IN THE FLOW"):
        j = t.find(stop)
        if j >= 0:
            t = t[:j]
    return t.strip()


_NOTE_LABELS = {"nose", "palate", "finish"}


def _tasting(notes: str) -> str | None:
    segs = [x.strip() for x in notes.split("|") if x.strip()]
    start = next((i for i, x in enumerate(segs) if re.match(r"tasting notes\s*:?$", x, re.I)), None)
    if start is None:
        return None
    body = segs[start + 1:]
    parts, j = [], 0
    while j + 1 < len(body) and body[j].rstrip(":").lower() in _NOTE_LABELS:
        parts.append(f"{body[j].rstrip(':').title()}: {body[j + 1].rstrip('. ')}.")
        j += 2
    if parts:
        return " ".join(parts)[:900]
    if body and not body[0].startswith("Loading image"):
        return re.sub(r"\s+", " ", body[0]).strip()[:900]  # one paragraph ("TASTING NOTES: The nose opens with ...")
    return None


def _proof(notes: str, handle: str) -> float | None:
    if handle == AFTERSWARM_I:
        m = re.search(r"AFTERSWARM II: MEADOWFOAM\s*\|?.*?Proof:\s*(\d{2,3}(?:\.\d+)?)", notes, re.S)
        return float(m.group(1)) if m else None
    m = re.search(r"(?:bottled at|bottled non-chill filtered at)\s+(\d{2,3}(?:\.\d+)?)\s*proof", notes, re.I) \
        or re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof release", notes, re.I) \
        or re.search(r"Proof:\s*(\d{2,3}(?:\.\d+)?)\b", notes)
    if m:
        return float(m.group(1))
    # Rye 101 states its proof as the product name's own number, never as "N proof": "We feel that 101 is the perfect proof".
    m = re.search(r"\bthat (\d{2,3}) is the perfect proof", notes, re.I)
    return float(m.group(1)) if m else None


def _age(notes: str) -> tuple[float | None, str | None]:
    notes = re.sub(r"\s*\|\s*", " ", notes)  # the block's markup breaks ("aged| six years and older") must not split a phrase
    t = re.sub(r"\b\w+[- ]to[- ]\w+[- ]year[- ]old\b", " ", notes, flags=re.I)  # "four-to-five-year-old": a component range
    t = re.sub(r"\b\d+\s*[–-]\s*\d+\+?\s*year", " ", t)                          # "6–8+ year", "5–9 years"
    t = re.sub(r"\b10\+ year-old rye", " ", t)                                    # 40% of Tokaji's blend, not the bottling
    return age(t)


def parse(url: str, page: str) -> list[BottlingRecord] | BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases, class_raw, finish = REFILE[handle]
    name = f"Shortbarrel {expression}"
    notes = _notes(page)
    if not notes:
        return None
    img = (re.search(r'property="og:image:secure_url" content="([^"]+)"', page) or re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]
    years, label = _age(notes)
    proof = _proof(notes, handle)
    if class_raw and re.search(r"cask strength|barrel proof", notes, re.I):
        class_raw += " Cask Strength"
    mash = None
    if expression == "Four Grain":
        mash = "Four Grain"  # the name and the body copy say four grain; the sibling blurb that says wheated is not read
    rec = BottlingRecord(
        brand_family="Shortbarrel", expression=expression, name=name, source_url=url, proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash, description=_text(notes[:600]), tasting_notes=_tasting(notes),
        image_url=html.unescape(img) if img else None, finish=finish, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
    if handle != AFTERSWARM_I:
        return rec
    # The same page also states the first Afterswarm, Georgia Wildflower, with its own proof.
    gm = re.search(r"AFTERSWARM: GEORGIA WILDFLOWER\s*\|?.*?Proof:\s*(\d{2,3}(?:\.\d+)?)", notes, re.S)
    first = BottlingRecord(
        brand_family="Shortbarrel", expression="Afterswarm: Georgia Wildflower Rye", name="Shortbarrel Afterswarm: Georgia Wildflower Rye",
        source_url=url, proof=float(gm.group(1)) if gm else None, class_raw=class_raw, description=_text(notes[:600]),
        image_url=rec.image_url, finish=finish, aliases=["Shortbarrel Afterswarm", "Shortbarrel Afterswarm (Georgia Wildflower)"], is_core_range=False,
    )
    rec.age_years, rec.age_label = None, None
    return [rec, first]
