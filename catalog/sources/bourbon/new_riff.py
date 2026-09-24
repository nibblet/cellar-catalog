"""newriffdistilling.com (Kentucky). One page per spirit under /spirits/<slug>/, WordPress: an h1 name,
a structured "Age / Proof: | Aged at least N years / M Proof" line (a single-barrel release states
"Bottled at Barrel Proof" there — no number, so no proof), mash-bill percentages just above it, and one
`class="wp-post-image"` bottle shot. The site also sells a gin (not whiskey) and New Make (unaged, not a
catalog bottling) — both skipped. Yearly limited series (Single Malt, Silver Grove Bourbon and Rye,
Headliner) keep only the current vintage; the single-barrel "Selection" and "Cigar Club" pages describe
the program, not one bottling, and state no proof, so they are skipped rather than crawled."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "New Riff"
DELAY = 6
SITEMAP = "https://newriffdistilling.com/product-sitemap.xml"
IMAGE_PREFIX = "https://newriffdistilling.com/"
CATALOG_FAMILIES = ["New Riff"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class hint). class hint overrides the rye/bourbon guess from the name.
REFILE = {
    "new-riff-bottled-in-bond-bourbon": ("Bottled in Bond Bourbon", ["New Riff Bourbon", "New Riff"], None),
    "new-riff-bottled-in-bond-rye": ("Bottled in Bond Rye", ["New Riff Rye", "New Riff Kentucky Straight Rye"], None),
    "new-riff-8-year-old-bourbon": ("8 Year Old Bourbon", ["New Riff 8 year old", "New Riff 8 Year Old"], None),
    "new-riff-8-year-old-rye": ("8 Year Old Rye", [], None),
    "new-riff-backsetter-bourbon": ("Backsetter Bourbon", [], None),
    "new-riff-backsetter-rye": ("Backsetter Rye", [], None),
    "new-riff-winter-whiskey": ("Winter Whiskey", [], None),
    "new-riff-6-year-old-malted-rye": ("6 Year Old Malted Rye", [], "Straight Rye Malt Whiskey"),
    "new-riff-red-turkey-wheat": ("Red Turkey Wheat", [], None),
    "new-riff-maltster-malted-wheat": ("Maltster Malted Wheat", [], None),
    "new-riff-maltster-bourbon-with-malted-rye": ("Maltster Bourbon With Malted Rye", [], None),
    "new-riff-maltster-bourbon-with-crystal-malt-and-malted-rye": ("Maltster Bourbon With Crystal Malt and Malted Rye", [], None),
    "new-riff-yellow-leaming-bourbon": ("Yellow Leaming Bourbon", [], None),
    "new-riff-blue-clarage-bourbon": ("Blue Clarage Bourbon", [], None),
    "new-riff-balboa-rye": ("Balboa Rye", [], None),
    "new-riff-aroostook-kentucky-grown-straight-malted-rye": ("Aroostook Kentucky-Grown Straight Malted Rye", [], "Straight Rye Malt Whiskey"),
    "new-riff-sherry-finish-malted-rye": ("Sherry Finish Malted Rye", [], "Straight Rye Malt Whiskey"),
    "olnew-riff-bourbon": ("Ol'New Riff Bourbon", ["Ol' New Riff Bourbon"], None),
    "olnew-riff-rye": ("Ol'New Riff Rye", ["Ol' New Riff Rye"], None),
    "duet-american-whiskey": ("Duet American Whiskey", ["Duet"], "Blended American Whiskey"),
    "new-riff-single-malt-whiskey-2026": ("Single Malt Whiskey", ["New Riff Single Malt Whiskey 2026", "New Riff Sour Mash Single Malt"], "American Single Malt Whiskey"),
    "new-riff-silver-grove-bourbon-2026": ("Silver Grove Bourbon", ["New Riff Silver Grove Bourbon 2026"], None),
    "new-riff-silver-grove-rye-2026": ("Silver Grove Rye", ["New Riff Silver Grove Rye 2026"], None),
    "new-riff-headliner-2026": ("Headliner", ["New Riff Headliner 2026"], None),
}
NOT_CORE = re.compile(r"single malt|silver grove|headliner|sherry finish|ol'new riff|duet|aroostook|blue clarage|yellow leaming", re.I)
RARITY = [(r"single malt|silver grove|headliner|sherry finish", "unicorn"),
          (r"ol'new riff|duet|aroostook|blue clarage|yellow leaming|balboa|red turkey|maltster", "lottery"),
          (r"8 year|backsetter|winter|malted rye", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
SKIP = re.compile(r"kentucky-wild-gin|new-riff-new-make|single-barrel")


def list_urls(fetcher) -> list[str]:
    urls = {u for u in re.findall(r"<loc>(https://newriffdistilling\.com/spirits/[a-z0-9'-]+/)</loc>", fetcher.get(SITEMAP))
            if not SKIP.search(u) and u.rstrip("/").split("/")[-1] in REFILE}
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_hint = REFILE[slug]
    name = f"New Riff {expression}"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    m = re.search(r"Age / Proof:\s*\|\s*([^|]+)", flat)
    stats = m.group(1) if m else ""
    pf = None
    m2 = re.search(r"\b(\d{2,3}(?:\.\d+)?) Proof\b", stats)
    if m2 and "barrel proof" not in stats.lower():
        pf = float(m2.group(1))
    years, label = age(stats) if stats else age(name)
    if years is None and label is None:
        years, label = age(name)
    desc = _text((re.search(r"Whiskey\| ([^|]{40,600})", flat) or re.search(r"Spirits\| ([^|]{40,600})", flat) or [None, None])[1])
    rye = bool(re.search(r"\brye\b", name, re.I)) and "bourbon" not in name.lower()
    class_raw = class_hint or ("Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey")
    if "Bottled in Bond" in expression:
        class_raw += " Bottled-in-Bond"
    mash = "rye" if class_raw and "Rye" in class_raw and "Bourbon" not in class_raw else "wheated" if "Wheat" in expression else None
    img = (re.search(r'src="([^"]+)"[^>]*class="wp-post-image"', page) or [None, None])[1]
    return BottlingRecord(
        brand_family="New Riff", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
