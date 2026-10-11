"""oldelk.com (Old Elk Distillery, Fort Collins — Squarespace; oldelkdistillery.com redirects here).
Re-checked 2026-10-11 after being parked ("no proof anywhere"): the site has been rebuilt and every
bottling now carries a structured spec line under its title — `<CLASS> · N PROOF · N% ALC/VOL` — on four
nav-linked pages:
  /lineup                          core: Slow Cut Bourbon, Slow Cut Wheated Bourbon, Straight Wheat Whiskey
                                   (/whiskeys is the same page — it redirects here)
  /10-year-lineup                  10 Year Straight Bourbon / Straight Wheated Bourbon / Straight Wheat Whiskey
  /cask-finish-series              Port Cask Finish Bourbon, Cognac Cask Finish Wheat, Cigar Cut Punch Cut
  /folds-of-honor-american-whiskey the Folds of Honor blended American whiskey (limited)
Not read: /specialty-whiskey (still served, but no longer in the nav — it carries an older Punch Cut at
111.7 proof against the nav-linked Cask Finish page's 109.1, i.e. history, not a listing — and the only
Infinity Blend), /10-year-collection and /new-home (marketing landing pages), /cigar-cut-blend (prose, no
proof), /single-barrel and /faqs (404 although the footer links them).

The mash bills are baked into images (`WEB_10YR+MASHBILL-0N.png`, and the same file is reused on /lineup
for the Slow Cut pages) — not machine-readable, never OCR'd. Mash is read only where the copy states a
percentage in prose ("a mash bill of 96 percent soft red winter wheat and four percent malted barley").
Age: stated only on the wheat whiskeys and the 10 Years ("aged for six years", "10 YEAR" in the title);
the Cask Finish pages state the base whiskey's age ("ORIGINAL AGE 5–6 YEARS", "aged for six years before
receiving an additional six months to one year of finishing"), which `normalize.age()` reads as a range
label or as the base age respectively — a finish adds only months to a base the maker names, and the page
says "original age". Punch Cut: "AGED 6–8 YEARS" is a display range, never `age_years`.
The page-level block is `<title> | <title> | <class> | · | N PROOF | · | N% ALC/VOL | <copy>` — the title
shows twice (tab, then block) — so each block is found from its proof outward."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, titlecase

PRODUCER = "Old Elk"
DELAY = 6
SITEMAP = "https://www.oldelk.com/sitemap.xml"
IMAGE_PREFIX = "https://www.oldelk.com/"
CATALOG_FAMILIES = ["Old Elk"]
PRODUCER_BY_FAMILY = {}

PAGES = ["lineup", "10-year-lineup", "cask-finish-series", "folds-of-honor-american-whiskey"]

# page → {heading (upper-cased, as printed in the tab/title) → (expression, aliases, bottle-image alt)}.
REFILE = {
    "lineup": {
        "SLOW CUT BOURBON": ("Slow Cut Bourbon", ["Old Elk Blended Bourbon"], "Old Elk Slow Cut Bourbon"),
        "SLOW CUT WHEATED BOURBON": ("Slow Cut Wheated Bourbon", ["Old Elk Wheated Straight Bourbon"], "Old Elk Slow Cut Wheated Bourbon"),
        "STRAIGHT WHEAT WHISKEY": ("Straight Wheat Whiskey", [], "Old Elk Straight Wheat Whiskey"),
    },
    "10-year-lineup": {
        "10 YEAR STRAIGHT BOURBON": ("10 Year Straight Bourbon", ["Old Elk 10 Year Bourbon"], "Old Elk 10 Year Straight Bourbon"),
        "10 YEAR STRAIGHT WHEATED BOURBON": ("10 Year Straight Wheated Bourbon", ["Old Elk 10 Year Wheated"], "Old Elk 10 Year Straight Wheated Bourbon"),
        "10 YEAR STRAIGHT WHEAT WHISKEY": ("10 Year Straight Wheat Whiskey", [], "Old Elk 10 Year Straight Wheat Whiskey"),
    },
    "cask-finish-series": {
        "PORT CASK FINISH BOURBON": ("Port Cask Finish Bourbon", ["Old Elk Port Cask Finish"], "Old Elk Port Cask Finish Bourbon"),
        "COGNAC CASK FINISH WHEAT": ("Cognac Cask Finish Wheat", [], "Old Elk Cognac Cask Finish Wheat Whiskey"),
        "CIGAR CUT - PUNCH CUT": ("Cigar Cut Punch Cut", [], "Old Elk Cigar Cut Punch Cut"),  # the tab says "CIGAR CUT PUNCH CUT"
    },
    "folds-of-honor-american-whiskey": {
        "FOLDS OF HONOR": ("Folds of Honor", [], "Old Elk Folds of Honor American Whiskey"),
    },
}
# The core lineup, the permanent 10 Year trio and the standing Cask Finish pair; Punch Cut is "Vol. 1"
# of an evolving blend and Folds of Honor is a limited charity release.
CORE = {"Slow Cut Bourbon", "Slow Cut Wheated Bourbon", "Straight Wheat Whiskey", "10 Year Straight Bourbon",
        "10 Year Straight Wheated Bourbon", "10 Year Straight Wheat Whiskey", "Port Cask Finish Bourbon", "Cognac Cask Finish Wheat"}
RARITY = [(r"folds of honor|punch cut", "limited"), (r".", "shelf")]
MASH_BILLS = {}

# A percentage recipe the copy states outright (the whiskey is named for its grain, so the rest is malted barley).
MASH_PROSE = {
    "Straight Wheat Whiskey": "96% Wheat, 4% Malted Barley",
    "10 Year Straight Wheat Whiskey": "96% Wheat",
}

BLOCK = re.compile(r"([^|]+?)\s*\|\s*·\s*\|\s*(\d{2,3}(?:\.\d+)?)\s*PROOF\s*\|\s*·\s*\|\s*(\d{2}(?:\.\d+)?)%\s*ALC/VOL\s*\|?\s*", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"https://www.oldelk.com/{p}" for p in PAGES]


def _flat(fragment: str) -> str:
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _images(page: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"<img\b[^>]*>", page):
        tag = m.group(0)
        src = re.search(r'\bdata-src="([^"]+)"', tag) or re.search(r'\bsrc="([^"]+)"', tag)
        alt = re.search(r'\balt="([^"]*)"', tag)
        if src and alt and alt.group(1) and html.unescape(alt.group(1)).lower() not in out:
            u = html.unescape(src.group(1))
            out[html.unescape(alt.group(1)).lower()] = ("https:" + u) if u.startswith("//") else u
    return out


def parse(url: str, page: str) -> list[BottlingRecord]:
    slug = url.rstrip("/").split("/")[-1]
    table = REFILE.get(slug)
    if not table:
        return []
    text = _flat(page)
    images = _images(page)
    blocks = list(BLOCK.finditer(text))
    out = []
    for i, m in enumerate(blocks):
        before = [s.strip() for s in text[: m.start()].split("|") if s.strip()] + [m.group(1).strip()]
        # the printed class is the segment right before the dot; the title is one of the 3 segments leading up to it
        cls_raw = m.group(1).strip()
        heading = next((s.upper() for s in reversed(before[-4:-1]) if s.upper() in table), None)
        if heading is None:
            continue
        expression, aliases, imgalt = table[heading]
        nxt = blocks[i + 1].start() if i + 1 < len(blocks) else len(text)
        seg = text[m.end():nxt]
        body = re.split(r"\|\s*TASTING NOTES", seg, 1)[0]
        copy = re.split(r"\|\s*(?:FIND NEAR YOU|PRE-ORDER)", body, 1)[0]
        proof = float(m.group(2))
        years, label = age(f"{heading.title()} {body}")
        if expression == "Cigar Cut Punch Cut":  # the title has no age; the 6–8 yr range is the blend's own statement
            years, label = age(body)
        desc = re.sub(r"\s*\|\s*", " ", copy).strip() or None
        if expression == "Cigar Cut Punch Cut" and desc:
            # A blend of four differently-finished components has no one finish; the second sentence
            # ("finished in a distinct secondary cask") would read as a finish called "A Distinct Secondary Cask".
            desc = desc.split(". ", 1)[0].rstrip(".") + "."
        out.append(BottlingRecord(
            brand_family="Old Elk", expression=expression, name=f"Old Elk {expression}",
            source_url=url, proof=proof, age_years=years, age_label=label,
            class_raw=titlecase(cls_raw.lower()), mash_raw=MASH_PROSE.get(expression), description=desc,
            image_url=images.get(imgalt.lower()), aliases=sorted(set(aliases) - {f"Old Elk {expression}"}),
            is_core_range=expression in CORE,
        ))
    return out
