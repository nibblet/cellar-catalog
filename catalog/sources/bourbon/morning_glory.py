"""spiritsoffrenchlick.com — Spirits of French Lick (West Baden Springs, Indiana), the distillery that makes The Morning
Glory. Scoped to The Morning Glory only: the site's other bourbons (William Dalton, Mattie Gladden, Lee Sinclair) belong to
other catalog rows and are not this module's. A Squarespace site; robots.txt is Squarespace's template (named AI crawlers
disallowed, which this fetcher's own CellarCatalog UA is not; /config, /search, /account, /api and `?format=` forms
disallowed, none used) with no Crawl-delay, so DELAY is the project's usual 6.

The site opens with an "Are You 21?" notice. It is a client-side overlay: the page text, including the product copy, is in
the HTML the server returns, so reading it passes nothing. No click-through, cookie or script is run (judgment call,
flagged for the owner; it differs from Boundary Oak's server-side /age-verification redirect, which is a real gate).

The one page is /spirits-all/the-morning-glory, titled "The Morning Glory Bottled-In-Bond Kasha Bourbon", and its copy
says "100 Proof". Mash bill is listed as ingredients only ("Corn, Rye, Kasha (toasted buckwheat), Buckwheat, and Malt"), no
percentages, so no mash bill and no mash style is taken. The page states no age: "Bottled-In-Bond" carries the Act's
4-year floor and "aged exclusively in our Chai cellar ... 105 entry proof" is a barrel entry proof, not an age or a bottling
proof; neither is read (the Bottled-in-Bond rule: proof is 100 by law, which the page also states, and the floor is not an age).

WHY THIS IS AN ADDITION AND NOT A CORRECTION. The catalog's two seed rows ("The Morning Glory Kasha Bourbon" and a hidden
duplicate "Kasha Bourbon") are 109 proof / 4.5 yr, and the owner's own notes on the visible one read "Office Cigar Lounge
Barrel Pick". A Bottled-in-Bond bottle is exactly 100 proof by law, so a 109-proof barrel pick cannot be the maker's
standard bottle; overwriting it to 100 would erase the member's pick. The maker's bottle therefore gets its own expression,
"Bottled in Bond Kasha Bourbon", whose key shares no tokens with the seed's "Kasha Bourbon" (pass 3 would also refuse it,
the proofs differ by 9). The two 109 rows are reported as STALE and are left as seeds for an owner decision.
Producer: the writer's `coalesce(producer, ...)` leaves the seed rows' "The Morning Glory"; the new row gets
"Spirits of French Lick", the distillery the site and the seed's own specs name."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import proof as parse_proof

PRODUCER = "Spirits of French Lick"
DELAY = 6
BASE = "https://www.spiritsoffrenchlick.com/"
IMAGE_PREFIX = "https://static1.squarespace.com/"
CATALOG_FAMILIES = ["The Morning Glory"]
PRODUCER_BY_FAMILY = {}

PAGE = BASE + "spirits-all/the-morning-glory"
# Evidence only: the lineup page that links it, and the full spirits list.
EVIDENCE = [BASE + "bourbon", BASE + "all-spirits"]
EXPRESSION = "Bottled in Bond Kasha Bourbon"
CORE = {EXPRESSION}
RARITY = [(r".", "limited")]  # craft bottled-in-bond, regional; the seed's own barrel picks are 'allocated'
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [PAGE, *EVIDENCE]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def parse(url: str, page: str) -> BottlingRecord | None:
    if url != PAGE:
        return None
    t = _flat(page)
    # the product's own copy: from its title to the "Where to Buy" block (the previous/next carousel follows it)
    i = t.find("The Morning Glory Bottled-In-Bond Kasha Bourbon")
    j = t.find("Where to Buy", i)
    own = t[i:j] if 0 <= i < j else ""
    if not own:
        return None
    m = re.search(r"\|\s*(\d{2,3}(?:\.\d)?)\s*Proof\s*\|", own, re.I)
    proof = parse_proof(m.group(1) + " proof") if m else None
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    img = html.unescape(og.group(1)).replace("http://", "https://") if og else None
    return BottlingRecord(
        brand_family="The Morning Glory", expression=EXPRESSION, name="The Morning Glory Bottled in Bond Kasha Bourbon",
        source_url=url, proof=proof, age_years=None, age_label=None,
        class_raw="Bottled in Bond Straight Bourbon Whiskey", mash_raw=None, mash_style=None, image_url=img,
        aliases=["The Morning Glory Bottled-In-Bond Kasha Bourbon"], is_core_range=True,
    )
