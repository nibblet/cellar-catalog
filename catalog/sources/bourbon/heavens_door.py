"""heavensdoor.com (Heaven's Door Spirits, Bob Dylan's whiskey brand — Wix). The site went through a
full rebrand: every core expression now carries a mythic release name (Refuge, Revival, Ascension,
Revelation) alongside its plain descriptive class, and the seed predates it — filed under the old plain
names ("Tennessee Bourbon", "Double Barrel") or, for the rye, an old cask finish ("Finished in Vosges Oak
Barrels Rye") the current page no longer states (it's finished in sherry casks now; same proof, same only
rye in the lineup, treated as the same evolving product). `REFILE` keeps the plain descriptive expression
so the exact-name and alias matches still land. Every core page carries a "PROOF | ALC./VOL" line and an
"AGE: At least N years" line; only the rye states a mash bill ("100% rye mash bill" in prose — the
bourbons never give grain percentages). The site's many limited/historical sub-lines (Bootleg Series,
Exploration Series, Decade Series, Master Blender's Edition, Trilogy Collection — a gift bundle of the
core three, not its own product) state no proof in static text on their landing pages at all (each
numbered volume apparently only lives in the Wix Store's own JS-rendered product cards, not in page copy)
and are not crawled; the seed's many rows for them have no current-page correspondence to check against
and are left for a human to reconcile rather than guessed at."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Heaven's Door"
DELAY = 6
SITEMAP = "https://www.heavensdoor.com/pages-sitemap.xml"
IMAGE_PREFIX = "https://static.wixstatic.com/"
CATALOG_FAMILIES = ["Heaven's Door"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases).
REFILE = {
    "straight-rye-whiskey": ("Rye", ["Heaven's Door Finished in Vosges Oak Barrels Rye"]),
    "tn-straight-bourbon-whiskey": ("TN Straight Bourbon", ["Heaven's Door Tennessee Bourbon"]),
    "ky-straight-bourbon-whiskey": ("KY Straight Bourbon", []),
    "double-barrel-whiskey": ("Double Barrel", []),
}
RARITY = [(r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://www.heavensdoor.com/{slug}" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Heaven's Door {expression}"

    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)

    pm = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*PROOF\s*\|\s*\d{1,3}(?:\.\d+)?%\s*ALC\./VOL", own)
    proof = float(pm.group(1)) if pm else None

    am = re.search(r"AGE:\|\s*At least (\w+) years?", own, re.I)
    years, label = age(f"aged at least {am.group(1)} years") if am else (None, None)

    rye = expression == "Rye"
    if rye:
        class_raw = "Kentucky Straight Rye Whiskey"
    elif expression == "TN Straight Bourbon":
        class_raw = "Tennessee Straight Bourbon Whiskey"
    elif expression == "Double Barrel":
        class_raw = "Double Barrel Whiskey"
    else:
        class_raw = "Kentucky Straight Bourbon Whiskey"

    mm = re.search(r"(\d{1,3})%\s*rye mash bill", own, re.I)
    mash_raw = f"{mm.group(1)}% Rye" if mm else None

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]

    desc = _text(own.split("AGE:", 1)[0][-600:])

    return BottlingRecord(
        brand_family="Heaven's Door", expression=expression, name=name,
        source_url=f"https://www.heavensdoor.com/{slug}", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style="rye" if rye else None, description=desc,
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=True,
    )
