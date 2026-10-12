"""2xowhiskey.com (Two Times Oak / 2XO by Dixon Dedman, Prestige Beverage Group). WordPress; robots asks for a
10 s Crawl-delay. No page states a proof or age in text, and nearly every bottle photo is a small lifestyle
shot whose label cannot be read. The one exception is American Oak: its page's product photo
(`2XO_AmericanOak_BlueBG_Edited.jpg`) shows "46% ALC/VOL" on the label (the PROOF line is hidden behind the
glass), read by hand; proof is ABV x 2 = 92, which also matches the seeded value. The module uses it only
while that same image is still on the cached page. The other products (French Oak, Gem of Kentucky, Kiawah,
Tribute, Innkeeper's, Phoenix, Vinyl, Sneakerhead, Hip-Hop) are listed so a future proof is picked up but
state nothing today. `tasting_notes` is the page's own palate line (the "moves from sweet ... finishing with" sentence of
the intro) plus its Tasting Notes block: Nose / Taste / Finish tabs on most pages, one paragraph on Gem of Kentucky. The
"What's New" press links below it are other articles and are never read."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Two Times Oak"
DELAY = 10
SITEMAP = "https://2xowhiskey.com/page-sitemap.xml"
IMAGE_PREFIX = "https://2xowhiskey.com/"
CATALOG_FAMILIES = ["2XO"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Kentucky Straight Bourbon Whiskey"
# slug → (expression, name, aliases, class, proof read from the label photo, photo file)
PAGES = {
    "american-oak": ("Oak Series American Oak", "2XO Oak Series American Oak", [], BOURBON, 92.0, "2XO_AmericanOak_BlueBG_Edited.jpg"),
    "french-oak": ("Oak Series French Oak", "2XO Oak Series French Oak", [], BOURBON, None, None),
    "gem-of-kentucky": ("Gem of Kentucky", "2XO Gem of Kentucky", [], BOURBON, None, None),
    "kiawah-blend": ("The Kiawah Blend", "2XO The Kiawah Blend", [], "Blend of Straight Bourbon Whiskeys", None, None),
    "the-tribute-blend": ("The Tribute Blend", "2XO The Tribute Blend", [], "Blend of Straight Bourbon Whiskeys", None, None),
}
CORE = {"Oak Series American Oak"}
RARITY = [(r"gem|kiawah|tribute", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://2xowhiskey.com/{slug}/" for slug in PAGES]


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")).strip()


def _notes(page: str) -> str | None:
    """The intro's palate sentence, then the Tasting Notes tabs ("Nose: ... Taste: ... Finish: ...") or paragraph under the heading."""
    sec = re.search(r'<section class="tasting-notes">(.*?)</section>', page, re.S)
    parts = []
    for intro in re.findall(r"<p>([^<]*\b(?:moves|moving)(?:\s|&nbsp;|\xa0)from[^<]*)</p>", page):
        parts += re.findall(r"[^.]*\b(?:moves|moving) from [^.]*\.", _clean(intro))
    tabs = re.findall(r'id="pills-(nose|taste|finish)"[^>]*>(.*?)</div>', sec.group(1), re.S) if sec else []
    for tab, body in tabs:
        items = [_clean(x) for x in re.findall(r"<p>(.*?)</p>", body, re.S)]
        if any(items):
            parts.append(f"{tab.capitalize()}: {', '.join(i for i in items if i)}.")
    if not tabs:
        para = re.search(r"<h2>Tasting Notes</h2>\s*<p>(.*?)</p>", page, re.S)
        parts += [_clean(para.group(1))] if para else []
    text = " ".join(p.strip() for p in parts).strip()
    return text[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, name, aliases, class_raw, proof, photo = PAGES[slug]
    stated = bool(photo and photo in page)
    return BottlingRecord(
        brand_family="2XO", expression=expression, name=name, source_url=url,
        proof=proof if stated else None, class_raw=class_raw,
        image_url=f"https://2xowhiskey.com/wp-content/uploads/2023/09/{photo}" if stated else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE, tasting_notes=_notes(page),
    )
