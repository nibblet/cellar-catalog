"""fourgatewhiskey.com (Four Gate Whiskey Company, Louisville — a sourcing/blending house, not a distiller;
a Duda site, static HTML, no cart). Every numbered batch has its own page, its own name and its own proof, so
each is its own bottling (a Foundation re-release is a different proof and age, a Split Stave rye is not the
bourbon): the record is "Batch N <Name>", the number being what tells Foundation 3 from Foundation 5.
Slugs are NOT reliable (batch-30-triple-oak is Batch 29, batch-22-barossa-creek is Indiana Foundation 10yr,
batch-23-barossa-creek2 is Barossa Creek, copy-of-batch-29-triple-oak is the Japanese Mizunara): the page's own
heading names it, and REFILE maps slug → that heading.

Facts come from the page's own spec block / prose, nothing else on the site:
  * proof: the first "N Proof" in the copy, else "ABV%/Proof: 61.7%/123.4º" (Batch 1), else "The proof was
    122.7" (Eagle Thief). Batch 13's block prints "1132 Proof" (a typo) but its prose says "113 proof"; the
    regex refuses a digit before the number so the prose figure is the one read.
  * age: only from a stated phrase. AGE_STATEMENTS names, per page, the exact phrase the page prints; the
    parser re-checks the phrase is on the page and reads nothing otherwise. Component ages of a blend ("5.5
    and 12 year") and "age at re-barreling" are not a bottling age, so those pages carry none. Months are real
    ("9 Year, 9 Month Old" = 9.75).
  * mash bill: a recipe only when the page prints exactly one; a blend of different mash bills has none.
  * the flagship (Split Stave by Kelvin) and the two 10-year single-barrel programs state no proof.
The bottle shot is the second distinct image on the page (the first is a site-wide texture).
tasting_notes is the page's own NOSE / TASTE / FINISH block (the "?" placeholders on unreleased-notes pages are dropped)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import titlecase

PRODUCER = "Four Gate Whiskey Company"
DELAY = 6
SITEMAP = "https://www.fourgatewhiskey.com/sitemap.xml"
IMAGE_PREFIX = "https://irp.cdn-website.com/"
CATALOG_FAMILIES = ["Four Gate Whiskey Company"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Four Gate Whiskey Company"
BASE = "https://www.fourgatewhiskey.com/"

BOURBON = "Kentucky Straight Bourbon Whiskey"
RYE = "Straight Rye Whiskey"
BLEND = "Blend of Straight Bourbon and Straight Rye Whiskeys"

# slug → (expression, aliases, class statement). None expression is never used: the flagship is Split Stave.
REFILE = {
    "batch-1-kelvin-collaboration": ("Batch 1 Kelvin Collaboration", [], BOURBON),
    "batch-2-outer-orbit-loop": ("Batch 2 Outer Orbit Loop", [], BOURBON),
    "batch-3-foundation": ("Batch 3 Foundation", ["Four Gate Foundation", "Foundation"], BOURBON),
    "batch-4-split-stave-by-kelvin": ("Batch 4 Split Stave by Kelvin", [], BOURBON),
    "batch-5-foundation": ("Batch 5 Foundation", [], BOURBON),
    # The catalog's seed "Four Gate The Kelvin Collaboration" is 126.4 proof, 12 years, which is Batch 6
    # (Kelvin Collaboration II) exactly; Batch 1 is 123.4 and states no total age.
    "batch-6-kelvin-collaboration-ii": ("Batch 6 Kelvin Collaboration II", ["Four Gate The Kelvin Collaboration"], BOURBON),
    "batch-7-river-kelvin-rye": ("Batch 7 River Kelvin Rye", ["Four Gate River Kelvin Rye"], RYE),
    "batch-8-tennessee-foundation": ("Batch 8 Tennessee Foundation", [], "Tennessee Straight Bourbon Whiskey"),
    "batch-9-andalusia-key": ("Batch 9 Andalusia Key", [], BOURBON),
    "batch-10-split-stave-by-kelvin-rye": ("Batch 10 Split Stave by Kelvin Rye", [], RYE),
    "batch-11-ruby-rye-springs": ("Batch 11 Ruby Rye Springs", [], RYE),
    "batch-12-kelvin-collaboration-ii": ("Batch 12 Kelvin Collaboration III", [], BOURBON),
    "batch-13-river-kelvin-rye": ("Batch 13 River Kelvin Rye", [], RYE),
    "batch-14-old-sherry-pike": ("Batch 14 Old Sherry Pike", [], BOURBON),
    "newpage3120629e": None,  # Batch 15.1 / 15.2 / 15.3, the Bluegrass Trilogy: three bottlings on one page (TRILOGY)
    "batch-16-rye-downunder": ("Batch 16 Rye DownUnder", [], RYE),
    "newpage": ("Batch 17 Split Stave by Kelvin Brrye", [], BLEND),
    "batch-18-saint-charente": ("Batch 18 Saint Charente", [], BOURBON),
    "batch-19-kelvin-collaboration-iiii": ("Batch 19 Kelvin Collaboration IIII", ["Four Gate Batch 19 Kelvin Collaboration IV"], BLEND),
    "batch-20-four-by-four": ("Batch 20 Four By Four", [], BOURBON),
    "batch-21-port-perry-perry": ("Batch 21 Port Perry Perry", [], RYE),
    "batch-22-barossa-creek": ("Batch 22 Indiana Foundation 10 Year", [], "Indiana Straight Bourbon Whiskey"),
    "batch-23-barossa-creek2": ("Batch 23 Barossa Creek", [], BLEND),
    "batch-24-brbn-downunder": ("Batch 24 BRBN Downunder", [], "Indiana Straight Bourbon Whiskey"),
    "batch-25-andalusia-key-rye": ("Batch 25 Andalusia Key Rye", [], RYE),
    "batch-26-andalusia-key-rye2": ("Batch 26 Andalusia Key II", [], BOURBON),
    "batch-27-split-stave-by-kelvin-rye2": ("Batch 27 Split Stave by Kelvin Rye", [], RYE),
    "batch-28-kelvin-v": ("Batch 28 Kelvin Collaboration V", [], BOURBON),
    # The page heading says Batch 29; the maker's menu links /batch-30-triple-oak. A Kentucky Straight Whiskey
    # (aged first in used cooperage), so the page itself says it is not a bourbon.
    "batch-30-triple-oak": ("Batch 29 Triple Oak", [], "Kentucky Straight Whiskey"),
    "tkc6-kelvin-collaboration-vi": ("Kelvin Collaboration VI", [], BOURBON),
    "copy-of-batch-29-triple-oak": ("Majestic Wood Japanese Mizunara", [], BOURBON),
    "mws-brazilian-ambruana": ("Majestic Wood Brazilian Amburana", [], BOURBON),
    "indiana-foundation-14yr": ("Indiana Foundation 14 Year", [], "Indiana Straight Bourbon Whiskey"),
    "kelvin-sixty": ("Kelvin Sixty", [], BOURBON),
    "eagle-thief": ("Eagle Thief", [], BOURBON),
    # The flagship has two pages (the older one is the first release, the 2023 one carries the award); neither
    # states a proof, so no row is created, but both stay listed so a future proof is picked up.
    "flagship-spit-stave-by-kelvin": ("Split Stave by Kelvin", [], BOURBON),
    "flagship-2023-split-stave-by-kelvin": ("Split Stave by Kelvin", [], BOURBON),
}
# Not crawled: foundation-10yr and river-kelvin-rye-10yr (a "small handful" of single barrels, cask strength,
# no proof — a program, not a bottling), private-select-casks (a program), blog posts.

TRILOGY = {  # sub-batch → (expression, finish), proof/bottle count read from the page
    "1": "Batch 15.1 Bluegrass Trilogy",
    "2": "Batch 15.2 Bluegrass Trilogy",
    "3": "Batch 15.3 Bluegrass Trilogy",
}

# slug → (phrase the page prints, years). The parser checks the phrase is on the page before using it.
AGE_STATEMENTS = {
    "batch-3-foundation": (r"9 Year, 9 Month Old", 9.75),
    "batch-5-foundation": (r"9 Year, 9 Month Old", 9.75),
    "batch-6-kelvin-collaboration-ii": (r"12 Year Old Kentucky Straight Bourbon finished", 12),
    "batch-7-river-kelvin-rye": (r"7 Year Old Indiana Straight Rye", 7),
    "batch-8-tennessee-foundation": (r"10 Year Old Tennessee Straight Bourbon", 10),
    "batch-13-river-kelvin-rye": (r"8 Year Old Indiana Straight Rye", 8),
    "batch-16-rye-downunder": (r"7 Year Old Indiana Straight Rye", 7),
    "batch-18-saint-charente": (r"7 year Kentucky Straight Bourbon Whiskey finished", 7),
    "batch-20-four-by-four": (r"9-Year Straight Bourbon", 9),
    "batch-21-port-perry-perry": (r"8-Year Straight Rye Whiskey", 8),
    "batch-22-barossa-creek": (r"10-Year Straight Bourbon Whiskey", 10),
    "batch-24-brbn-downunder": (r"Aged at least 6\.5 Years", 6.5),
    "batch-25-andalusia-key-rye": (r"Aged at least 7 Years", 7),
    "batch-26-andalusia-key-rye2": (r"Aged at least 7 Years, 6 Months", 7.5),
    "batch-27-split-stave-by-kelvin-rye2": (r"Aged minimum of 7 Years", 7),
    "batch-30-triple-oak": (r"aged a total of seven years, nine months", 7.75),
    "tkc6-kelvin-collaboration-vi": (r"Aged at least 9 Years", 9),
    "copy-of-batch-29-triple-oak": (r"Aged at least 7 Years 6 months", 7.5),
    "mws-brazilian-ambruana": (r"Aged at least 7 Years", 7),
    "indiana-foundation-14yr": (r"14-Year Indiana Straight bourbon", 14),
    "kelvin-sixty": (r"Aged at least 8 Years", 8),
    "eagle-thief": (r"barrel proof 12-year Kentucky Straight Bourbon", 12),
    "flagship-spit-stave-by-kelvin": (r"Aged at least 7 Years", 7),
    "flagship-2023-split-stave-by-kelvin": (r"Aged at least 7 Years", 7),
}

CORE = {"Split Stave by Kelvin"}
RARITY = [
    (r"split stave by kelvin$", "shelf"),
    (r"indiana foundation 14|eagle thief|batch (?:3|5|8) ", "lottery"),
    (r".", "allocated"),
]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + s for s in REFILE]


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t.replace("﻿", "")).strip()
    return t or None


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("﻿", "").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _own(page: str) -> str:
    """The product's own copy: after the second nav, before the press quotes and the footer."""
    t = _flatten(page)
    t = t.split("quotesArtboard")[0].split("Sip. Taste")[0].split("List of Services")[0]
    return t.split("Shop Four Gate|")[-1]


def _proof(own: str) -> float | None:
    flat = own.replace("|", " ")
    m = re.search(r"(?<![\d.])(\d{2,3}(?:\.\d)?)\s*º?\s*proof\b", flat, re.I) \
        or re.search(r"Proof:\s*[\d.]+%\s*/\s*(\d{2,3}(?:\.\d)?)", flat) \
        or re.search(r"proof was\s+(\d{2,3}(?:\.\d)?)", flat, re.I)
    return float(m.group(1)) if m else None


def _mash(own: str) -> str | None:
    flat = own.replace("|", " ")
    corn = r"(\d{1,2})\s*%\s*corn,?\s*(?:and\s*)?(\d{1,2})\s*%\s*rye,?\s*(?:and\s*)?(\d{1,2})\s*%\s*malted barley"
    found = []
    for m in re.finditer(corn, flat, re.I):
        t = tuple(int(x) for x in m.groups())
        if t not in found:
            found.append(t)
    rest = re.sub(corn, " ", flat, flags=re.I)  # a rye-only recipe beside a corn one is a bourbon/rye blend
    rye = {tuple(int(x) for x in m) for m in re.findall(r"(\d{1,2})\s*%\s*rye,?\s*(?:and\s*)?(\d{1,2})\s*%\s*malted barley", rest, re.I)}
    if not found and len(rye) == 1:
        a, b = next(iter(rye))
        return f"{a}% Rye, {b}% Malted Barley"
    if len(found) != 1 or rye:  # a blend of different mash bills has no single recipe
        return None
    c, r, b = found[0]
    return f"{c}% Corn, {r}% Rye, {b}% Malted Barley"


def _finish(own: str) -> str | None:
    flat = re.sub(r"\s+", " ", own.replace("|", " "))
    ms = re.findall(r"finished(?: in)? ((?:[\w'\-éáñçÉ™]+ ){0,9}?(?:casks?|barrels?))\b", flat, re.I)
    ms += re.findall(r"Finish Barrels:\s*([^|]+?)(?:\||$)", own)
    if not ms:
        return None
    f = re.sub(r"\s+(?:by|from|selected)\b.*$", "", ms[-1].strip(), flags=re.I)
    f = re.sub(r"^(?:their popular|rare)\s+", "", f, flags=re.I)
    if len(f.split()) < 2:  # "casks" alone is a stray match, not a finish
        return None
    out = re.sub(r"-([a-z])", lambda m: "-" + m.group(1).upper(), titlecase(f.replace("™", "")))
    return re.sub(r"\bPx\b", "PX", out)


def _msrp(own: str) -> float | None:
    flat = own.replace("|", " ")
    m = re.search(r"(?:MSRP|SRP)[^$]{0,25}\$\s*(\d+(?:\.\d\d)?)", flat) or re.search(r"\$\s*(\d+(?:\.\d\d)?)\s*SRP", flat)
    return float(m.group(1)) if m else None


def _image(page: str) -> str | None:
    seen = []
    for m in re.finditer(r'data-dm-image-path="([^"]+)"', page):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen[1] if len(seen) > 1 and "Logo" not in seen[1] else None  # [0] is the site-wide BLUE.png texture


def _age_label(years: float) -> str:
    whole, months = int(years), round((years - int(years)) * 12)
    if months:
        return f"{whole} yr {months} mo" if whole else f"{months} mo"
    return f"{whole} yr"


def _description(own: str) -> str | None:
    t = _text(own.split("TASTING NOTES")[0].replace("|", " "))
    # normalize.finish() reads a description for "<x> barrel finish"; Batch 3's "no matter the barrel finish we
    # choose" is the maker's philosophy, not a finish. This module reads finish itself, so drop such sentences.
    t = re.sub(r"[^.]*\b(?:cask|barrel|oak) finish(?:ed)?\b[^.]*\.?", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()[:700] or None


def _tasting(own: str) -> str | None:
    """The page's NOSE / TASTE / FINISH block, as 'Nose: ... Taste: ... Finish: ...'; '?' means the maker left it blank."""
    if "TASTING NOTES" not in own:
        return None
    flat = own.split("TASTING NOTES", 1)[1].replace("|", " ")
    parts = []
    for key, body in re.findall(r"\b(NOSE|TASTE|FINISH)\b\s*(.*?)(?=\b(?:NOSE|TASTE|FINISH)\b|$)", flat):
        body = (_text(body) or "").rstrip(" ,;")
        if len(body.strip("?. ")) > 1:
            parts.append(f"{key.title()}: {body}" + ("" if body.endswith((".", "!")) else "."))
    return " ".join(parts)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | list[BottlingRecord] | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    own = _own(page)
    img = _image(page)
    img = html.unescape(img) if img else None
    msrp, desc = _msrp(own), _description(own)

    if slug == "newpage3120629e":
        flat = own.replace("|", " ")
        out = []
        flat = flat.split("TRILOGY BATCHES", 1)[-1]
        for m in re.finditer(r"\b15\.([123])\s+(.*?)\s+[\d,]+ Bottles,\s*(\d{2,3}\.\d)\s*Proof", flat):
            sub, blurb, proof = m.group(1), m.group(2), float(m.group(3))
            expr = TRILOGY[sub]
            fm = re.search(r"[Ff]inished in (.*? Casks?)", re.sub(r"\s+", " ", blurb))
            out.append(BottlingRecord(
                brand_family=FAMILY, expression=expr, name=f"Four Gate {expr}", source_url=BASE + slug, proof=proof,
                class_raw=BOURBON, description=desc, image_url=img, finish=titlecase(fm.group(1)) if fm else None,
                is_core_range=False,
            ))
        return out or None

    expression, aliases, class_raw = REFILE[slug]
    name = f"Four Gate {expression}"
    years = label = None
    if slug in AGE_STATEMENTS:
        phrase, y = AGE_STATEMENTS[slug]
        if re.search(phrase, own.replace("|", " "), re.I):
            years, label = float(y), _age_label(float(y))
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=BASE + slug, proof=_proof(own),
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=_mash(own), description=desc,
        tasting_notes=_tasting(own), image_url=img, finish=_finish(own), msrp_usd=msrp, aliases=sorted(set(aliases) - {name}),
        is_core_range=expression in CORE,
    )
