"""lexingtonbrewingco.com (Lexington Brewing & Distilling Co., Alltech — Town Branch Distillery, Lexington KY).
Town Branch's own domain (townbranch.com) now belongs to an apartment complex, lexingtonbrewing.com is a GoDaddy
listing, and kentuckyale.com (the distillery's old site) is a dead host that 302s to this one; the real maker site
is lexingtonbrewingco.com (WordPress/Avada, Yoast sitemap, robots allows all). Pearse Lyons' Irish whiskeys, Ha'Penny
and Mil gin and Bluegrass Sundown share the "Whiskey & Spirits" page; only the Town Branch pages are read.

Each product page ends its copy with a fixed block — `Proof| 90| Alc/Vol| 45%| Released In| 2012` — which is the
bottling's own statement. Three pages state the figure another way and are read specially:
* True Cask says "Varies by Batch" but prints a BATCH HISTORY table (Batch #001 … #011, one proof each): the
  highest-numbered batch is the current one and supplies the proof (Booker's convention).
* Imperium prints "cask strength" in the block but an "Imperium Release History" (MMXXIV 96.0, MMXXV 105.0,
  MMXXVI 115.1) in the header; the page title still says MMXXIV. The three years are one annual bottling, so the
  newest year supplies proof and age range ("6-9 Years-Old" is a display label, not an age) and the seed's
  per-year row (Imperium MMXXV) is renamed Imperium.
* The three Single Barrel Reserve pages and the 11yr Cask Strength malt say "Varies by Batch": no proof, so they
  confirm nothing (and are not inserted); the seed's 100 for Single Barrel Reserve Rye is a guess the maker does
  not make.
Age comes only from the title ("7yr", "15yr"); the flagship, True Cask and Rye are "non-age-stated ... averaging
about seven years", which is NAS plus an average, not an age. The 11yr Sherry Cask malt is nav-listed but its link
leads to the Sherry Cask Finished *Bourbon* page (the heading names the bottling, so the bourbon is read). The
17yr Archive Series page still reads "Only XXX bottles", a draft placeholder, but states 17 years and bottled-in-bond
100 proof like its siblings. Mash bills print as "72% Corn / 15% Rye / 13% Malted Barley" or "Blended mash bills"."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Town Branch"  # the maker row and every seed row say Town Branch; the operator is Lexington Brewing & Distilling Co. (Alltech)
DELAY = 6
SITEMAP = "https://lexingtonbrewingco.com/page-sitemap.xml"
IMAGE_PREFIX = "https://lexingtonbrewingco.com/"
CATALOG_FAMILIES = ["Town Branch"]
PRODUCER_BY_FAMILY = {}
ROOT = "https://lexingtonbrewingco.com/whiskey-spirits/"

BOURBON = "Kentucky Straight Bourbon Whiskey"
RYE = "Kentucky Straight Rye Whiskey"
MALT = "Kentucky Single Malt Whiskey"

# page path (under /whiskey-spirits/) → (expression or None for the flagship, aliases, class_raw)
REFILE = {
    "town-branch/town-branch-kentucky-straight-bourbon-whiskey": (None, ["Town Branch Kentucky Straight Bourbon"], BOURBON),
    "town-branch/town-branch-true-cask-kentucky-straight-bourbon-whiskey": ("True Cask", [], BOURBON + " Cask Strength"),
    "town-branch/town-branch-wheated-bourbon-whiskey": ("6 Year Wheated", ["Town Branch 6 Year Wheated Bourbon"], BOURBON),
    "town-branch-maple-barrel-stout-bourbon": ("Maple Barrel Stout Finished", ["Town Branch Maple Barrel Stout Finished Bourbon"], BOURBON),
    "town-branch/town-branch-imperium-bourbon-whiskey": ("Imperium", ["Town Branch Imperium MMXXV", "Town Branch Imperium MMXXIV", "Town Branch Imperium MMXXVI"], BOURBON + " Cask Strength"),
    "town-branch/town-branch-sherry-cask-finished-bourbon-whiskey": ("Sherry Cask Finished", ["Town Branch Sherry Cask Finished Bourbon"], BOURBON),
    "town-branch/town-branch-small-batch-straight-rye-whiskey": ("Small Batch Rye", ["Town Branch Small Batch Straight Rye", "Town Branch Kentucky Straight Rye"], RYE),
    "town-branch-overproof-kentucky-straight-whiskey": ("Overproof", ["Town Branch Overproof Kentucky Straight Whiskey"], "Kentucky Straight Whiskey, a blend of straight bourbons and straight rye"),
    "town-branch/town-branch-7yr-kentucky-single-malt-whiskey": ("7 Year Kentucky Single Malt", ["Town Branch 7yr Kentucky Single Malt Whiskey"], MALT),
    "town-branch/town-branch-15yr-bib-single-malt-whiskey": ("15 Year Bottled-in-Bond Kentucky Single Malt Archive Series", ["Town Branch Bottled-in-Bond Kentucky Single Malt Archive Series"], MALT + " Bottled in Bond"),
    "town-branch/town-branch-16yr-bottled-in-bond-kentucky-single-malt-whiskey": ("16 Year Bottled-in-Bond Kentucky Single Malt Archive Series", [], MALT + " Bottled in Bond"),
    "town-branch/town-branch-17yr-bottled-in-bond-kentucky-single-malt-whiskey-2": ("17 Year Bottled-in-Bond Kentucky Single Malt Archive Series", [], MALT + " Bottled in Bond"),
    "town-branch/town-branch-single-barrel-reserve-bourbon-whiskey": ("Single Barrel Reserve Bourbon", [], BOURBON + " Single Barrel Cask Strength"),
    "town-branch/town-branch-single-barrel-reserve-rye-whiskey": ("Single Barrel Reserve Rye", [], RYE + " Single Barrel Cask Strength"),
    "town-branch/town-branch-single-barrel-reserve-kentucky-single-malt-whiskey": ("Single Barrel Reserve Kentucky Single Malt", [], MALT + " Single Barrel Cask Strength"),
    "town-branch/town-branch-11yr-cask-strength-kentucky-single-malt-whiskey": ("11 Year Cask Strength Kentucky Single Malt", [], MALT + " Cask Strength"),
}
FINISH = {
    "Maple Barrel Stout Finished": "Kentucky Maple Barrel Stout Barrels",
    "Sherry Cask Finished": "Oloroso Sherry Barrels",
}
NO_MASH = {"Imperium"}  # two blended recipes printed as codes ("50% (72C | 15R | 13MB) + 50% (70C | 22W | 8MB)")
CORE = {None, "True Cask", "6 Year Wheated", "Small Batch Rye", "Overproof", "7 Year Kentucky Single Malt"}
RARITY = [(r"archive series|11 year", "lottery"), (r"imperium|small batch rye|single barrel", "allocated"),
          (r"maple barrel|sherry cask", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [ROOT + p for p in REFILE]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _text(frag: str | None) -> str | None:
    t = re.sub(r"\s+", " ", (frag or "").replace("|", " ")).strip(" |")
    return t or None


def _image(page: str) -> str | None:
    for m in re.finditer(r'<img[^>]*(?:data-orig-src|src)="(https://lexingtonbrewingco\.com/wp-content/uploads/[^"]+\.(?:png|jpe?g))"[^>]*class="[^"]*img-responsive', page):
        if "Seals" not in m.group(1):
            return m.group(1)
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    path = url.replace(ROOT, "")
    if path not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[path]
    name = f"Town Branch {expression}" if expression else "Town Branch"
    own = _flat(page)
    title_m = re.search(r"Whiskey & Spirits\| » \|(?: Town Branch\| » \|)? ([^|]+)\|", own)
    title = (title_m.group(1) if title_m else "").replace("®", "").strip()
    body = own.split("Home| » ", 1)[-1].split("only ships spirits", 1)[0]  # the page's own copy, not the nav above it
    blk = re.search(r"area\.\| Proof\| ([^|]*)\| Alc/Vol\| ([^|]*)\|", own)

    proof = None
    if blk:
        pm = re.fullmatch(r"(\d{2,3}(?:\.\d+)?)", blk.group(1).strip())
        proof = float(pm.group(1)) if pm else None
    years_text = age_text = None
    if expression == "True Cask":
        batches = re.findall(r"Batch #(\d+)\| (\d{2,3}(?:\.\d+)?) proof", own)
        if batches:
            proof = float(max(batches, key=lambda b: int(b[0]))[1])
    if expression == "Imperium":
        rel = re.findall(r"(MMXX[IVX]+) \((\d{4})\) \| (\d{2,3}(?:\.\d+)?) Proof \|[^|]*\| ([^|]+)\|", own)
        if rel:
            latest = max(rel, key=lambda r: int(r[1]))
            proof, age_text = float(latest[2]), latest[3]

    years, label = age(age_text) if age_text else (None, None)
    tm = re.search(r"\b(\d{1,2})\s*yr\b", f"{title} {expression or ''}", re.I) or re.search(r"\b(\d{1,2}) Year\b", expression or "")
    if tm:  # age from the bottling's own title only
        years, label = float(tm.group(1)), f"{tm.group(1)} yr"
    elif re.search(r"non-age-stated", body, re.I):
        years, label = None, "NAS"

    mash_raw = None
    if expression not in NO_MASH:
        mm = re.search(r"Mash Bill:\s*\|?\s*(.*?)(?:\|\s*(?:Buy Now\|\s*)?Product Finder|$)", body)
        if mm:
            raw = re.split(r",\s*finished", mm.group(1))[0].strip(" |")
            # "72% Corn | 15% Rye | 13% Malted Barley" / "72% Corn / 15% Rye / ..." → "72% Corn, 15% Rye, ..."
            mash_raw = re.sub(r"\s*[|/]\s*", ", ", raw) if re.search(r"\d\s*%", raw) else None

    pitch = _text(re.split(r"Mash Bill:", body.split(title, 1)[-1] if title else body)[0][:900])

    return BottlingRecord(
        brand_family="Town Branch", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, finish=FINISH.get(expression),
        description=pitch, image_url=_image(page), aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
