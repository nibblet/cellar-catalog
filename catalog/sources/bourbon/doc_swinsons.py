"""docswhiskey.com (Doc Swinson's, Distiller's Way LLC, Ferndale WA — docswinsons.com redirects here). A
sourcer/blender: whiskey is bought from MGP (and, for a few one-offs, Dickel and an unnamed Kentucky
distillery) and finished in Washington. Squarespace; `sitemap.xml` lists the product pages (the core
lineup at the root, every Exploratory release under `/library-exploratory-cask/`); pages are 0.2–2 MB of
inline JSON, so they are read as flattened text from the page title down to "SALES RESOURCES".

Layouts (all handled by one parser):
* Core lineup (`/session-blend`, `/triple-cask-bourbon`, `/bottled-bond-rye`, `/library-blenders-cut-bourbon`,
  `/library-high-proof-triple-cask`): a "PROOF:" / "AGED:" / "MASHBILL:" block.
* Exploratory releases: usually "Batch NN-NNN | PROOF: N | PRODUCING DISTILLERY | BATCH NOTES (mash bills)",
  one block per batch **newest first**, so the first block is the current release and everything after the
  second "PROOF" label is history (the same rule Michter's Legacy pages and Barrell's batch pages use). The
  two newest pages (Samba, Funky Drummer) use a "PRODUCT SPECS" block ("Proof: 103.7 (51.85% ABV)", "Minimum
  age of batch: 9 years"). Kiona Cask's first block has no proof at all and the only proof on the page
  belongs to a *different* bottling further down (Release #4, a Dickel Cabernet cask), so it is
  NO_PROOF: listed, never confirmed from that second number.

Facts the site does not state are not guessed: an age is read only from "Minimum age of batch", an
"Aged:" / "AGED" / "Age:" field, or an explicit "N-year" / "N year" in the intro (never from the component
list "American White Oak … 5 years 10 months" or "ex-Pineau casks 9 months to 1 year 2 months", and never
from "two five-year bourbons" — a blend of unnamed-age components). Mash bills are the percentages the
page prints, grouped into the page's two blended recipes (a bill closes when it reaches 100% or a grain
repeats); Session's second bill prints "45 malted barley" (a typo for 4%) so that bill keeps only its two
stated percentages. The class is the label's ("Straight Bourbon Whiskey" / "Straight Rye Whiskey"),
never the finishing subtitle: "Rye Whiskey Finished in Rum cask solera" would read as rum to
`spirit_type()`, and "A Blend of Straight Bourbons" would read as a blend (the same call Copper & Kings
makes). `og:image` is a site-wide logo on the core pages and a banner on several Exploratory pages, so the
bottle shot is the page's own `Docs_Bottles_*` file (or Session's alt-tagged bottle); older Exploratory
pages carry only a hero photo and get no image. Solera Method Rye (Core Collection) has no page: its nav
link `/alter-ego-rye-library` 404s and only a sales-sheet PDF exists, so it is neither added nor matched.
Lost Nectar is a rum and is skipped. Past Exploratory releases (the "Whiskey Archives") are still on
the maker's site with proofs and are imported; a page that is merely sold out is still the maker's
standing statement of the bottling.

`tasting_notes` is the current release's own "TASTING NOTES" / "SENSORY NOTES" section (a plain list, or Nose / Palate /
Finish lines), read only from the first batch block so an older batch's notes are never borrowed (the 15 Year's current
batches print none; the only notes on the page are Batch 6's). A page with no such section keeps just the sentences of
its intro that say what the whiskey smells or tastes like."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Doc Swinson's"
DELAY = 6
SITEMAP = "https://www.docswhiskey.com/sitemap.xml"
IMAGE_PREFIX = "https://www.docswhiskey.com/"
CATALOG_FAMILIES = ["Doc Swinson's"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Doc Swinson's"

# path → (expression, aliases, 'bourbon'|'rye', finish as the maker's subtitle words it).
REFILE = {
    # Core lineup
    "session-blend": ("Session Bourbon", ["Doc Swinson's 5 Year Session Blend", "Doc Swinson's Session Blend", "Doc Swinson's Session Blend Straight Bourbon"], "bourbon", None),
    "triple-cask-bourbon": ("Alter Ego Triple Cask", ["Doc Swinson's Triple Cask Bourbon", "Doc Swinson's Triple Cask"], "bourbon", "Sherry & Cognac Casks"),
    "bottled-bond-rye": ("Bottled in Bond Rye", ["Doc Swinson's Bottled in Bond Straight Rye Whiskey"], "rye", None),
    "library-blenders-cut-bourbon": ("Blenders Cut", ["Doc Swinson's Blender's Cut", "Doc Swinson's Blenders Cut Bourbon", "Doc Swinson's Blender's Cut Straight Bourbon"], "bourbon", None),
    "library-high-proof-triple-cask": ("High Proof Triple Cask", ["Doc Swinson's Alter Ego High Proof Triple Cask"], "bourbon", "Sherry & Cognac Casks"),
    # Exploratory Cask Series (current)
    "library-exploratory-cask/samba": ("Exploratory Cask Samba", [], "rye", "Rum Cask Solera & Brazilian Amburana Casks"),
    "library-exploratory-cask/fruit-odyssey": ("Exploratory Cask Fruit Odyssey", [], "bourbon", "Ruby Port Casks"),
    "library-exploratory-cask/golden-hour": ("Exploratory Cask Golden Hour", [], "rye", "Rum Solera & Port Casks"),
    "library-exploratory-cask/summer-retreat": ("Exploratory Cask Summer Retreat", [], "rye", "White Port Casks"),
    "library-exploratory-cask/funky-drummer": ("Exploratory Cask Funky Drummer", [], "rye", "Jamaican Rum Casks"),
    "library-exploratory-cask/tres-amigos": ("Exploratory Cask Tres Amigos", [], "rye", "Rum & Anejo Tequila Casks"),
    # Whiskey Archives
    "library-exploratory-cask/reefer-madness": ("Exploratory Cask Reefer Madness", [], "rye", "Rum & Ex-Peated Scotch Casks"),
    "library-exploratory-cask/smoke-on-water": ("Exploratory Cask Smoke on Water", [], "rye", "Peated Scotch Quarter Casks"),
    "library-exploratory-cask/bossa-nova": ("Exploratory Cask Bossa Nova", [], "bourbon", "Amburana Casks"),
    "library-exploratory-cask/garryana": ("Exploratory Cask Forest & Fable", ["Doc Swinson's Exploratory Cask Garryana"], "bourbon", "Garryana Oak Casks"),
    "library-exploratory-cask/dos-padres": ("Exploratory Cask Dos Padres", [], "bourbon", "Anejo Tequila Casks"),
    "library-exploratory-cask/french-toasted": ("Exploratory Cask French Toasted", [], "bourbon", "Toasted French Oak Casks"),
    "library-exploratory-cask/tawny-port": ("Exploratory Cask Tawny Port", [], "bourbon", "Tawny Port Casks"),
    "library-exploratory-cask/moscatel": ("Exploratory Cask Moscatel", [], "bourbon", "Moscatel Casks"),
    "library-exploratory-cask/pineau-des-charentes": ("Exploratory Cask Pineau des Charentes", [], "bourbon", "Pineau Des Charentes Casks"),
    "library-exploratory-cask/el-cuerpo": ("Exploratory Cask El Cuerpo", [], "bourbon", "Pedro Ximenez Sherry Casks"),
    "library-exploratory-cask/la-mente": ("Exploratory Cask La Mente", [], "bourbon", "Oloroso Sherry Casks"),
    "library-exploratory-cask/l-esprit": ("Exploratory Cask L'Esprit", [], "bourbon", "Cognac Casks"),
    "library-exploratory-cask/the-forgotten-one": ("Exploratory Cask The Forgotten One", [], "bourbon", "Madeira Casks"),
    "library-exploratory-cask/15-year-bourbon": ("Exploratory Cask 15 Year", ["Doc Swinson's Exploratory Cask Series", "Doc Swinson's Cask Strength 15 Year Kentucky Bourbon"], "bourbon", None),
    "library-exploratory-cask/madeira-finished-bourbon": ("Exploratory Cask Sercial & Malmsey Madeira", [], "bourbon", "Sercial & Malmsey Madeira Casks"),
    "library-exploratory-cask/sercial-malmsey-madeira": ("Exploratory Cask Madeira", [], "bourbon", "Madeira Casks"),
    "library-exploratory-cask/kiona-cask": ("Exploratory Cask Kiona", ["Doc Swinson's Kiona Cask"], "bourbon", "Cabernet Sauvignon Casks"),
}
CORE = {"Session Bourbon", "Alter Ego Triple Cask", "Bottled in Bond Rye", "Blenders Cut"}
# The first (current) block of these pages states no proof; the proof further down is another bottling's.
NO_PROOF = {"library-exploratory-cask/kiona-cask"}
# Pages whose bottle count (stated on the page) is under 500: one to two casks.
RARITY = [(r"forgotten one|exploratory cask madeira|sercial", "lottery"),
          (r"exploratory|high proof", "allocated"),
          (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://www.docswhiskey.com/{slug}" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"[​﻿\xa0]", " ", t).replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _main(own: str) -> str:
    """The page's own content: after the last nav 'Doc's Journal' in the header, before the footer."""
    # The header menu is printed three times; the last copy ends "… Folder:| Buy Doc's| Back| Buy Online | … | Doc's Journal |".
    # (A body link can also say "Doc's Journal", so anchor on the menu's own last "Back|", not the last "Doc's Journal".)
    j = own[:1300].rfind("Back|")
    m = re.compile(r"Doc's Journal\s*\|").search(own, j) if j >= 0 else None
    start = m.end() if m else 0
    end = own.find("SALES RESOURCES", start)
    return own[start:end if end > 0 else None].strip(" |")


_PROOF_LABEL = re.compile(r"\bPROOF\b\s*\|?\s*:", re.I)


def _mash(block: str) -> str | None:
    bills, cur, total = [], [], 0.0
    for pct, grain in re.findall(r"(\d+(?:\.\d+)?)\s*%\s*(corn|rye|wheat|malted barley)", block, re.I):
        g = grain.title()
        if g in {x[1] for x in cur} or total >= 99.5:
            bills.append(cur); cur, total = [], 0.0
        cur.append((pct, g)); total += float(pct)
    if cur:
        bills.append(cur)
    out = [", ".join(f"{p}% {g}" for p, g in b) for b in bills if len(b) >= 2]  # a lone "21% Rye" in prose is not a recipe
    return " / ".join(dict.fromkeys(out)) or None


def _age(intro: str, block: str) -> tuple[float | None, str | None]:
    for pat in (r"minimum age of batch:?\s*\|?\s*(\d{1,2})\s*years?",
                r"\bAGED?\b\s*\|?\s*:?\s*\|?\s*(\d{1,2})\s*years?",
                r"\b(\d{1,2})[- ]year\b"):
        m = re.search(pat, block if pat != r"\b(\d{1,2})[- ]year\b" else intro, re.I)
        if m:
            y = float(m.group(1))
            return y, f"{int(y)} yr"
    return None, None


_NOTES_LABEL = re.compile(r"^(?:tasting|sensory) notes\s*:?$", re.I)
_SUBLABEL = re.compile(r"^(nose|aroma|palate|finish)\s*(?:[:\-–]\s*(?:-\s*)?(.*))?$", re.I)
_SENSORY = re.compile(r"\b(?:notes of|aromas of|aromatics|palate|on the nose)\b", re.I)


def _is_label(seg: str) -> bool:
    """Where a plain notes list ends: an upper-case heading ("HOW TO ENJOY", "AWARDS:"), the next batch, or page chrome."""
    letters = re.sub(r"[^A-Za-z]", "", seg)
    if len(letters) >= 5 and seg.upper() == seg and not _SUBLABEL.match(seg):
        return True
    return seg.startswith(("Batch ", "Exploratory Cask Release", "←", "→", "Find ", "Previous", "Written By"))


def _tasting(block: str, intro: str) -> str | None:
    segs = [x.strip() for x in block.split("|") if x.strip()]
    for i, seg in enumerate(segs):
        if not _NOTES_LABEL.match(seg):
            continue
        body = segs[i + 1:]
        if body and _SUBLABEL.match(body[0]):
            # Nose / Palate / Finish: each label owns one value (inline, or the next segment). The paragraph after the
            # last one can be a "try our other bottles" cross-sell, so nothing past the last value is read.
            parts, k = [], 0
            while k < len(body) and _SUBLABEL.match(body[k]):
                m = _SUBLABEL.match(body[k])
                value, k = (m.group(2), k + 1) if m.group(2) else (body[k + 1].lstrip("- ") if k + 1 < len(body) else "", k + 2)
                if value.strip():
                    parts.append(f"{m.group(1).title()}: {value.strip().rstrip('. ')}.")
            return " ".join(parts)[:900] or None
        plain = []
        for x in body:
            if _is_label(x):
                break
            plain.append(x)
        text = re.sub(r"\s+", " ", " ".join(plain)).strip()
        return (text.rstrip(".") + ".")[:900] if text else None  # empty: this batch printed no notes (a later batch's are not ours)
    prose = _text(re.sub(r"^.*?\bWritten By\b[^|]*\|[^|]*\|", "", intro)) or ""
    keep = [x for x in re.split(r"(?<=[.!?])\s+", prose) if _SENSORY.search(x)]
    return " ".join(keep)[:900] or None


def _image(page: str) -> str | None:
    for m in re.finditer(r"<img[^>]*>", page):
        t = m.group(0)
        src = re.search(r'data-src="([^"]+)"', t)
        alt = re.search(r'alt="([^"]*)"', t)
        if src and (re.search(r"Docs_Bottles", src.group(1)) or (alt and re.search(r"(?i)session blend straight bourbon", alt.group(1)))):
            return html.unescape(src.group(1))
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.split("docswhiskey.com/", 1)[-1].strip("/")
    if slug not in REFILE:
        return None
    expression, aliases, kind, finish = REFILE[slug]
    name = f"{FAMILY} {expression}"
    main = _main(_flatten(page))
    marks = [m.start() for m in _PROOF_LABEL.finditer(main)]
    block = main[:marks[1]] if len(marks) > 1 else main     # the current release: up to the second batch's PROOF label
    intro = main[:marks[0]] if marks else main

    proof = None
    if slug not in NO_PROOF and marks:
        pm = re.match(r"\bPROOF\b\s*\|?\s*:\s*\|?\s*(\d{2,3}(?:\.\d+)?)", main[marks[0]:], re.I)
        proof = float(pm.group(1)) if pm else None
    if slug in NO_PROOF:
        block = main[:marks[0]] if marks else main
        intro = block

    years, label = (None, None) if slug in NO_PROOF else _age(intro, block)
    mash_raw = None if slug in NO_PROOF else _mash(block)
    rye = kind == "rye"
    class_raw = "Straight Rye Whiskey" if rye else "Straight Bourbon Whiskey"
    desc = _text(re.sub(r"^.*?\bWritten By\b[^|]*\|[^|]*\|", "", intro)[:900])
    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=f"https://www.docswhiskey.com/{slug}",
        proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw,
        mash_style="rye" if rye else None, description=(desc or "")[:500] or None, tasting_notes=_tasting(block, intro), image_url=_image(page), finish=finish,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
