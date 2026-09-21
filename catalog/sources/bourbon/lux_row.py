"""Lux Row Distillers (Luxco / MGP): three WordPress sites, two page shapes.

rebelbourbon.com and ezrabrooks.com (Elementor) have one page per whiskey under /whiskey/<slug>/: a
brand h5, the name in an h4, a proof line ("50% ALC/VOL / 100 PROOF", "58.5% ALC/VOL • 117 PROOF"), a
paragraph, TASTING NOTES, INGREDIENTS and a bottle shot (the first upload image after the logo; the
rest are sibling thumbs). Rebel's lineup comes from its page sitemap (the /whiskey/ index renders in
JS); Ezra's from the links on its /whiskey/ index, which drops the retired pages the sitemap keeps.

luxrowdistillers.com carries the smaller brands as one page per brand with a tab per variant
(<div id="varieties-N">): an h2 brand, an h5 variant, copy, INGREDIENTS, sometimes a proof block
(".unit" 49.3 % / 98.6 PROOF). Daviess County prints its proof only as an image and states it once in
prose ("Like all Daviess County variants … is 96 proof"), which applies to every tab; David Nicholson's
proof image is named for what it shows ("50-100_proof.png"). Blood Oath lists every pact; the first
tab is the current one and the catalog keeps one Blood Oath row with the pacts as releases."""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin, urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, titlecase

PRODUCER = "Lux Row"
DELAY = 6
SITEMAP = "https://rebelbourbon.com/page-sitemap.xml"
IMAGE_PREFIX = "https://"  # three hosts; the hero insert is guarded by source and the missing-image check
CATALOG_FAMILIES = ["Rebel", "Rebel Yell", "Ezra Brooks", "Old Ezra", "Daviess County", "Blood Oath", "David Nicholson", "Lux Row"]
PRODUCER_BY_FAMILY = {}
EZRA_INDEX = "https://ezrabrooks.com/whiskey/"
LUX_PAGES = ["https://luxrowdistillers.com/blood-oath/", "https://luxrowdistillers.com/daviess-county-bourbon/",
             "https://luxrowdistillers.com/david-nicholson/", "https://luxrowdistillers.com/lux-row-double-barrel/"]

# rebelbourbon.com / ezrabrooks.com slug → (family, expression, aliases). Flavored whiskeys and the cream are not listed.
REFILE = {
    "kentucky-straight-bourbon": ("Rebel", None, ["Rebel Kentucky Straight Bourbon", "Rebel Bourbon", "Rebel Yell", "Rebel Yell Kentucky Straight Bourbon", "Rebel 80"]),
    "100-proof-bourbon": ("Rebel", "100", ["Rebel 100 Proof Bourbon", "Rebel Yell 100", "Rebel 100 Proof"]),
    "rebel-100-aged-6-years": ("Rebel", "100 Aged 6 Years", ["Rebel 100 6 Year", "Rebel 6 Year 100 Proof"]),
    "small-batch-reserve": ("Rebel", "Small Batch Reserve", ["Rebel Yell Small Batch Reserve"]),
    "10-year-single-barrel-bourbon": ("Rebel", "10 Year Single Barrel", ["Rebel Yell 10 Year Single Barrel", "Rebel 10 Year Single Barrel Bourbon"]),
    "straight-rye-whiskey": ("Rebel", "Straight Rye", ["Rebel 100 Proof Straight Rye Whiskey", "Rebel Yell Straight Rye", "Rebel Rye", "Rebel 100 Rye"]),
    "kyle-busch-108": ("Rebel", "Kyle Busch 108", ["Rebel KB108", "Rebel Kyle Busch 108 Single Barrel", "Rebel KB108 V2"]),
    "kyle-busch-108-v2": ("Rebel", "Kyle Busch 108", ["Rebel KB108", "Rebel Kyle Busch 108 Single Barrel", "Rebel KB108 V2"]),
    "ezra-90": ("Ezra Brooks", "90", ["Ezra Brooks Kentucky Straight Bourbon", "Ezra Brooks Bourbon", "Ezra 90"]),
    "ezra-99": ("Ezra Brooks", "99", ["Ezra Brooks 99 Bourbon", "Ezra Brooks 99 Proof", "Ezra 99"]),
    "ezra-99-rye": ("Ezra Brooks", "99 Rye", ["Ezra Brooks Straight Rye", "Ezra Brooks 99 Straight Rye Whiskey", "Ezra 99 Rye"]),
    "old-ezra": ("Old Ezra", "Barrel Strength", ["Old Ezra 7 Year Barrel Strength", "Old Ezra 7 Year", "Old Ezra Extra Aged Bourbon", "Old Ezra 7"]),
    "old-ezra-7-straight-rye-whiskey": ("Old Ezra", "7 Year Rye", ["Old Ezra 7-Year Straight Rye Whiskey", "Old Ezra 7 Year Straight Rye", "Old Ezra Rye"]),
    "cask-finished-series": ("Ezra Brooks", "", []),  # the expression is the page's h4 ("PORT CASK FINISH"): the series rotates
}
CASK_ALIASES = {"Port Cask Finish": ["Ezra Brooks 99 Special Cask Finished Series Port Wine Cask Finished", "Ezra Brooks 99 Port Cask Finish", "Ezra Brooks Port Cask Finished"]}
# luxrowdistillers.com: (brand h2, variant h5) → (family, expression, aliases)
LUX_TABS = {
    ("BLOOD OATH", None): ("Blood Oath", None, ["Blood Oath Pact", "Blood Oath Bourbon"]),
    ("DAVIESS COUNTY", "KENTUCKY STRAIGHT WHISKEY"): ("Daviess County", "Bourbon", ["Daviess County Kentucky Straight Bourbon", "Daviess County"]),
    ("DAVIESS COUNTY", "CABERNET SAUVIGNON FINISH"): ("Daviess County", "Cabernet Sauvignon Finish", ["Daviess County Cabernet Sauvignon Cask Finish"]),
    ("DAVIESS COUNTY", "FRENCH OAK"): ("Daviess County", "French Oak Cask Finish", ["Daviess County French Oak", "Daviess County French Oak Finish"]),
    ("DAVIESS COUNTY", "MEDIUM TOASTED BARREL FINISHED BOURBON"): ("Daviess County", "Toasted Barrel Finish", ["Daviess County Toasted Barrel Finish Series", "Daviess County Medium Toasted Barrel Finished Bourbon"]),
    ("DAVID NICHOLSON", "1843"): ("David Nicholson", "1843", ["David Nicholson 1843 Bourbon"]),
    ("DAVID NICHOLSON", "RESERVE"): ("David Nicholson", "Reserve", ["David Nicholson Reserve Bourbon"]),
    ("LUX ROW", "12 YEAR DOUBLE BARREL"): ("Lux Row", "12 Year Double Barrel", ["Lux Row Distillers Double Barrel", "Lux Row Double Barrel", "Lux Row Distillers 12 Year Double Barrel"]),
    ("LUX ROW", "FOUR GRAIN DOUBLE SINGLE BARREL"): ("Lux Row", "Four Grain Double Single Barrel", ["Lux Row Distillers Four Grain Double Single Barrel"]),
    ("LUX ROW", "SMALL BATCH PX SHERRY CASK FINISH"): ("Lux Row", "Small Batch PX Sherry Cask Finish", ["Lux Row Distillers Small Batch PX Sherry Cask Finish"]),
}
NOT_CORE = re.compile(r"10 year|single barrel|kyle busch|french oak|small batch reserve|cask finish|barrel finish|cabernet|blood oath|lux row|double barrel|four grain|aged 6", re.I)
RARITY = [(r"blood oath|lux row", "lottery"), (r"10 year|kyle busch|old ezra|cask finish|barrel finish|cabernet|french oak|small batch reserve|david nicholson", "allocated"),
          (r"aged 6|99 rye|daviess", "limited"), (r".", "shelf")]
MASH_BILLS = {}
SKIP = re.compile(r"root-beer|ginger|butter-pecan|bourbon-cream|blended-whiskey|kyle-busch-108/$|french-oak-finish")  # KB108 V2 is the current label; French Oak is a 2020 page the lineup nav no longer links


def list_urls(fetcher) -> list[str]:
    urls = {u for u in re.findall(r"<loc><!\[CDATA\[(https://rebelbourbon\.com/whiskey/[^\]]+)\]\]>", fetcher.get(SITEMAP)) if not SKIP.search(u)}
    urls |= {"https://ezrabrooks.com" + p for p in re.findall(r'href="(?:https://ezrabrooks\.com)?(/whiskey/[a-z0-9-]+/)"', fetcher.get(EZRA_INDEX)) if not SKIP.search(p)}
    urls |= set(LUX_PAGES)
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'").replace("|", "")
    t = re.sub(r"\s+", " ", t).replace(" ,", ",").strip()
    return t or None


def _flat(fragment: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", fragment, flags=re.S)))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _mash(ingredients: str | None, name: str, class_raw: str = "") -> str | None:
    t = (ingredients or "").lower()
    if "Rye Whiskey" in class_raw:
        return "rye"
    if re.search(r"four[- ]grain", name, re.I):
        return "four_grain"
    if "wheat" in t and "rye" in t:
        return "unknown"  # Daviess County blends a wheated and a ryed mash bill: neither family
    if "wheat" in t:
        return "wheated"
    if "rye" in t:
        return "traditional"
    return None


def _record(url, family, expression, aliases, *, pf, copy, ingredients, notes, img, h_name, class_raw, finish=None, years_label=None):
    name = f"{family} {expression}" if expression else family
    years, label = years_label if years_label else age(" ".join(x for x in (expression, copy) if x))
    if years is None and label is None and copy:
        m = re.search(r"barrels? for (\d{1,2}|[a-z]+) years", copy)  # "We age this … in new, charred white oak barrels for seven years"
        if m:
            years, label = age(f"aged {m.group(1)} years")
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=ingredients, mash_style=_mash(ingredients, name, class_raw), description=copy, tasting_notes=notes,
        image_url=img, finish=finish, aliases=sorted({*aliases, *([h_name] if h_name else [])} - {name}), is_core_range=not NOT_CORE.search(name),
    )


def _brand_page(url: str, page: str, slug: str) -> BottlingRecord | None:
    family, expression, aliases = REFILE[slug]
    h4 = _text((re.search(r'<h4 class="elementor-heading-title[^"]*">(.*?)</h4>', page, re.S) or [None, ""])[1])
    if slug == "cask-finished-series":
        expression = titlecase(h4) if h4 else None
        aliases = CASK_ALIASES.get(expression or "", [])
    flat = _flat(page)
    m = re.search(r"(\d{2,3}(?:\.\d+)?) PROOF\b", flat)
    pf = float(m.group(1)) if m else None
    own = flat[m.end():].split("| TASTING NOTES")[0] if m else ""
    copy = _text(own.split("| STOCK UP")[0].split("| Buy Now")[0])
    notes = _text((re.search(r"TASTING NOTES\s*\|\s*([^|]+)", flat) or [None, ""])[1])
    ingredients = _text((re.search(r"INGREDIENTS\s*\|\s*([^|]+)", flat) or [None, ""])[1])
    imgs = [urljoin(url, s) for s in re.findall(r'<img[^>]+(?:data-src|src)="([^"]+uploads[^"]+)"', page)]
    img = next((i for i in imgs if not re.search(r"logo|accent|icon|no-product|old-fashioned", i, re.I)), None)
    rye = bool(re.search(r"\brye\b", f"{expression or ''} {h4 or ''}", re.I))
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"
    finish = re.sub(r"\s*Finish(ed)?\b", "", expression) if expression and "Finish" in expression else None
    h_name = None
    if h4 and slug != "cask-finished-series":
        t = titlecase(h4)
        h_name = t if t.lower().startswith(family.lower()) else f"{family} {t}"
        if h_name.lower() == family.lower():
            h_name = None  # "OLD EZRA" names the brand, not this bottling
    return _record(url, family, expression, aliases, pf=pf, copy=copy, ingredients=ingredients, notes=notes, img=img, h_name=h_name, class_raw=class_raw, finish=finish)


def _lux_page(url: str, page: str) -> list[BottlingRecord]:
    out = []
    tabs = re.split(r'<div id="varieties-\d+"', page)[1:]
    whole = _flat(page)
    m = re.search(r"all (?:[A-Z][a-z]+ )+variants[^.|]*?(\d{2,3}(?:\.\d+)?) proof", whole, re.I)
    page_proof = float(m.group(1)) if m else None  # Daviess County states its one proof once, for every variant
    for seg in tabs:
        h2 = _text((re.search(r"<h2[^>]*>(.*?)</h2>", seg, re.S) or [None, ""])[1])
        h5 = _text((re.search(r"<h5[^>]*>(.*?)</h5>", seg, re.S) or [None, ""])[1])
        key = (h2.upper() if h2 else "", None if h2 and h2.upper() == "BLOOD OATH" else (h5.upper() if h5 else ""))
        if key not in LUX_TABS:
            continue
        family, expression, aliases = LUX_TABS[key]
        flat = _flat(seg)
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\| PROOF", flat)
        pf = float(m.group(1)) if m else page_proof
        if pf is None:
            m = re.search(r"/\d{2}(?:\.\d)?-(\d{2,3}(?:\.\d)?)_proof\.png", seg)  # David Nicholson: the proof is an image named for it
            pf = float(m.group(1)) if m else None
        copy = _text(flat.split("| INGREDIENTS")[0].split(f"{h5}| " if h5 else "| ", 1)[-1].split("| Only for a Lucky Few")[0].split("| Due to the limited")[0])
        ingredients = _text((re.search(r"INGREDIENTS\s*\|\s*([^|]+)", flat) or [None, ""])[1])
        notes = _text(" ".join(re.findall(r"(?:AROMA|PALATE|FINISH)\|\s*([^|]+)", flat)))
        # The bottle is the one image sized in px; icons, medals and the proof image are capped with max-width.
        imgs = [urljoin(url, re.search(r'src="([^"]+)"', tag).group(1)) for tag in re.findall(r"<img[^>]+>", seg)
                if "max-width" not in tag and re.search(r'src="', tag) and not re.search(r"icon|proof", tag, re.I)]
        img = imgs[0] if imgs else None
        years_label = None
        if family == "Blood Oath":
            aliases = [*aliases, f"Blood Oath {h5}", f"Blood Oath {h5.replace('No. ', '')}"] if h5 else aliases
            ages = sorted({int(a) for a in re.findall(r"(\d{1,2})-year", copy or "")})
            if len(ages) >= 2:
                years_label = (None, f"{ages[0]}–{ages[-1]} yr")  # a blend of ages is a display label
        finish = re.sub(r"\s*Finish(ed)?\b", "", expression.replace("Small Batch ", "")) if expression and "Finish" in expression else None
        class_raw = "Kentucky Straight Bourbon Whiskey"
        out.append(_record(url, family, expression, aliases, pf=pf, copy=copy, ingredients=ingredients, notes=notes, img=img,
                           h_name=None, class_raw=class_raw, finish=finish, years_label=years_label))
        if family == "Blood Oath":
            break  # the first tab is the current pact; older pacts are releases of the same row
    return out


def parse(url: str, page: str) -> BottlingRecord | list[BottlingRecord] | None:
    host = urlparse(url).netloc
    if host == "luxrowdistillers.com":
        return _lux_page(url, page)
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    return _brand_page(url, page, slug)
