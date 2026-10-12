"""starlightdistillery.com (Huber's Starlight Distillery, Starlight, Indiana — a farm distillery that
also makes brandy, gin, rum and vodka; those live under /brandies/, /gins/, /rums/, /vodkas/ and are
never crawled). WordPress with a custom `sd_product` post type; `sd_product-sitemap.xml` is the only
reliable product index — the nav's category pages (/bourbons/, /finishings/, ...) are Beaver Builder
loops with no plain `<a>` tags a generic crawler can enumerate. Every page ends in an "Explore More
Spirits" carousel of *other* products, each with its own "N Proof" span (`sd_related_products_item_proof`
or `sd_product_card_proof`) — the page is always truncated at that marker before reading anything, or a
sibling's proof reads as this bottling's own. A finishing's name alone rarely says what it is ("Mizunara
Reserve", "Cigar Batch" name nothing) — the class is read from the body's own opening sentence
("Starlight Cigar Batch Bourbon is..."), which also catches /finishings/orchard-blossom being a Rye
despite living in the same URL bucket as five Bourbon finishes. "Aged for a minimum of 4 years" is
boilerplate repeated on unrelated products (Bottled-in-Bond and the non-bonded Carl T. both use it
verbatim) describing the distillery's usual floor, not a stated fact about that SKU — stripped before
reading age; a genuine age ("aged slowly for a full decade" on the 10 Year Reserve) is unaffected. No
page anywhere states mash bill percentages — only qualitative "3-grain"/"4-grain"/"sweet mash
fermentation" — so mash_style stays unset throughout. `tasting_notes` is the page's own Tasting Notes block (Nose /
Taste / Finish, not Appearance and not the placeholder "varies by release" lines), cut before the cocktail recipe."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Starlight"
DELAY = 6
SITEMAP = "https://starlightdistillery.com/sd_product-sitemap.xml"
IMAGE_PREFIX = "https://starlightdistillery.com/"
CATALOG_FAMILIES = ["Starlight"]
PRODUCER_BY_FAMILY = {}

# path (under the domain, no leading/trailing slash) → (expression, aliases).
REFILE = {
    "bourbons/carl-t-bourbon-whiskey": ("Carl T.", []),
    "bourbons/bottled-in-bond-bourbon-whiskey": ("Bottled-in-Bond", []),
    "bourbons/10-year-reserve-bourbon-whiskey": ("10 Year Reserve", []),
    "bourbons/single-barrel-bourbon-whiskey": ("Single Barrel", []),
    "bourbons/toasted-barrel-bourbon": ("Toasted Barrel", []),
    "bourbons/double-oaked-bourbon-whiskey": ("Double Oaked", []),
    "ryes/old-rickhouse-rye-whiskey": ("Old Rickhouse Rye", []),
    "ryes/bottled-in-bond-rye-whiskey": ("Bottled-in-Bond Rye", []),
    "ryes/double-oak-old-rickhouse-rye-whiskey": ("Double Oak Old Rickhouse Rye", []),
    "ryes/single-barrel-old-rickhouse-rye-whiskey": ("Single Barrel Rye", []),
    "finishings/mizunara-reserve": ("Mizunara Reserve", []),
    "finishings/10-year-mizunara-reserve": ("10 Year Mizunara Reserve", []),
    "finishings/cigar-batch": ("Cigar Batch", []),
    "finishings/honey-reserve": ("Honey Reserve", []),
    "finishings/sakura-reserve": ("Sakura Reserve", []),
    "finishings/single-barrel-vdn-finished-bourbon-whiskey": ("Single Barrel VDN Finished", []),
    "finishings/orchard-blossom": ("Orchard Blossom", []),
    "other-whiskeys/single-barrel-light-whiskey": ("Single Barrel Light Whiskey", []),
    "single-malt/indiana-uplands-american-single-malt-whiskey": ("Indiana Uplands American Single Malt", []),
    "blackberry-whiskey": ("Blackberry Whiskey", []),
    "flavored/peach-whiskey": ("Peach Whiskey", []),
}
NOT_CORE = re.compile(
    r"mizunara|cigar batch|honey reserve|sakura|vdn finished|orchard blossom|"
    r"single barrel light|indiana uplands|blackberry whiskey|peach whiskey", re.I,
)
RARITY = [(r"indiana uplands", "unicorn"), (r"mizunara|sakura|vdn finished|orchard blossom", "lottery"),
          (r"cigar batch|honey reserve|single barrel light", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
CARD_PROOF = re.compile(r'<span class="sd_related_products_item_proof">.*?</span>', re.S)
CARD_PROOF2 = re.compile(r'<span class="sd_product_card_proof">.*?</span>', re.S)
CLASS_WORDS = re.compile(
    r"\b(Rye\s+Whiskey|Wheat\s+Whiskey|American\s+Single\s+Malt\s+Whiskey|Single\s+Malt\s+Whiskey|"
    r"Light\s+Whiskey|Bourbon(?:\s+Whiskey)?)\b", re.I,
)


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://starlightdistillery.com/{p}/" for p in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _notes(own: str) -> str | None:
    """The Tasting Notes block is `Label| text|` pairs; the cocktail recipe that follows is never read."""
    i = own.find("Tasting Notes")
    if i < 0:
        return None
    toks = [t.strip() for t in own[i + len("Tasting Notes"):].split("|") if t.strip()]
    got = {}
    for k in range(len(toks) - 1):
        if toks[k] in ("Nose", "Taste", "Finish") and toks[k] not in got:
            if not re.match(r"(varies|because each barrel|tasting notes vary)", toks[k + 1], re.I):
                got[toks[k]] = toks[k + 1].rstrip(". ")
        elif toks[k] in ("Featured Cocktail", "Sorry, we couldn't find any posts. Please try a different search."):
            break
    return " ".join(f"{label}: {got[label]}." for label in ("Nose", "Taste", "Finish") if label in got)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    path = url.replace("https://starlightdistillery.com/", "").strip("/")
    if path not in REFILE:
        return None
    expression, aliases = REFILE[path]
    name = f"Starlight {expression}"
    page = CARD_PROOF.sub("", page)
    page = CARD_PROOF2.sub("", page)
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = flat.split("Explore More Spirits", 1)[0]

    pm = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*Proof\b", own, re.I)
    proof = float(pm.group(1)) if pm else None

    age_text = re.sub(r"(?:a\s+minimum\s+of|at\s+least)\s+\d{1,2}\s+years?", "", own, flags=re.I)
    years, label = age(age_text)

    cm = CLASS_WORDS.search(own)
    class_raw = f"Straight {cm.group(1)}" if cm else None
    if class_raw and not re.search(r"whiskey", class_raw, re.I):
        class_raw += " Whiskey"

    mm = re.search(r"[\w' -]*?mash bills?", own, re.I)
    mash_raw = mm.group(0).strip() if mm else None

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]

    return BottlingRecord(
        brand_family="Starlight", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=None,
        description=_text(own.split("Tasting Notes", 1)[0][-700:]), tasting_notes=_notes(own), image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
