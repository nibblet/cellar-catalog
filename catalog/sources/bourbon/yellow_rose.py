"""yellowrosedistilling.com (Yellow Rose Distilling, Houston — "Houston's first legal whiskey distillery").
WordPress + Elementor; the whole lineup is ONE page, /products/, one `<h2>` heading per bottling with its
copy and a strength line under it. (The "Shop" button goes to shopyellowrosedistilling.com, a Shopify
store whose product pages carry only a one-sentence blurb and a price — no proof, no age — so it adds
nothing but the class words the REFILE table below cites: "Outlaw Bourbon Whiskey", "Premium American
Whiskey", "Harris County Straight Bourbon", "Travis County Blended Bourbon Whiskey", "Kerr County Limited
Edition Blended Bourbon", "Jim Marshall Collection Limited Edition Straight Bourbon".) The old
/straight-rye-whiskey, /double-barrel-bourbon … pages in the 2014 Google sitemap are gone; the live
sitemap lists only /products/ and /cocktails/.

Strength is printed as "46% ABV" (the four Originals and the three 2025 releases); the Jim Marshall
release prints "116 Proof | 58% ABV". Proof is read from an explicit "N Proof" first, else it is ABV x 2
— the same figure by definition, and the label's ABV is the legal statement. No bottle's age is stated
anywhere on the site (Outlaw says only "aged in small American oak barrels", with a 15% angel share), so
age stays unread, and the seed row's 1-year age is left alone. Mash: Outlaw's prose says "100% Texas
yellow corn" and Rye "95% rye"; the Jim Marshall and Kerr County tag lines print "100% Texas Yellow
Corn". Travis County's copy calls it "a proprietary blend of 100% Texas corn whiskey and a traditional
bourbon mash bill", so the corn tag describes one component and is NOT read as a recipe. Harris County
names its grains (yellow corn, Elbon rye, San Jacinto malted barley) with no percentages — no mash bill."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Yellow Rose"
DELAY = 6
PAGE = "https://yellowrosedistilling.com/products/"
SITEMAP = "https://yellowrosedistilling.com/sitemap_index.xml"  # unused (one page); bourbon_write.py reads the host from it
IMAGE_PREFIX = "https://yellowrosedistilling.com/"
CATALOG_FAMILIES = ["Yellow Rose"]
PRODUCER_BY_FAMILY = {}

# heading text (upper-cased) → (expression, aliases, class statement, image file-name keyword, mash_raw or None).
REFILE = {
    "OUTLAW BOURBON": ("Outlaw Bourbon", [], "Bourbon Whiskey", "Outlaw-Bourbon", "100% Corn"),
    "PREMIUM AMERICAN": ("Premium American", ["Yellow Rose Premium American Whiskey"], "American Whiskey", "Premium-American", None),
    "RYE WHISKEY": ("Rye Whiskey", ["Yellow Rose Rye"], "Rye Whiskey", "Rye_HR", "95% Rye"),
    "HARRIS COUNTY": ("Harris County", ["Yellow Rose Harris County Straight Bourbon"], "Straight Bourbon Whiskey", "Harris-County", None),
    "JIM MARSHALL COLLECTION, LIMITED RELEASE": ("Jim Marshall Collection", ["Yellow Rose Jim Marshall Collection Limited Edition Straight Bourbon"], "Straight Bourbon Whiskey", "Jim-Marshall", "100% Corn"),
    "TRAVIS COUNTY BLENDED BOURBON WHISKEY": ("Travis County", ["Yellow Rose Travis County Blended Bourbon Whiskey"], "Blended Bourbon Whiskey", "Travis-County", None),
    "KERR COUNTY LIMITED EDITION": ("Kerr County", ["Yellow Rose Kerr County Limited Edition Blended Bourbon"], "Blended Bourbon Whiskey", "Kerr-County", "100% Corn"),
}
# "The Originals" are the four bottles the page calls the core of the house; the rest are 2025 "New Releases".
CORE = {"Outlaw Bourbon", "Premium American", "Rye Whiskey", "Harris County"}
RARITY = [(r"jim marshall|kerr county", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [PAGE]


def _flat(fragment: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t).strip(" |")


def parse(url: str, page: str) -> list[BottlingRecord]:
    heads = [(m.start(), m.end(), _flat(m.group(1)).upper()) for m in re.finditer(r"<h[1-3][^>]*>(.*?)</h[1-3]>", page, re.S)]
    heads = [h for h in heads if h[2] in REFILE]
    images = re.findall(r'src="(https://yellowrosedistilling\.com/wp-content/uploads/[^"]+\.(?:png|jpe?g))"', page)
    out = []
    for i, (_, end, title) in enumerate(heads):
        stop = heads[i + 1][0] if i + 1 < len(heads) else len(page)
        seg = page[end:stop]
        if i + 1 == len(heads):  # the last block runs into the footer's newsletter signup
            seg = seg.split("Never Miss a New Release", 1)[0]
        expression, aliases, cls, imgkey, mash = REFILE[title]
        own = _flat(seg)

        pm = re.search(r"\b(\d{2,3}(?:\.\d)?)\s*Proof\b", own, re.I)
        am = re.search(r"\b(\d{2}(?:\.\d)?)\s*%\s*ABV\b", own, re.I)
        proof = float(pm.group(1)) if pm else (round(float(am.group(1)) * 2, 1) if am else None)

        # Strip the tasting-note blocks (NOSE / PALATE / FINISH) from the description.
        desc = own.split("NOSE:", 1)[0].strip(" |")
        desc = re.sub(r"\s*\|\s*", " ", desc).strip() or None
        hits = [u for u in images if imgkey.lower() in u.lower()]  # the 2025 releases only ship a sized file ("...-772x1200.png")
        img = next((u for u in hits if not re.search(r"-\d+x\d+\.\w+$", u)), hits[0] if hits else None)

        out.append(BottlingRecord(
            brand_family="Yellow Rose", expression=expression, name=f"Yellow Rose {expression}",
            source_url=PAGE, proof=proof, age_years=None, age_label=None, class_raw=cls, mash_raw=mash,
            description=desc, image_url=img, aliases=sorted(set(aliases) - {f"Yellow Rose {expression}"}),
            is_core_range=expression in CORE,
        ))
    return out
