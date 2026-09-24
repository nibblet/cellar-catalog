"""bardstownbourbon.com (The Bardstown Bourbon Company, Bardstown, KY — a contract distiller that also
bottles its own lines). No product sitemap; the lineup is reached from /our-products/. One WordPress page
per bottling under /products/<slug>/: an "age | N years | mash bill | Corn N% / Rye N% / … | M PROOF /
750ML" block for the house Origin Series, a "M PROOF | 375ML" line without age for the Distillery Reserve
finishes, and a bottle shot as the first non-SVG `attachment-full size-full` image. The Discovery Series
is one numbered release at a time — the newest (page named by year since 2026, by number before) is the
bottling, older numbers are history. The large Collaborative Series (one-off brewery and winery barrel
swaps: Founders KBS, Goose Island, Silver Oak, Amrut, Mars, …) and the single-barrel program pages
(state no fixed proof) are not crawled — too many one-off finishes to be "most available" bourbon."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Bardstown Bourbon Company"
DELAY = 6
SITEMAP = "https://www.bardstownbourbon.com/our-products/"  # no real product sitemap; used only as IMAGE_PREFIX's fallback host
IMAGE_PREFIX = "https://www.bardstownbourbon.com/"
CATALOG_FAMILIES = ["Bardstown Bourbon Company"]
PRODUCER_BY_FAMILY = {}
DISCOVERY_INDEX = "https://www.bardstownbourbon.com/discovery-series/"

# slug → (expression, aliases, class hint).
REFILE = {
    "origin-series-bourbon": ("Origin Series Bourbon", ["Bardstown Bourbon Company Fusion Series", "Bardstown Bourbon Company Bourbon"], None),
    "origin-series-rye": ("Origin Series Rye", [], "Kentucky Straight Rye Whiskey"),
    "origin-series-wheated-bottled-in-bond": ("Origin Series Wheated Bottled in Bond", [], "Kentucky Straight Bourbon Whiskey Bottled-in-Bond"),
    "cascadia": ("Distillery Reserve Cascadia", ["Cascadia Garryana Finish"], None),
    "cathedral-french-oak": ("Distillery Reserve Cathedral French Oak", ["Cathedral French Oak"], None),
    "hokkaido-mizunara-oak-barrel-finish": ("Distillery Reserve Hokkaido Mizunara", ["Hokkaido Mizunara Oak Barrel Finish"], None),
}
NOT_CORE = re.compile(r"distillery reserve|discovery series", re.I)
RARITY = [(r"discovery series", "unicorn"), (r"distillery reserve", "lottery"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = {f"https://www.bardstownbourbon.com/products/{slug}/" for slug in REFILE}
    page = fetcher.get(DISCOVERY_INDEX)
    slugs = re.findall(r'href="https://www\.bardstownbourbon\.com/products/(discovery(?:-series)?-[a-z0-9]+)/"', page)
    if slugs:
        urls.add(f"https://www.bardstownbourbon.com/products/{slugs[0]}/")  # the first listed is the current release
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    if slug in REFILE:
        expression, aliases, class_hint = REFILE[slug]
    elif re.match(r"discovery(-series)?-[a-z0-9]+$", slug):
        expression, aliases, class_hint = "Discovery Series", [], None
        h1 = _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
        if h1:
            aliases = [f"Bardstown Bourbon Company {h1}", h1]
    else:
        return None
    name = f"Bardstown Bourbon Company {expression}"
    own = flat.split("| You May Also")[0].split("| DISCOVER")[0]
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?) PROOF\b", own)
    pf = float(m.group(1)) if m else None
    m = re.search(r"age\| (\d{1,2}) years", own)
    years, label = (float(m.group(1)), f"{m.group(1)} yr") if m else age(name)
    if years is None and label is None and slug.startswith("discovery"):
        m = re.search(r"blends? [a-z ]*bourbons? aged (\d{1,2}), (\d{1,2}) and (\d{1,2}) years", own, re.I)
        if m:
            label = f"{min(int(x) for x in m.groups())}–{max(int(x) for x in m.groups())} yr"  # a blend of ages is a display label
    mash_raw = (re.search(r"mash bill\| ([^|]+)", own) or [None, None])[1]
    desc = _text((re.search(r"750ML\|?\s*([^|]{30,400})", own) or re.search(r"375\s?ML\|?\s*([^|]{30,400})", own) or [None, None])[1])
    rye = "rye" in expression.lower() and "bourbon" not in expression.lower()
    class_raw = class_hint or ("Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey")
    mash = "rye" if rye else "wheated" if "wheat" in (mash_raw or "").lower() else \
        "high_rye" if re.search(r"high[- ]rye", own, re.I) else None
    img = next((html.unescape(m.group(1)) for m in re.finditer(r'<img[^>]+src="([^"]+wp-content/uploads/[^"]+\.(?:png|jpe?g|webp))"[^>]*class="[^"]*attachment-full size-full', page)
                if not re.search(r"logo|icon|medal|award|gold|badge", m.group(1), re.I)), None)
    return BottlingRecord(
        brand_family="Bardstown Bourbon Company", expression=expression, name=name, source_url=url, proof=pf,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=mash, description=desc,
        image_url=img, aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
