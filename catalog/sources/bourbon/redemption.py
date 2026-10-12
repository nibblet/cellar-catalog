"""redemptionwhiskey.com (Redemption Whiskey, Deutsch Family Wine & Spirits; WordPress, one static page per
whiskey under /whiskeys/, listed in ww_product-sitemap.xml and on the /whiskeys/ index). The site shows an
age-gate overlay, but the overlay is only markup in the same HTML the server returns for every client —
nothing is bypassed; no cookie or click is simulated. Every product page carries the same block:
"Strength | 46% ABV (92 Proof)" (proof is read only from that line — the rye and bourbon pages also carry a
boilerplate "Moving our bourbon to 92 proof ..." paragraph that is a sibling's story, not their own), a
hero title in the <h1> (which is where an age such as "9 Year old" or "18 Year Old Bourbon" is printed), and a
mash-bill *pie-chart image* with no text. The mash bill is therefore known only from the prose when the
copy states a grain percentage ("21% rye backbone", "36% rye", "45% winter wheat", "rye content of 95%").
That is enough for mash_style but not a full recipe, so no mash_bill is stored (mash_raw stays empty).
Only the bonded single barrel states an age in its body ("aged for at least six years in a federally
bonded warehouse"); the flagship Bourbon, Rye, High Rye and Wheated pages state none, so the seed's ages for
those rows are left alone (never NAS from silence). Cognac Cask Finish states "limited-edition".
The "Higher Marques" shelf (Bonded Single Barrel, Cognac Cask Finish, Wheated Bourbon) and "Classics" are the
standing lineup; "Limited Releases" and "The Ancients" are releases and are not core range. tasting_notes is the page's own
flavor tile ("Notes | Caramel, Baking Spices, Anise") plus its "Tasting Notes" block (Sniff / Sip / Savor = aroma, taste,
aftertaste); the hero blurb, the Master Blender quote and the 92-proof boilerplate under it are not read."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, mash_style, spirit_type

PRODUCER = "Redemption"
DELAY = 6
BASE = "https://www.redemptionwhiskey.com/whiskeys/"
SITEMAP = "https://www.redemptionwhiskey.com/ww_product-sitemap.xml"
IMAGE_PREFIX = "https://www.redemptionwhiskey.com/"
CATALOG_FAMILIES = ["Redemption"]
PRODUCER_BY_FAMILY = {}

# slug -> (expression, aliases, class statement printed in the hero title, grain text the copy states,
#          finish as the page states it). expression None is the plain "Redemption" flagship (the page is
#          titled "Bourbon"). The class is the title's own word — "Bourbon" / "Rye" — never inferred from the name.
REFILE = {
    "bourbon-whiskey": (None, ["Redemption Bourbon"], "Bourbon Whiskey", "21% rye", None),
    "high-rye-bourbon": ("High Rye", ["Redemption High Rye Bourbon"], "Bourbon Whiskey", "36% rye", None),
    "rye": ("Rye", ["Redemption Rye Whiskey"], "Rye Whiskey", "95% rye", None),
    "wheated-bourbon": ("Wheated Bourbon", [], "Bourbon Whiskey", "45% winter wheat", None),
    "bonded-single-barrel-bourbon": ("Bonded Single Barrel", ["Redemption Bonded Single Barrel Bourbon"], "Bourbon Whiskey", None, None),
    "cognac-cask-finish": ("Cognac Cask Finish", [], "Bourbon Whiskey", "high rye", "Cognac Casks"),
    "9-years-aged-barrel-proof-bourbon": ("9 Year Barrel Proof", ["Redemption 9 Year Barrel Proof Bourbon"], "Bourbon Whiskey", None, None),
    "10-year-barrel-proof-high-rye-bourbon": ("10 Year Barrel Proof High Rye", ["Redemption 10 Year Barrel Proof High Rye Bourbon"], "Bourbon Whiskey", None, None),
    "10-year-barrel-proof-rye": ("10 Year Barrel Proof Rye", [], "Rye Whiskey", "95% rye", None),
    "18-year-old-bourbon": ("The Ancients 18 Year Bourbon", ["Redemption 18 Year Bourbon"], "Bourbon Whiskey", None, None),
    "18-year-old-rye": ("The Ancients 18 Year Rye", ["Redemption 18 Year Rye"], "Rye Whiskey", None, None),
    "36-year-old-bourbon": ("The Ancients 36 Year Bourbon", ["Redemption 36 Year Bourbon"], "Bourbon Whiskey", None, None),
}
CORE = {None, "High Rye", "Rye", "Wheated Bourbon", "Bonded Single Barrel"}
RARITY = [(r"ancients", "unicorn"), (r"barrel proof|cognac", "allocated"), (r"bonded single barrel", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE] + [f"{BASE}{slug}/" for slug in REFILE]


def _plain(fragment: str, sep: str = " ") -> str:
    t = html.unescape(re.sub(r"<[^>]+>", sep, fragment)).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE or "/whiskeys/" not in url:
        return None
    canon = re.search(r'rel="canonical" href="([^"]+)"', page)
    if canon and canon.group(1).rstrip("/").split("/")[-1] != slug:
        return None  # redirected somewhere that is not this product's page
    expression, aliases, class_raw, grain, finish_ = REFILE[slug]
    name = f"Redemption {expression}" if expression else "Redemption"

    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", page, flags=re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = _plain(h1.group(1)) if h1 else ""
    # The hero: title, tagline and the maker's paragraph — up to the first "N Proof" tile. Age is read here only.
    hero = _plain(body[h1.end():].split("Proof", 1)[0]) if h1 else ""
    own = _plain(body, "|")

    pm = re.search(r"Strength[\s|]*[\d.]+\s*%[\s|]*ABV[\s|]*\(\s*(\d{2,3}(?:\.\d+)?)\s*Proof\s*\)", own, re.I)
    proof = float(pm.group(1)) if pm else None

    # "Aged for at least six years" is the bonded page's own sentence; the titles print "9 Year old" etc.
    years, label = age(f"{title} {hero}")

    # The "Details" tile lists three flavors; the Tasting Notes block has Sniff / Sip / Savor lines. `own` is a run of
    # text cells split by "|"; each label is followed by its text as the next non-empty cell.
    cells = [c.strip() for c in own.split("|") if c.strip()]

    def after(label: str, start: int = 0) -> tuple[str | None, int]:
        i = next((k for k in range(start, len(cells) - 1) if cells[k] == label), None)
        return (cells[i + 1], i) if i is not None else (None, start)

    pieces = [("Notes", after("Notes")[0])]  # "Tasting Notes" is a different cell, so it cannot match here
    _, at = after("Tasting Notes")
    if at:
        pieces += [(label, after(key, at)[0]) for label, key in (("Aroma", "Sniff"), ("Taste", "Sip"), ("Aftertaste", "Savor"))]
    notes = " ".join(f"{k}: {v}" for k, v in pieces if v) or None
    notes = notes[:900].rsplit(" ", 1)[0] if notes and len(notes) > 900 else notes
    img = re.search(r'property="og:image" content="([^"]+)"', page)
    st = spirit_type(class_raw, name)
    style = mash_style(grain, st, name) if grain else (mash_style(None, st, name) if st == "rye" else None)

    return BottlingRecord(
        brand_family="Redemption", expression=expression, name=name, source_url=f"{BASE}{slug}/",
        proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_style=style,
        description=hero.split("Find Near You", 1)[-1].strip() or None, tasting_notes=notes,
        image_url=html.unescape(img.group(1)).split("?")[0] if img else None, finish=finish_,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
