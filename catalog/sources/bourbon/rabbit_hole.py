"""rabbitholedistillery.com (Rabbit Hole Distilling, Louisville — Pernod Ricard-owned). The marketing
site *is* the Shopify store (no separate shop subdomain; shop.rabbitholedistillery.com redirects back
here), so every page is fetched as its `.json` product endpoint rather than scraped HTML — `body_html`
carries the same accordion copy the rendered page shows, including a formal "SPECS PROOF N (N% ABV)
TYPE ... SIZE 750ml" block on the four core expressions (Cavehill, Heigold, Boxergrail, Dareringer).
Founder's Collection and Distillery Series releases (Adourra, Amburana, Mizunara, Follesrunn,
Heretofore, Rabelo, Seasong, Starlino, Velarde) have no SPECS block, just prose that states proof and
age inconsistently or not at all — Amburana and Mizunara give an age but no proof number (both are
cask strength, no fixed figure); Velarde's two-barrel blend ("Barrel 1: 4+ Yrs / Barrel 2: 4 Mos")
has no single age to state and is left unread rather than guessed. Single-barrel and numbered-batch
drops (Cavehill Queen, Heigold Alice, WBSC Sonia, ...) and the Boxergrail/Revera Founder's/Distillery
entries with `body_html: null` state nothing at all and are not crawled — the store's own `product_type`
field lumps Bespoke Gin and Liddel Vodka in with "Whiskey", so scope is the REFILE table, not the type.

`tasting_notes` is the product's own tasting text, in the first of three shapes the body has: a "TASTING NOTES" block (the four
core pages quote Whiskey Advocate there; Amburana, Mizunara and Adourra have their own), else labelled Aroma / Palate / Finish
(or Nose / Taste / Finish) lines, else the prose sentences that name aromas and flavors. The DESCRIPTION, STORY, food pairings,
shipping and "Distillery Series" boilerplate that sit beside them are never read."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Rabbit Hole"
DELAY = 6
SITEMAP = "https://www.rabbitholedistillery.com/collections/all/products.json?limit=250"
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["Rabbit Hole"]
PRODUCER_BY_FAMILY = {}
PRODUCT_URL = "https://www.rabbitholedistillery.com/products/{}.json"

# handle → (expression, aliases).
REFILE = {
    "cavehill-kentucky-straight-bourbon-whiskey": ("Cavehill", []),
    "heigold-kentucky-straight-bourbon-whiskey": ("Heigold", []),
    "boxergrail-kentucky-straight-rye-whiskey": ("Boxergrail", ["Rabbit Hole Boxergrail Rye"]),
    "dareringer-straight-bourbon-whiskey-finished-in-px-sherry-casks": ("Dareringer", []),
    "adourra-founders": ("Adourra", []),
    "amburana-1-1-750-retail-only": ("Amburana", []),
    "rabbit-hole-mizunara-cask-strength-founders-collection-kentucky-straight-bourbon-whiskey": ("Mizunara", []),
    "follesrunn-1-375": ("Follesrunn", []),
    "heretofore-1-375-french-oak": ("Heretofore", []),
    "rabelo-1-375": ("Rabelo", []),
    "seasong-1-375": ("Seasong", []),
    "starlino-single-bottle-375ml": ("Starlino", []),
    "velrade-375ml": ("Velarde", []),
    "10-year-anniversary-bottle": ("Tenniel", []),
}
CORE = {"Cavehill", "Heigold", "Boxergrail", "Dareringer"}
RARITY = [(r"adourra|amburana|mizunara|tenniel", "unicorn"), (r"follesrunn|heretofore|rabelo|seasong|starlino|velarde", "lottery"),
          (r".", "shelf")]
MASH_BILLS = {}
CLASS_WORDS = re.compile(r"\b(Kentucky\s+Straight\s+Rye\s+Whiskey|Straight\s+Rye\s+Whiskey|Rye\s+Whiskey|"
                          r"Kentucky\s+Straight\s+Bourbon\s+Whiskey|Straight\s+Bourbon\s+Whiskey|Straight\s+Bourbon|Bourbon)\b", re.I)


def list_urls(fetcher) -> list[str]:
    handles: set[str] = set()
    page = 1
    while True:
        raw = fetcher.get(f"https://www.rabbitholedistillery.com/collections/all/products.json?limit=250&page={page}")
        data = json.loads(raw)
        products = data.get("products", [])
        if not products:
            break
        handles.update(p["handle"] for p in products)
        page += 1
    return sorted(PRODUCT_URL.format(h) for h in handles if h in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(body_html: str | None) -> str:
    body = re.sub(r"<style[^>]*>.*?</style>", "", body_html or "", flags=re.S)
    body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace(" ", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _join(tokens: list[str]) -> str:
    """Space-join `|` fragments, gluing the one-letter drop-cap splits ("T| obacco") back together."""
    out = ""
    for t in (x.strip() for x in tokens):
        if not t or t == ":":
            continue
        glue = re.search(r"(?:^|\s)[A-HJ-Z]$", out) and t[0].islower()
        out += t if glue else (" " + t if out else t)
    return out


LABELS = {"aroma": "Aroma", "aromas": "Aroma", "nose": "Nose", "palate": "Palate", "taste": "Taste", "finish": "Finish"}
SENSORY = re.compile(r"\b(?:aromas? of|scents? of|nose of|each sip|palate of|fades? into|finish(?:es)? (?:of|with|into))\b", re.I)


def _notes(own: str) -> str | None:
    """A TASTING NOTES block, else the Aroma / Palate / Finish lines, else the sentences that name aromas and flavors."""
    m = re.search(r"\|\s*TASTING NOTES:?\s*\|(.*?)(?=\|\s*(?:STORY|DESCRIPTION|Numbered Limited Edition)\b|$)", own, re.I)
    if m:
        text = _join(m.group(1).split("|"))
        if re.search(r"\s*-\s*[\"“]?Whiskey Advocate[\"”]?\s*$", text):  # a critic's quote, not the maker's words: stored under the maker's name it would misattribute
            return None
        return text[:900] or None
    parts: dict[str, list[str]] = {}
    key = None
    for raw in own.split("|"):
        t = raw.strip()
        label = LABELS.get(t.rstrip(":").strip().lower())
        if label and (t.endswith(":") or t.isupper() or t[:1].isupper()):
            key = label
            parts.setdefault(key, [])
        elif key and re.match(r"(?:DETAILS|Details|Mash Bill|AVAILABLE|Proof)", t):
            break
        elif key and t:
            parts[key].append(t)
    out = []
    for k, toks in parts.items():
        v = _join(toks).strip().rstrip(" .,")
        if v:
            out.append(f"{k}: {v}.")
    if out:
        return " ".join(out)[:900]
    text = _join(own.split("|"))
    sents = [x for x in re.split(r"(?<=[.!?])\s+", text) if SENSORY.search(x)]
    return " ".join(sents)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1].removesuffix(".json")
    if handle not in REFILE:
        return None
    expression, aliases = REFILE[handle]
    name = f"Rabbit Hole {expression}"
    data = json.loads(page)["product"]
    own = _flatten(data.get("body_html"))

    sm = re.search(r"SPECS\|?\s*PROOF\s*\|?\s*(\d{2,3}(?:\.\d+)?)", own)
    pm = sm or re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*proof\b", own, re.I)
    proof = float(pm.group(1)) if pm else None

    years, label = age(own)

    tm = re.search(r"TYPE\s*\|?\s*([^|]+?)\s*\|", own)
    type_field = tm.group(1).strip() if tm else ""
    cm = CLASS_WORDS.search(type_field) or CLASS_WORDS.search(own)
    class_raw = None
    if cm:
        matched = cm.group(1)
        rye = bool(re.search(r"rye", matched, re.I))
        class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"
    if class_raw and re.search(r"cask strength|barrel[- ]proof", own, re.I):
        class_raw += " Cask Strength"

    four_grain = bool(re.search(r"four[- ]grain", own, re.I))
    high_rye = bool(re.search(r"high[- ]rye", own, re.I))
    mash_style = "four_grain" if four_grain else "high_rye" if high_rye and class_raw and "Rye" not in class_raw else None
    mash_raw = type_field or None

    img = None
    images = data.get("images") or []
    if images:
        img = images[0].get("src")
    elif data.get("image"):
        img = data["image"].get("src")

    desc = _text(own.split("| TASTING NOTES", 1)[0][:600]) if "TASTING NOTES" in own else _text(own[:600])

    return BottlingRecord(
        brand_family="Rabbit Hole", expression=expression, name=name, source_url=f"https://www.rabbitholedistillery.com/products/{handle}",
        proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=mash_style,
        description=desc, tasting_notes=_notes(own), image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
