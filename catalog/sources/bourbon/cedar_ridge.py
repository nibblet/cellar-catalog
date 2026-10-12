"""cedarridgedistillery.com (Cedar Ridge Distillery, Swisher, Iowa). WordPress; whiskeys-sitemap.xml lists
one page per bottling, all static HTML. Only a minority of pages state a proof, and in three different
ways: a "112 Proof | 56% ABV | 750 ML" line (the 2025/2026 releases), proof inside the blurb ("finished
... and bottled at 115 proof", "for added complexity at 94 proof"), and the Bottled-in-Bond pair, where
the bourbon page only recites the Act ("a minimum of 4 years at 100 proof" — the law's floor, so the age
is not read from it) and the rye page states "4-years old / Bottled at 100 Proof". The flagship Straight
Bourbon page states no proof at all; its blurb calls it "Our Original 86 Bourbon", so 86 is read from the
maker's own product name (PROOF_FROM_NAME) rather than left blank. Single Barrel Collection lists two
different barrels with their own ages and proofs, so no single proof is taken. Every mash bill is a
structured "Mashbill | 74% Corn | 14% Malted Rye | 12% Malted Barley" block. Clown's Iowa Shine is
unaged raw spirit and is skipped. The pages have no tasting block, so `tasting_notes` is only the product-copy
sentences that name a "note" (three pages: "bold notes of tobacco", "a sweet honey note"); vague praise ("flavorful",
"tangy"), cask and malting explanations and shipping text are not notes, so most pages leave it None."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Cedar Ridge"
DELAY = 6
SITEMAP = "https://cedarridgedistillery.com/whiskeys-sitemap.xml"
CATALOG_FAMILIES = ["Cedar Ridge"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class).  expression None is the flagship.
REFILE = {
    "straight-bourbon-whiskey": ("Original 86", ["Cedar Ridge Bourbon", "Cedar Ridge Straight Bourbon Whiskey"], "Iowa Straight Bourbon Whiskey"),
    "straight-rye-whiskey": ("Straight Rye", ["Cedar Ridge Rye"], "Iowa Straight Rye Whiskey"),
    "wheat-whiskey": ("Wheat Whiskey", [], "American Single Malt Whiskey"),
    "barrel-proof": ("Barrel Proof Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "bottled-in-bond-bourbon": ("Bottled in Bond Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "bottled-in-bond-rye-whiskey": ("Bottled in Bond Rye", [], "Iowa Straight Rye Whiskey"),
    "double-barrel-bourbon": ("Double Barrel Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "double-barrel-rye": ("Double Barrel Rye", [], "Iowa Straight Rye Whiskey"),
    "honey-bourbon": ("Honey Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "sir-maple": ("Sir Maple Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "orange-px-sherry-bourbon": ("Orange PX Sherry Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "amontillado-sherry-finished-bourbon": ("Amontillado Sherry Finished Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "port-cask-bourbon": ("Port Cask Finished Bourbon", [], "Iowa Straight Bourbon Whiskey"),
    "port-cask-finished-straight-rye-whiskey": ("Port Cask Finished Straight Rye", [], "Iowa Straight Rye Whiskey"),
    "anniversary-edition-bourbon": ("Anniversary Edition 2025", ["Cedar Ridge Anniversary Edition Bourbon"], "Iowa Straight Bourbon Whiskey"),
    "anniversary-edition-2026": ("Anniversary Edition 2026", [], "Iowa Straight Bourbon Whiskey"),
    "nine-three-quarters-rye": ("Nine & Three Quarters Rye", [], "Iowa Straight Rye Whiskey"),
    "single-barrel-collection": ("Single Barrel Collection", ["Cedar Ridge S.B.C."], "Iowa Straight Bourbon Whiskey"),
    "slipknot-no-9-iowa-whiskey": ("Slipknot No. 9 Iowa Whiskey", [], "Blended Whiskey"),
    "slipknot-no-9-reserve": ("Slipknot No. 9 Reserve", [], "Blended Whiskey"),
    "slipknot-red-cask-no-9": ("Slipknot Red Cask No. 9", [], "Blended Whiskey"),
    "the-quintessential": ("QuintEssential Solera Edition", ["Cedar Ridge QuintEssential"], "American Single Malt Whiskey"),
    "the-quintessential-first-fill-sherry-cask": ("QuintEssential First Fill Sherry Cask", [], "American Single Malt Whiskey"),
    "the-quintessential-single-cask-series-ex-bourbon-cask": ("QuintEssential Single Cask Ex-Bourbon Cask", [], "American Single Malt Whiskey"),
    "the-quintessential-single-cask-series-new-american-oak": ("QuintEssential Single Cask New American Oak", [], "American Single Malt Whiskey"),
    "the-quintessential-single-cask-series-peat-amontillado": ("QuintEssential Single Cask Peated Amontillado", [], "American Single Malt Whiskey"),
    "the-quintessential-single-cask-series-tawny-port": ("QuintEssential Single Cask Tawny Port", [], "American Single Malt Whiskey"),
    "the-quintessential-singlecaskseries-tokaji": ("QuintEssential Single Cask Tokaji", [], "American Single Malt Whiskey"),
    "the-quintessential-singlecask-confused-breakfast-podcast": ("QuintEssential Single Cask Confused Breakfast Podcast", [], "American Single Malt Whiskey"),
    "the-quintessential-special-release": ("QuintEssential Special Release Pete & Sherri 1st Anniversary", [], "American Single Malt Whiskey"),
    "quintessential-special-release": ("QuintEssential Special Release Pete & Sherri 2nd Anniversary", [], "American Single Malt Whiskey"),
    "the-quintessential-special-release-portside": ("QuintEssential Special Release Portside", [], "American Single Malt Whiskey"),
    "the-quintessential-special-release-untitled-cigar-malt": ("QuintEssential Special Release Untitled Cigar Malt", [], "American Single Malt Whiskey"),
    "the-quintessential-special-release-wine-club": ("QuintEssential Special Release Wine Club", [], "American Single Malt Whiskey"),
    "the-quintessential-special-release-numberfive": ("QuintEssential Special Release Number Five", [], "American Single Malt Whiskey"),
}
# Clown's Iowa Shine (slipknot-clowns-iowa-shine) is unaged raw spirit: not listed.
CORE = {"Original 86", "Straight Rye", "Wheat Whiskey", "QuintEssential Solera Edition"}
# The maker's own product name carries the proof where the page prints none.
PROOF_FROM_NAME = {"straight-bourbon-whiskey": 86.0}
RARITY = [
    (r"single barrel collection|nine & three|anniversary|special release|first fill|single cask", "allocated"),
    (r"slipknot|original 86|straight rye|wheat whiskey|solera", "shelf"),
    (r".", "limited"),
]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = re.findall(r"<loc>([^<]+/whiskeys/([^</]+)/)</loc>", fetcher.get(SITEMAP))
    return sorted({u for u, slug in urls if slug in REFILE or slug == "slipknot-clowns-iowa-shine"})


def _clean(page: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _own(text: str) -> str:
    """The product's own copy: after the site menu's last 'Careers', before the bundles/cocktails footer."""
    starts = [m.end() for m in re.finditer(r"Careers\|", text)]
    if not starts:
        return text
    k = starts[-1]
    ends = [i for i in (text.find(m, k) for m in ("Whiskey Bundles", "Leaving a Legacy", "Private Barrel Program|", "Featured Cocktails")) if i > 0]
    return text[k:min(ends)] if ends else text[k:k + 1500]


TASTE_CUE = re.compile(r"\bnotes?\b", re.I)


def _notes(own: str) -> str | None:
    """Sentences of the product copy (the part before the Mashbill block) that name a taste."""
    out = []
    for para in own.split("Mashbill|")[0].split("|"):
        out += [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", para.strip()) if TASTE_CUE.search(s)]
    return " ".join(out)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"Cedar Ridge {expression}"
    own = _own(_clean(page))

    proof = None
    # "112 Proof | 56% ABV", "bottled at 115 proof", "at 94 proof", "Bottled at 100 Proof"
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*Proof\s*\|\s*[\d.]+%\s*ABV", own, re.I)
    if not m:
        # the Act's recital ("a minimum of 4 years at 100 proof") is the law, not this bottle's statement
        stated = re.sub(r"[^.|]*Bottled-in-Bond Act[^|]*", "", own, flags=re.I) if slug == "bottled-in-bond-bourbon" else own
        m = re.search(r"(?:bottled\s+at|complexity\s+at|At)\s+(\d{2,3}(?:\.\d+)?)\s*proof", stated, re.I)
    if m:
        proof = float(m.group(1))
    elif slug == "bottled-in-bond-bourbon":
        proof = 100.0  # bottled in bond is 100 proof by law
    elif slug in PROOF_FROM_NAME:
        proof = PROOF_FROM_NAME[slug]
    if slug == "single-barrel-collection":
        proof = None  # two different barrels, each with its own proof

    years = label = None
    if slug == "bottled-in-bond-rye-whiskey":
        years, label = age("4-years old")
    elif slug == "nine-three-quarters-rye":
        years, label = age("aged at least nine years")
    elif slug == "wheat-whiskey":
        years, label = age("aged two years")

    mm = re.search(r"Mashbill\|(.*?)(?:\|\s*(?:Shop|Buy|Sold|Coming|Restocked|\d{4} Release|\$)|$)", own, re.I)
    mash_raw = None
    if mm:
        parts = re.findall(r"(\d+(?:\.\d+)?)%\s*([^|]+)", mm.group(1))
        mash_raw = ", ".join(f"{pct}% {grain.strip()}" for pct, grain in parts) or None

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and "privatebarrel" in img:  # Port Cask's og:image is the generic private-barrel bottle, not this whiskey
        img = None
    desc = own.split("Mashbill|")[0]
    desc = re.sub(r"Direct shipping[^|]*\|?|Unfortunately we do not ship[^|]*\|?", "", desc)
    desc = re.sub(r"\s*\|\s*", " ", desc).strip() or None

    return BottlingRecord(
        brand_family="Cedar Ridge", expression=expression, name=name,
        source_url=url, proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, description=desc[:600] if desc else None, tasting_notes=_notes(own),
        image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
