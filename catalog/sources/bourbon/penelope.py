"""shop.penelopebourbon.com — Penelope Bourbon's own Shopify store (penelopebourbon.com itself is a
WordPress marketing site whose copy rarely states a number; the store's product pages carry a "Bourbon
Facts" / "Whiskey Facts" spec block instead: one `<li><h4>label</h4><p>value</p></li>` per fact — Type &
Process, Proof, Age (sometimes relabelled "Age/Barrel Char", and on the Toasted series that field holds
the char level, not a year), and Mash Bill. The flagship Barrel Strength page has a content-entry error
(its proof sits in the Type & Process field, not the Proof field), so proof is read from whichever field
states a number. Five ready-to-pour cocktail SKUs on the same store are not whiskey and are skipped.
tasting_notes is the page's own "Tasting Notes" list (Aroma / Body / Finish, as 'Aroma: ... Palate: ... Finish: ...')."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Penelope"
DELAY = 6
SITEMAP = "https://shop.penelopebourbon.com/products.json?limit=250"
IMAGE_PREFIX = "https://shop.penelopebourbon.com/"
CATALOG_FAMILIES = ["Penelope"]
PRODUCER_BY_FAMILY = {}

# handle → (expression, aliases).
REFILE = {
    "kentucky-straight-bourbon": ("Kentucky Straight Bourbon Whiskey", ["Penelope Classic Series"]),
    "straight-rye-whiskey": ("Straight Rye Whiskey", ["Penelope Classic Series Rye"]),
    "penelope-four-grain-straight-bourbon": ("Four Grain", []),
    "wheated": ("Wheated Bourbon", []),
    "architect-series": ("Architect", []),
    "barrel-strength": ("Barrel Strength", []),
    "toasted-series": ("Toasted Series", []),
    "rio": ("Rio", []),
    "riviera": ("Riviera", []),
    "rose-cask-finish": ("Rosé Cask Finish", []),
    "havana": ("Havana", []),
    "valencia": ("Valencia", []),
    "tokaji-cask-finish": ("Tokaji Cask Finish Rye", ["Tokaji Cask Finish"]),
    "cigar-sessions": ("Cigar Sessions", ["Cigar Sessions Chapter 01"]),
    "cigar-sessions-chapter-02": ("Cigar Sessions Chapter 02", []),
    "barrel-strength-7-year": ("Barrel Strength 7 Year", []),
    "american-light-whiskey-18-year": ("18 Year American Light", ["American Light Whiskey"]),
    "serena-lily": ("Serena & Lily", []),
    "omega": ("Omega", []),
    "penelope-toasted-rye": ("Toasted Rye", []),
}
NOT_CORE = re.compile(r"tokaji|cigar sessions|barrel strength 7|18 year|serena|omega|toasted rye|rio|riviera|ros|havana|valencia|architect", re.I)
RARITY = [(r"tokaji|18 year|serena|omega|barrel strength 7", "unicorn"), (r"cigar sessions|toasted rye", "lottery"),
          (r"rio|riviera|ros|havana|valencia|architect|toasted series", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
PRODUCT_URL = "https://shop.penelopebourbon.com/products/{}"


def list_urls(fetcher) -> list[str]:
    data = json.loads(fetcher.get(SITEMAP))
    handles = {p["handle"] for p in data["products"]} & set(REFILE)
    return sorted(PRODUCT_URL.format(h) for h in handles)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<br\s*/?>", ", ", fragment))
    t = re.sub(r"<[^>]+>", " ", t).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip(" ,")
    return t or None


def _tasting(page: str) -> str | None:
    """The page's own `<h3>Tasting Notes</h3><ul><li><h4>Aroma|Body|Finish</h4><p>..</p>` list. Other <h4> rows
    ("Forward Notes" repeats the marketing blurb) are skipped."""
    m = re.search(r"<h3>\s*Tasting notes\s*</h3>(.*?)</ul>", page, re.S | re.I)
    parts = []
    for label, body in re.findall(r"<h4>(.*?)</h4>\s*<p>(.*?)</p>", m.group(1), re.S) if m else []:
        key = {"aroma": "Aroma", "body": "Palate", "body notes": "Palate", "finish": "Finish"}.get((_text(label) or "").lower())
        body = _text(body)
        if key and body:
            parts.append(f"{key}: {body}" + ("" if body.endswith((".", "!")) else "."))
    return " ".join(parts)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases = REFILE[handle]
    name = f"Penelope {expression}"
    m = re.search(r"(?:Bourbon|Whiskey) Facts\s*</h3>(.*?)</ul>", page, re.S)
    block = m.group(1) if m else ""
    facts = {}
    for li in re.findall(r"<li>(.*?)</li>", block, re.S):
        lm = re.search(r"<h4>(.*?)</h4>\s*<p>(.*?)</p>", li, re.S)
        if lm:
            facts[_text(lm.group(1)).lower()] = _text(lm.group(2))
    type_field = next((v for k, v in facts.items() if "type" in k), "")
    proof_field = facts.get("proof", "")
    pf = None
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:proof)?", proof_field, re.I) if proof_field and re.search(r"\d", proof_field) else None
    if m:
        pf = float(m.group(1))
    else:  # the Barrel Strength page's own content-entry error: the number sits in Type & Process instead
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", type_field, re.I)
        pf = float(m.group(1)) if m else None
    age_field = next((v for k, v in facts.items() if k.startswith("age")), "") or ""
    years, label = age(age_field)
    mash_raw = next((v for k, v in facts.items() if "mash" in k), None)
    # A genuine blend of whiskey types ("Straight Bourbon, 100% American Single Malt, and American Light
    # Whiskey"), not a finish description that happens to contain "and" ("honey barrels and then Amburana barrels").
    type_kinds = len(set(re.findall(r"straight bourbon|straight rye|single malt|light whiskey", type_field, re.I)))
    blend = type_kinds > 1
    rye = bool(re.search(r"\brye\b", type_field, re.I)) and not re.search(r"bourbon", type_field, re.I)
    light = bool(re.search(r"light whiskey", type_field, re.I)) and not rye and "bourbon" not in type_field.lower()
    if blend:
        class_raw = "Blended American Whiskey"
    elif rye:
        class_raw = "Straight Rye Whiskey" if "2 grain" not in type_field.lower() else "Straight Rye Whiskey"
    elif light:
        class_raw = "American Light Whiskey"
    else:
        class_raw = "Straight Bourbon Whiskey"
    desc = type_field if len(type_field) > 20 else None
    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]
    return BottlingRecord(
        brand_family="Penelope", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style=None, description=desc, tasting_notes=_tasting(page),
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
