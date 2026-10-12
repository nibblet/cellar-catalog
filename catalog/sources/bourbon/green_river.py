"""greenriverwhiskey.com (Green River Distilling Co., Owensboro — greenriverdistilling.com redirects
here). WordPress + Elementor, no cart (a "Buy" button links out to a third-party retailer); every page
is static HTML, no JS needed. Proof is printed two ways across the site — "(90 proof)" and "[92 PROOF]" —
so both bracket styles are matched. The flagship three (Kentucky Straight Bourbon, Kentucky Wheated
Bourbon, Kentucky Straight Rye) name their mash bill only in prose ("high-rye mash bill", "high-wheat
mash bill") with no percentages and state no age on the page itself (an age *is* published, but only on
a separate FAQ page, which is not read as this bottling's own statement); everything else — Full Proof,
Wheated Full Proof, the two Single Barrel programs, Toasted Double Oak, 1885 Bourbon — carries a
structured "Mash Bill | N% | grain | N% | grain | N% | grain" block. Age is stated inconsistently:
Toasted Double Oak says "After aging eight years" (present participle, not `normalize.age()`'s "aged"),
1885 states "aged four years" plainly, and both Single Barrel pages state "aged a minimum of/over five
years" with proof left as "Proof Varies by Barrel" since cask strength differs bottle to bottle — the
maker's own single-barrel policy statement, not a legal floor, so it's trusted the same as any other
stated age.

`tasting_notes` is the page's own "tasting notes" block: its Taste and Finish lines (the Appearance line is left out). The
honey-finished whiskey prints no such block, so it stays None."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Green River"
DELAY = 6
SITEMAP = "https://greenriverwhiskey.com/sitemap.xml"
IMAGE_PREFIX = "https://greenriverwhiskey.com/"
CATALOG_FAMILIES = ["Green River"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases). expression None is the plain "Green River" flagship.
REFILE = {
    "kentucky-straight-bourbon": (None, []),
    "kentucky-wheated-bourbon": ("Wheated Bourbon", []),
    "kentucky-straight-rye": ("Rye", []),
    "full-proof-bourbon": ("Full Proof", []),
    "wheated-full-proof-bourbon": ("Wheated Full Proof", []),
    "single-barrel-bourbon": ("Single Barrel", []),
    "single-barrel-wheated": ("Wheated Bourbon Single Barrel", []),
    "honey-whiskey": ("Honey Finished", []),
    "toasted-double-oak": ("Distillery Select: Toasted Double Oak", []),
    "1885-bourbon": ("1885 Bourbon", []),
}
CORE = {None, "Wheated Bourbon", "Rye", "Full Proof", "Wheated Full Proof", "Honey Finished"}
RARITY = [(r"toasted double oak", "lottery"), (r"single barrel|1885", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://greenriverwhiskey.com/{slug}/" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _tasting_notes(own: str) -> str | None:
    """`tasting notes | Taste | ... | appearance | ... | finish | ...` up to the page's next section."""
    m = re.search(r"tasting notes\s*\|", own, re.I)
    if not m:
        return None
    zone = re.split(r"Find Green River Near You|LINKS\b|FREQUENTLY ASKED", own[m.end():], maxsplit=1)[0]
    got = [(label, _text(v.group(1))) for label, pat in (("Taste", r"Taste\s*\|\s*([^|]+)"), ("Finish", r"finish\s*\|\s*([^|]+)"))
           if (v := re.search(pat, zone, re.I))]
    return " ".join(f"{label}: {text.rstrip('.')}." for label, text in got if text)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases = REFILE[slug]
    name = f"Green River {expression}" if expression else "Green River"

    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.sub(r"(\|\s*)+", "| ", own)

    pm = re.search(r"[\(\[]\s*(\d{2,3}(?:\.\d+)?)\s*proof\s*[\)\]]", own, re.I)
    proof = float(pm.group(1)) if pm else None

    mm = re.search(r"Mash Bill\|\s*(.*?)\|\s*tasting notes", own, re.I)
    mash_raw = None
    if mm:
        parts = re.findall(r"(\d+(?:\.\d+)?)\s*%\|\s*([^|]+)", mm.group(1))
        mash_raw = ", ".join(f"{pct}% {grain.strip().title()}" for pct, grain in parts) or None
    elif re.search(r"high[- ]rye mash bill", own, re.I):
        mash_raw = "High-Rye Mash Bill"
    elif re.search(r"high[- ]wheat mash bill", own, re.I):
        mash_raw = "High-Wheat Mash Bill"

    age_text = own.replace("aging", "aged")
    years, label = age(age_text)

    rye = expression == "Rye"
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]

    desc = _text(own.split("tasting notes", 1)[0][-600:] if "tasting notes" in own.lower() else own[:600])

    return BottlingRecord(
        brand_family="Green River", expression=expression, name=name,
        source_url=f"https://greenriverwhiskey.com/{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style="rye" if rye else None, description=desc,
        tasting_notes=_tasting_notes(own), image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
