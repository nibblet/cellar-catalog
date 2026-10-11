"""drinkmhs.com (Mile High Spirits, Denver — maker of Fireside). The brand has no site of its own:
firesidewhiskey.com does not resolve and milehighspirits.com is a parked placeholder (robots `Disallow: /`,
`noindex`, a mailto and nothing else — not read). The real maker site is drinkmhs.com (robots: `Allow: /`,
no Crawl-delay), a Vite/React single-page app: every URL, including each `/spirits/<slug>` page in its
sitemap, serves the same 6 KB shell (`<div id="root">`) and the content is drawn client-side. The whole
catalogue is a literal array (`Ct=[{slug,name,category,proof,description,...}]`) inside the hashed
`/assets/index-<hash>.js` bundle, so this module crawls the home page (to find the current bundle name) and
the bundle, and `parse()` reads that array. Nothing is rendered, nothing is evaded; the bundle is a public
static asset the site itself serves to every visitor.

What the maker sells (whiskey): Fireside Bourbon (80), Bottled in Bond (100), Wheated Bottled in Bond (100),
8 Year (105.6, Double Gold SFWSC 2026), Port / Pinot / Cabernet finishes (105.6), Rye Barrel Finish (a
single-barrel 6-year bourbon, 105.6), Barrel Share (88, brewery-barrel finish), Straight Malt (109), Peated
Single Malt (117), Hazmat Proof (single-barrel cask strength — "current release 8 Year, 143.5 Proof", a
program whose proof changes with the barrel) and Strato (106, aged in the stratosphere). Skipped: Fireside
Peach (70, flavored), Old Fashioned (bottled cocktail), and every gin, vodka, rum, tequila and liqueur.
NOT on the site: any rye whiskey page (the Spirits page names "Bottled-in-Bond Rye" in a bullet list only),
Triple Rye, a non-hazmat Single Barrel bourbon, or a High Rye bourbon. "Single Barrel Picks" is a program
(retailer/club inquiry form) that bottles "at whatever proof the barrel gives us" and states no proof.

Facts are read from the product's own array entry only: proof from `proof` (or, for Hazmat, the stated
`currentRelease`); age only from "N-year-old" / "N years old" in the product's own description (never the
Bottled-in-Bond "aged at least four years" floor, never a finishing stage or a component age); mash bill from
a stated percentage recipe. The 105.6 shared by the 8 Year and the finishes is the maker's own statement on
each page, so it counts (it looked like a seed default, but the maker prints it)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Mile High Spirits"
DELAY = 6
SITE = "https://drinkmhs.com"
SITEMAP = f"{SITE}/sitemap.xml"
IMAGE_PREFIX = f"{SITE}/"
CATALOG_FAMILIES = ["Fireside"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Straight Bourbon Whiskey"
# slug → (expression, aliases, class). expression None is the family flagship ("Fireside Bourbon").
# Catalog expressions are kept where the seed already carries the bottling ("Barrel Finish Series: Pinot Noir",
# "Rye-Barrel Finish"); the maker's own page title is an alias.
REFILE = {
    "fireside-bourbon": (None, ["Fireside", "Fireside Bourbon"], "Bourbon Whiskey"),
    "fireside-bottled-in-bond": ("Bottled in Bond", ["Fireside Bottled in Bond Bourbon"], "Bottled in Bond Straight Bourbon Whiskey"),
    "wheated-bottled-in-bond": ("Bottled in Bond Wheated", ["Fireside Wheated Bottled in Bond", "Fireside Bottled in Bond Wheated Bourbon"],
                                "Bottled in Bond Straight Wheated Bourbon Whiskey"),
    "fireside-8-year": ("8 Year", ["Fireside 8 Year Straight Bourbon"], BOURBON),
    "fireside-port-finish": ("Single Barrel Bourbon Port Barrel Finish", ["Fireside Port Finish"], "Bourbon Whiskey"),
    "fireside-pinot-finish": ("Barrel Finish Series: Pinot Noir", ["Fireside Pinot Finish"], "Bourbon Whiskey"),
    "fireside-cabernet-finish": ("Cabernet Finish", ["Fireside Cabernet Finish"], "Bourbon Whiskey"),
    "fireside-rye-barrel-finish": ("Rye-Barrel Finish", ["Fireside Rye Barrel Finish"], "Bourbon Whiskey"),
    "fireside-barrel-share": ("Barrel Share", ["Fireside Barrel Share"], "Bourbon Whiskey"),
    # No seed alias is given: key() cuts everything from "(" on, so "Fireside Single Barrel (8 Years)" collapses to the
    # name of the 4-year "Fireside Single Barrel" row, and the (5 Year) / (7 Year) / (8 Years) expressions share one
    # expression_key. Hazmat Proof is therefore added as its own row and the seed's 143.5-proof / 8-year row is merged
    # into it (sql/20261012_fireside.sql), not claimed by the matcher.
    "fireside-hazmat": ("Hazmat Proof", ["Fireside Hazmat Proof"], "Single Barrel Cask Strength Bourbon Whiskey"),
    "fireside-straight-malt": ("Straight Malt", ["Fireside Straight Malt Whiskey"], "American Single Malt Whiskey"),
    "fireside-peated-single-malt": ("Peated Single Malt", ["Fireside Peated Single Malt Whiskey"], "American Single Malt Whiskey"),
    "strato-whiskey": ("Strato Whiskey", ["Fireside Strato Whiskey"], "Bourbon Whiskey"),
}
# Standing lineup only. Finishes, the 8 Year ("first small-batch release"), Hazmat (a per-barrel program), the
# anniversary Straight Malt, Barrel Share and Strato are releases.
CORE = {None, "Bottled in Bond", "Bottled in Bond Wheated", "Peated Single Malt"}
RARITY = [(r"strato|barrel share", "limited"), (r"hazmat|8 year", "allocated"), (r"finish|straight malt", "limited"), (r".", "shelf")]
MASH_BILLS = {}

_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12}


def _bundle_url(home: str) -> str | None:
    m = re.search(r'src="(/assets/index-[A-Za-z0-9_-]+\.js)"', home)
    return SITE + m.group(1) if m else None


def list_urls(fetcher) -> list[str]:
    bundle = _bundle_url(fetcher.get(SITE + "/"))
    return [SITE + "/", bundle] if bundle else [SITE + "/"]


def _string(obj: str, key: str) -> str | None:
    """The JS string literal after `key:` in one array entry ('...', "..." or `...`), unescaped."""
    m = re.search(rf"(?<![A-Za-z]){key}:(?P<q>[\"'`])(?P<v>(?:\\.|(?!(?P=q)).)*)(?P=q)", obj, re.S)
    if not m:
        return None
    v = re.sub(r"\\(.)", r"\1", m.group("v"))
    return html.unescape(v).replace("\xa0", " ").replace("’", "'")


def _entries(bundle: str) -> dict[str, str]:
    """slug → the raw text of its entry in the catalogue array."""
    start = bundle.find('[{slug:"fireside-bourbon"')
    if start < 0:
        return {}
    end = bundle.find("].map(", start)
    arr = bundle[start:end if end > 0 else start + 120000]
    parts = re.split(r'(?=\{slug:")', arr)
    out = {}
    for p in parts:
        m = re.match(r'\{slug:"([^"]+)"', p)
        if m:
            out[m.group(1)] = p
    return out


def _proof(entry: str) -> float | None:
    cur = _string(entry, "currentRelease")
    for t in (cur, _string(entry, "proof")):
        if t:
            m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", t, re.I)
            if m:
                return float(m.group(1))
    return None


def _age(entry: str, desc: str) -> float | None:
    cur = _string(entry, "currentRelease") or ""
    m = re.match(r"(\d{1,2})\s*year", cur, re.I)
    if m:
        return float(m.group(1))
    text = re.sub(r"[A-Z][A-Za-z ]+: \"[^\"]*\"", " ", desc)  # a quoted review is not the maker's statement
    m = re.search(r"\b(\d{1,2}|" + "|".join(_NUM) + r")[- ]years?[- ]old\b", text, re.I)
    if m:
        v = m.group(1).lower()
        return float(v) if v.isdigit() else float(_NUM[v])
    return None


def _mash(desc: str) -> str | None:
    m = re.search(r"((?:\d{1,2}(?:\.\d)?\s*%\s*[A-Za-z][A-Za-z -]*?)(?:\s*(?:,|/|and)\s*(?:and\s+)?\d{1,2}(?:\.\d)?\s*%\s*[A-Za-z][A-Za-z -]*?){1,})\s*(?:mash\s?bill|\)|\.|;|,|$)", desc)
    if not m:
        return None
    parts = re.findall(r"(\d{1,2}(?:\.\d)?)\s*%\s*([A-Za-z][A-Za-z -]*?)(?=\s*(?:,|/|and\b|$))", m.group(1))
    return ", ".join(f"{p}% {g.strip().title()}" for p, g in parts) or None


def _image(entry: str, bundle: str) -> str | None:
    m = re.search(r"localImage:([A-Za-z_$][\w$]*)\b(?!\.)", entry)
    if not m:
        return None
    v = re.search(rf"[,;\s]{re.escape(m.group(1))}=\"(/assets/[^\"]+)\"", bundle)
    return SITE + v.group(1) if v else None


def parse(url: str, page: str) -> list[BottlingRecord] | None:
    if "/assets/index-" not in url:
        return None
    entries = _entries(page)
    out = []
    for slug, (expression, aliases, class_raw) in REFILE.items():
        entry = entries.get(slug)
        if entry is None:
            continue
        name = f"Fireside {expression}" if expression else "Fireside Bourbon"
        desc = _string(entry, "description") or ""
        malt = "single malt" in class_raw.lower()
        out.append(BottlingRecord(
            brand_family="Fireside", expression=expression, name=name, source_url=f"{SITE}/spirits/{slug}",
            proof=_proof(entry), age_years=(a := _age(entry, desc)), age_label=(f"{int(a)} yr" if a else None),
            class_raw=class_raw,
            mash_raw=None if malt else _mash(desc),  # the malt recipes name wheat/malts, which mash_style() would misread
            description=desc[:600] or None, image_url=_image(entry, page),
            aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
        ))
    return out
