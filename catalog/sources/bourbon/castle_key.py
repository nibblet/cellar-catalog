"""castleandkey.com (Castle & Key Distillery, Frankfort — Shopify). The `.json` product API's `body_html`
carries the marketing description and, usefully, the "Aged for N years" statement, but not proof or
mash bill — those live only in the rendered page's theme-built "Tasting Notes" accordion (Proof / Alc-Vol
/ Mashbill), so pages are crawled as rendered HTML, not the JSON endpoint. The mash bill is printed in
abbreviated codes with no on-site legend (`73% WC, 10% R, 17% MB` on the flagship, `73% WC, 10% W, 17% MB`
on the wheated line, `17% YC, 63% R, 20% MB` on the rye) — WC/YC both read as corn, R rye, W wheat, MB
malted barley by the standard convention, expanded before handing to `normalize.mash_style()` since it
only recognizes spelled-out grain words. A release's own title says its class for the core four and named
Experimental Series entries ("Restoration Rye Whiskey", "Vino De Naranja (Restoration Rye)"), but two
Experimental Series releases don't ("Hungarian Tokaji Casks" names neither): those instead open their
description with "Our Rye is..." or "Our Wheated Bourbon is...", read as the self-description rather than
guessed from the name. A URL slug can be a stale leftover of an earlier vintage's own age (the wheated
line's handle, `small-batch-7-year-wheated-bourbon`, is now a 5-year whiskey per its own body copy) —
the body text is read, never the slug.

`tasting_notes` is the accordion's "Flavor Profile & Tasting Notes" panel: two unlabelled flavor lists (nose, palate) and a
Finish line, read up to the "Featured Recipe" block (the cocktail and the "Discover Our Spirits" carousel of sibling bottles
come after it, and the marketing copy above is not read)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Castle & Key"
DELAY = 6
SITEMAP = "https://castleandkey.com/sitemap.xml"
IMAGE_PREFIX = "https://castleandkey.com/"
CATALOG_FAMILIES = ["Castle & Key"]
PRODUCER_BY_FAMILY = {}

# handle → (expression, aliases).
REFILE = {
    "small-batch-bourbon": ("Small Batch", []),
    "small-batch-7-year-wheated-bourbon": ("Small Batch Wheated", []),
    "wheated-cask-strength": ("Cask Strength Wheated", []),
    "2025-restoration-rye-whiskey": ("Restoration Rye", ["Castle & Key Restoration", "Castle & Key Restoration Rye", "Restoration"]),
    "castle-key-experimental-series-vino-de-naranja-rye": ("Vino De Naranja", []),
    "castle-key-experimental-series-hungarian-tokaji-casks": ("Hungarian Tokaji Casks", []),
}
CORE = {"Small Batch", "Small Batch Wheated", "Cask Strength Wheated", "Restoration Rye"}
RARITY = [(r"vino de naranja|tokaji", "lottery"), (r"cask strength", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
MASH_EXPAND = {"WC": "Corn", "YC": "Corn", "R": "Rye", "W": "Wheat", "MB": "Malted Barley"}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://castleandkey.com/products/{h}" for h in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _expand_mash(raw: str) -> str:
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*%\s*([A-Za-z]+)", raw)
    return ", ".join(f"{pct}% {MASH_EXPAND.get(code.upper(), code)}" for pct, code in parts) or raw


def _tasting(own: str) -> str | None:
    segs = [x.strip() for x in own.split("|") if x.strip()]
    start = next((i for i, x in enumerate(segs) if x == "Flavor Profile & Tasting Notes"), None)
    if start is None:
        return None
    body = []
    for x in segs[start + 1:]:
        if x in ("Featured Recipe", "Discover Our Spirits", "View Full Recipe"):
            break
        body.append(x)
    if "Finish" in body:
        k = body.index("Finish")
        head, tail = body[:k], body[k + 1:]
    else:
        head, tail = body, []
    text = ""
    for x in (y.strip(". ") for y in head):  # the theme breaks a line mid-list ("Red Apple, | Honeysuckle"): rejoin after a comma, else start a new list
        text = x if not text else f"{text} {x}" if text.endswith(",") else f"{text}. {x}"
    if tail:
        text += (". " if text else "") + "Finish: " + " ".join(tail).strip(". ")
    return (text + ".")[:900] if text else None


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases = REFILE[handle]
    name = f"Castle & Key {expression}"
    own = _flatten(page)

    pm = re.search(r"Tasting Notes\|\s*Proof\|\s*(\d{2,3}(?:\.\d+)?)", own)
    proof = float(pm.group(1)) if pm else None

    years, label = age(own)

    mm = re.search(r"Mashbill\|\s*([^|]+)\|", own)
    mash_raw = _expand_mash(mm.group(1)) if mm else None

    cm = re.search(r"\bOur (Rye|Wheated Bourbon|Bourbon) is\b", own)
    if cm:
        base = cm.group(1)
    elif "rye" in name.lower():
        base = "Rye"
    else:
        base = "Bourbon"
    rye = base == "Rye"
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"
    if re.search(r"cask strength", own, re.I):
        class_raw += " Cask Strength"

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]

    desc = _text(own.split("Add to cart", 1)[-1].split("Tasting Notes", 1)[0][:600])

    return BottlingRecord(
        brand_family="Castle & Key", expression=expression, name=name,
        source_url=f"https://castleandkey.com/products/{handle}", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style="rye" if rye else None, description=desc, tasting_notes=_tasting(own),
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
