"""garrisonbros.com (Garrison Brothers Distillery, Hye, Texas — garrisonbrothers.com is an unrelated
parked domain, not the maker). WordPress with a Rank Math `Product` JSON-LD block on every page, whose
`additionalProperty` "Proof" value and `isRelatedTo` ("Permanent Collection" vs "Limited Release", which
matches the site's own "Our Babies" vs "Limited Releases" nav split) are reliable, but whose `category`
is a fixed site-wide "Texas Straight Bourbon Whiskey" default rather than a per-product statement, and
whose Proof value can lag a year behind the current release for an annually-updated page (Cowboy
Bourbon's schema said 146.4 while the body copy's current vintage said 141.0) — proof is read from the
body's own "N PROOF" line first, the schema only as a fallback. Age is the harder problem: the schema's
one-sentence `description` states it in elliptical, two-stage phrasing ("spent four years in white
American oak and four more in Pedro Ximenez sherry casks", "aged four years ... and aged an additional
year") that no single regex catches as one number — `_years()` below sums every explicit "N years"
mention, treats a bare "N more" as another mention of the same unit once a first one is established, and
treats an unquantified "an additional year" as +1; a real production floor ("aged at least six years"
under the Bottled-in-Bond Act) is a specific stated fact here, not reused boilerplate, and is trusted.
Single Barrel is a by-the-barrel purchase program bundling several proof variants on one page, not a
bottling, and Boot Flask is merchandise; neither is crawled."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Garrison Brothers"
DELAY = 6
SITEMAP = "https://www.garrisonbros.com/our-babies/"
IMAGE_PREFIX = "https://www.garrisonbros.com/"
CATALOG_FAMILIES = ["Garrison Brothers"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases).
REFILE = {
    "small-batch": ("Small Batch", ["Small Batch Texas"]),
    "honeydew": ("HoneyDew", ["Honey Dew"]),
    "balmorhea": ("Balmorhea", []),
    "guadalupe": ("Guadalupe", []),
    "lady-bird": ("Lady Bird", []),
    "cowboy-bourbon": ("Cowboy Bourbon", []),
    "laguna-madre": ("Laguna Madre", []),
    "sonora": ("Sonora", []),
    "bottled-in-bond": ("Bottled in Bond", []),
    "hye-rye": ("Hye Rye", []),
    "px": ("Ranch Reserve PX", ["PX"]),
    "oloroso": ("Ranch Reserve Oloroso", ["Oloroso"]),
    "young-gun": ("Young Gun", []),
    "estacado": ("Estacado", []),
    "hurricane-tough": ("Hurricane Tough", []),
}
RARITY = [(r"hurricane tough|young gun", "unicorn"), (r"ranch reserve|hye rye|estacado", "lottery"),
          (r"cowboy bourbon", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://www.garrisonbros.com/our-babies/{slug}/" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _years(text: str) -> tuple[float | None, str | None]:
    nums: list[float] = []
    has_years = False
    for m in re.finditer(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(years?|summers?|more)\b", text, re.I):
        raw, unit = m.group(1).lower(), m.group(2).lower()
        n = float(raw) if raw.isdigit() else _NUM_WORDS.get(raw)
        if not n:
            continue
        if unit == "more" and not has_years:
            continue
        nums.append(n)
        has_years = has_years or unit != "more"
    if has_years and re.search(r"\ban?\s+(?:additional|extra|further)\s+year\b", text, re.I):
        nums.append(1)
    if not nums:
        return None, None
    total = sum(nums)
    return total, f"{int(total) if total == int(total) else total} yr"


def _product_schema(page: str) -> dict | None:
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in data.get("@graph", []) if isinstance(data, dict) else []:
            if isinstance(node, dict) and node.get("@type") == "Product":
                return node
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Garrison Brothers {expression}"
    schema = _product_schema(page) or {}

    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    own = html.unescape(re.sub(r"<[^>]+>", "|", body))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)
    own = own.split("Skip to content", 1)[-1]

    pm = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*[%]?\s*\|*\s*PROOF\b", own, re.I)
    if pm:
        proof = float(pm.group(1))
    else:
        props = schema.get("additionalProperty") or []
        sp = next((p.get("value") for p in props if p.get("name") == "Proof"), None)
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", sp or "")
        proof = float(m.group(1)) if m else None

    description = schema.get("description") or ""
    years, label = _years(description)

    class_raw = schema.get("category") or "Texas Straight Bourbon Whiskey"
    img = ((schema.get("image") or {}).get("url"))
    core = (schema.get("isRelatedTo") or "").lower() == "permanent collection"

    return BottlingRecord(
        brand_family="Garrison Brothers", expression=expression, name=name,
        source_url=f"https://www.garrisonbros.com/our-babies/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=None, description=_text(description) or _text(own[:600]),
        image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=core,
    )
