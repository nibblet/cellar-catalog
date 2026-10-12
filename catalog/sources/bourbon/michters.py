"""michters.com — Michter's Distillery (WordPress + WPBakery). /whiskeys/ links one page per whiskey
(/whiskey/<slug>/ redirects to /<slug>/). Each page: an h2 with the full name ("Michter's US★1 Kentucky
Straight Bourbon"), an ABV line ("47.2% ALC./VOL", or "ALC./VOL VARIES"), a description, a facts block
("BOTTLING STRENGTH | 94.4 proof (47.2% Alcohol by Volume)") and one straight-on bottle shot. Barrel
strength pages give a "BARRELING STRENGTH | 103 Proof" (entry proof, ignored) and either a range for
the year's release (no proof) or its average (taken). The Legacy Series pages (Bomberger's, Shenk's)
and Celebration stack one block per year, newest first; the first block is the current release.
tasting_notes is that block's own "TASTING NOTES" paragraph, or the Legacy Series' NOSE / PALATE / FINISH lines (APPEARANCE is a colour)."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Michter's"
DELAY = 6
SITEMAP = "https://michters.com/sitemap.xml"
IMAGE_PREFIX = "https://michters.com/"
INDEX = "https://michters.com/whiskeys/"
CATALOG_FAMILIES = ["Michter's", "Bomberger's", "Shenk's"]
PRODUCER_BY_FAMILY = {}

# slug → (family, expression, aliases). The catalog writes US★1 as US*1.
REFILE = {
    "kentucky-straight-bourbon": ("Michter's", "US*1 Bourbon", ["Michter's US*1 Kentucky Straight Bourbon", "Michter's US*1 Small Batch Bourbon"]),
    "us1-kentucky-straight-rye": ("Michter's", "US*1 Rye", ["Michter's US*1 Kentucky Straight Rye", "Michter's US*1 Single Barrel Rye"]),
    "sour-mash": ("Michter's", "US*1 Sour Mash", ["Michter's US*1 Original Sour Mash", "Michter's US*1 Sour Mash Whiskey"]),
    "us1-american-whiskey": ("Michter's", "US*1 American Whiskey", ["Michter's US*1 Unblended American Whiskey"]),
    "10-year-kentucky-straight-bourbon": ("Michter's", "10 Year Bourbon", ["Michter's 10 Yr", "Michter's 10 Year", "Michter's 10 Year Kentucky Straight Bourbon", "Michter's 10 Year Single Barrel Bourbon"]),
    "10-year-kentucky-straight-rye": ("Michter's", "10 Year Rye", ["Michter's 10 Year Kentucky Straight Rye", "Michter's 10 Year Single Barrel Rye"]),
    "20-year-kentucky-straight-bourbon": ("Michter's", "20 Year Bourbon", ["Michter's 20 Yr", "Michter's 20 Year", "Michter's 20 Year Kentucky Straight Bourbon"]),
    "25-year-kentucky-straight-bourbon": ("Michter's", "25 Year Bourbon", ["Michter's 25 Yr", "Michter's 25 Year", "Michter's 25 Year Kentucky Straight Bourbon"]),
    "25-year-kentucky-straight-rye": ("Michter's", "25 Year Rye", ["Michter's 25 Year Kentucky Straight Rye"]),
    "us-1-barrel-strength-rye": ("Michter's", "US*1 Barrel Strength Rye", []),
    "us-1-limited-release-barrel-strength-bourbon": ("Michter's", "US*1 Barrel Strength Bourbon", ["Michter's US*1 Limited Release Barrel Strength Bourbon"]),
    "us-1-barrel-strength-sour-mash": ("Michter's", "US*1 Barrel Strength Sour Mash", []),
    "us1-toasted-barrel-finish-bourbon": ("Michter's", "US*1 Toasted Barrel Finish Bourbon", ["Michter's Toasted Finish", "Michter's US*1 Toasted Barrel Finish"]),
    "toasted-barrel-finish-rye": ("Michter's", "US*1 Toasted Barrel Finish Rye", []),
    "us1-toasted-barrel-finish-sour-mash": ("Michter's", "US*1 Toasted Barrel Finish Sour Mash", []),
    "bombergers-declaration": ("Bomberger's", "Declaration", ["Bomberger's Declaration Kentucky Straight Bourbon"]),
    "bombergers-pfg": ("Bomberger's", "PFG", ["Bomberger's PFG Precision Fine Grain Bourbon", "Bomberger's Precision Fine Grain"]),
    "shenks-homestead": ("Shenk's", "Homestead Sour Mash", ["Shenk's Homestead", "Shenk's Homestead Sour Mash Whiskey"]),
    "celebration-sour-mash": ("Michter's", "Celebration Sour Mash", []),
}
NOT_CORE = re.compile(r"10 year|20 year|25 year|barrel strength|toasted|bomberger|shenk|celebration", re.I)
RARITY = [(r"20 year|25 year|celebration", "unicorn"), (r"10 year|toasted barrel finish rye|barrel strength|bomberger|shenk", "lottery"), (r"toasted", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    index = fetcher.get(INDEX)
    slugs = set()
    years = {}
    for href in re.findall(r'href="(?:https://michters\.com)?/(?:whiskey/)?([a-z0-9-]+)/?"', index):
        m = re.match(r"celebration-sour-mash-(\d{4})$", href)
        if m:
            years[int(m.group(1))] = href
        elif href in REFILE and href != "celebration-sour-mash":  # the bare slug redirects to the 2013 page
            slugs.add(href)
    if years:
        slugs.add(years[max(years)])  # the current Celebration release
    return sorted(f"https://michters.com/{s}/" for s in slugs)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _tasting(own: str) -> str | None:
    """`own` is the current release's block (cut before the older years and the sibling-whiskey links)."""
    m = re.search(r"TASTING NOTES\| ([^|]+)", own, re.I)
    if m:
        return (_text(m.group(1)) or "")[:900] or None
    parts = []
    for key in ("NOSE", "PALATE", "FINISH"):
        m = re.search(rf"\| {key}\| ([^|]+)", own)
        body = _text(m.group(1)).rstrip(" ,;") if m else None
        if body:
            parts.append(f"{key.title()}: {body}" + ("" if body.endswith((".", "!")) else "."))
    return " ".join(parts)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.strip("/")
    slug = re.sub(r"^celebration-sour-mash-\d{4}$", "celebration-sour-mash", slug)
    if slug not in REFILE:
        return None
    family, expression, aliases = REFILE[slug]
    name = f"{family} {expression}"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'").replace("★", "*")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    h2 = _text((re.search(r'<h2[^>]*class="vc_custom_heading"[^>]*>(.*?)</h2>', page, re.S) or [None, ""])[1])
    if h2:
        h2 = re.sub(r"US\s*[★*]\s*1", "US★1", h2)
    # The current release is the first block: from its heading to the next year heading / the footer.
    start = flat.find(h2.replace("★", "*")) if h2 else 0
    own = re.split(r"\| \d{4}\| LEGACY SERIES|\| Whiskeys\| The US|\| Share:|Are You of Legal Drinking Age", flat[max(start, 0):])[0][:6000]
    pf = None
    m = re.search(r"BOTTLING STRENGTH\| ([^|]*)", own)
    strength = m.group(1) if m else ""
    if re.search(r"ranged? from|between", strength, re.I):
        pf = None  # a single-barrel release's range is not a proof
    else:
        m = re.search(r"\b(\d{2,3}(?:\.\d+)?) proof", strength, re.I)
        pf = float(m.group(1)) if m else None
    if pf is None and not re.search(r"BOTTLING STRENGTH", own):
        m = re.search(r"\b(\d{2}(?:\.\d+)?)% ALC\./VOL", own)  # the header line ("54% ALC./VOL"); "VARIES" states nothing
        pf = round(float(m.group(1)) * 2, 1) if m else None
    desc = _text((re.search(r'single-whiskey-page-product-description-new\s*">\s*<div class="wpb_wrapper">(.*?)</div>', page, re.S) or [None, ""])[1])
    years, label = age(" ".join(x for x in (h2, expression) if x))
    blend = re.search(r"youngest whiskey being (?:over )?(\d{1,2}) years old and the oldest whiskey being (?:over )?(\d{1,2})", desc or "")
    if blend:  # Celebration: a blend spanning ages is a display label
        years, label = None, f"{blend.group(1)}–{blend.group(2)} yr"
    elif years is None and label is None and desc:
        years, label = age(desc)
    m = re.search(r"WHISKEY TYPE\| ([^|]*)", own)
    class_raw = m.group(1).strip() if m else ""
    if not class_raw:
        class_raw = "Kentucky Straight Rye Whiskey" if "Rye" in expression else "Kentucky Straight Bourbon Whiskey" if "Bourbon" in expression or family == "Bomberger's" \
            else "Sour Mash Whiskey" if "Sour Mash" in expression else "American Whiskey"
    img = (re.search(r'bottleimageonorder">.*?<img[^>]+src="([^"]+)"', page, re.S) or [None, None])[1]
    mash = "rye" if "Rye" in expression else None
    finish = "Toasted Barrel" if "Toasted Barrel" in expression else None
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=desc, tasting_notes=_tasting(own),
        image_url=html.unescape(img) if img else None, finish=finish,
        aliases=sorted({*aliases, *([h2.replace("★", "*"), h2] if h2 else [])} - {name}),
        is_core_range=not NOT_CORE.search(name),
    )
