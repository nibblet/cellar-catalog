"""brothersbondbourbon.com (Brother's Bond Distilling Co. LLC — the brand's own Shopify storefront). The domain is the
maker's, not a retailer's: the footer and the cookie notice name Brother's Bond Distilling Co. LLC, and the five
bottles are its own products, sold from the site (the same store also sells barware, chocolate and merchandise, none
of which is imported). robots.txt is Shopify's template with no Crawl-delay, so DELAY is the project's usual 6; its
comment block asks automated shoppers to use a UCP/MCP checkout endpoint, which concerns buying, not reading product
pages, and nothing here touches a cart or checkout.

The list is the five bottles linked from the home page (the "Shop" tiles): Straight Bourbon Whiskey, Bottled-In-Bond
Straight Bourbon Whiskey, Regenerative Grain Bourbon, Original Cask Strength Straight Bourbon Whiskey and American
Blended Rye Whiskey. The handles all start "new-brothers-bond...-copy" (Shopify duplicated the old pages when the
site was rebuilt); the handle is not the name, the page heading is.

Facts live in each page's blurb and its "Details" block, read from the product section only (the text between the
last gallery marker and "Tasting Notes"; "You May Also Like" carries the sibling bottles):
- Strength: "bottled at 40% ALC/VOL (80 proof)", "100 Proof", "bottled at 46% ALC/VOL (92 proof)", "bottled at 47.5%
  ALC/VOL (95 proof)". Original Cask Strength states "Bottled at barrel proof (varies by batch)" — no number, so it is
  listed and corrected but not confirmed, and the seed's 114.1 stays.
- Mash bill: "Mash Bill: 65% Corn, 22% Rye, 13% Wheat & Barley" (the maker lumps wheat and barley into one figure;
  kept as printed).
- Age: every blurb says "aged a minimum of N years" (Straight Bourbon 4, Regenerative Grain 4, Original Cask Strength 4,
  American Blended Rye 4, Bottled-in-Bond 7: "a minimum of seven years — three years longer than required"). That is the
  maker's own statement about the bottling (the youngest whiskey in it), not the legal definition, and it is how the
  label's age statement works; normalize.age() reads "aged ... a minimum of N years". The seeds said NAS; the diff
  corrects them to the stated age. Listed for the owner.

Batches: the Regenerative Grain release is numbered by batch on the label ("New Batch", "Batch 0002" in the seed), but
the maker's page is one standing product with no batch number, so it is ONE bottling, "Regenerative Grain Bourbon",
and the seed's batch is an alias. Original Cask Strength is likewise one bottling ("for each batch release, 70 of the
finest barrels are hand-selected"); batches live on the bottle, never as records.

Not imported: the "Bottled-In-Bond ... (Winter Special)" listing (same page, same copy, same 100 proof; a seasonal
sale of the standard bottle, not a bottling) and every non-whiskey product.

Class: the rye's name carries the word "Blended" (four mash bills barrel-blended); its class is rye whiskey, not a
cross-type blend, so class_raw says "Rye Whiskey" (a "blend" in class_raw would send spirit_type() to 'blend').
Mash style: the Straight Bourbon page calls itself "a four-grain, high-rye straight bourbon" and the Regenerative Grain
page "four-grain", so both are four_grain (normalize reads that phrase first); the others follow their recipe."""
from __future__ import annotations

import html
import re
import urllib.parse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof as parse_proof

PRODUCER = "Brother's Bond"
DELAY = 6
SITEMAP = "https://brothersbondbourbon.com/sitemap_products_1.xml"
IMAGE_PREFIX = "https://brothersbondbourbon.com/"
CATALOG_FAMILIES = ["Brother's Bond"]
PRODUCER_BY_FAMILY = {}

BASE = "https://brothersbondbourbon.com/products/"
BOURBON = "Straight Bourbon Whiskey"
# handle → (expression, name, [catalog names it answers to], class statement, style the page states)
PAGES = {
    "new-brothers-bond®-straight-bourbon-whiskey-copy": (
        "Straight Bourbon", "Brother's Bond Straight Bourbon", ["Brother's Bond Bourbon"], BOURBON, "four_grain"),
    "new-brother-s-bond®-bottled-in-bond-straight-bourbon-whiskey-copy": (
        "Bottled in Bond", "Brother's Bond Bottled in Bond", ["Brother's Bond Bottled-In-Bond Straight Bourbon Whiskey"],
        "Bottled in Bond " + BOURBON, None),
    "new-brothers-bond®-regenerative-grain-bourbon-copy": (
        "Regenerative Grain Bourbon", "Brother's Bond Regenerative Grain Bourbon",
        ["Brother's Bond Regenerative Grain New Batch", "Brother's Bond Regenerative Grain"], BOURBON, "four_grain"),
    "new-brothers-bond®-original-cask-strength-straight-bourbon-whiskey-copy": (
        "Original Cask Strength", "Brother's Bond Original Cask Strength",
        ["Brother's Bond Cask Strength Straight Bourbon"], BOURBON + " Cask Strength", None),
    "new-brothers-bond®-american-blended-rye-whiskey-copy": (
        "American Blended Rye", "Brother's Bond American Blended Rye Whiskey", ["Brother's Bond American Blended Rye"],
        "Rye Whiskey", None),
}
CORE = {"Straight Bourbon", "Bottled in Bond", "Regenerative Grain Bourbon", "Original Cask Strength", "American Blended Rye"}
RARITY = [(r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + urllib.parse.quote(h) for h in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def _product(own: str) -> str:
    """The product's own section: after the last gallery marker, before the tasting notes and the sibling carousel."""
    marks = list(re.finditer(r"Go to item \d+ \|", own))
    start = marks[-1].end() if marks else 0
    seg = own[start:]
    end = seg.find("| Tasting Notes")
    return seg[:end] if end > 0 else seg


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
    if handle not in PAGES:
        return None
    expression, name, aliases, class_raw, style = PAGES[handle]
    seg = _product(_flat(page))

    sm = re.search(r"\bStrength \| (.*?) \| Color\b", seg)
    strength = sm.group(1) if sm else ""
    proof = parse_proof(strength) if re.search(r"\d", strength) else None

    years, label = age(seg)

    # The blurb is printed twice: a truncated teaser ("22% Rye,... | Read More") and the full text; take the full one.
    mash_raw = None
    for mm in re.finditer(r"Mash Bill: (\d[^|]*?)(?= \| )", seg):
        if not mm.group(1).rstrip().endswith(("...", ",", "\u2026")):
            mash_raw = re.sub(r"(\d)\s+%", r"\1%", mm.group(1)).strip().rstrip(".")
            break

    og = re.search(r'property="og:image" content="([^"]+)"', page)
    img = html.unescape(og.group(1)).replace("http://", "https://") if og else None

    return BottlingRecord(
        brand_family="Brother's Bond", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=style,
        image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
