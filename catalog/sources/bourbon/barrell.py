"""barrellbourbon.com (Barrell Craft Spirits, Louisville — a blender, not a distiller). A Wix site whose
"Core Products" (Batch Bourbon, Batch Rye, Foundation) and "Limited Releases" (Gold Label, Gray Label,
New Year, the dormant Infinite Barrel Project) pages each embed the CURRENT release's stats followed by
a full history of every past batch on the same page, oldest last — the current one is whichever text
comes before the *second* "N proof" mention (single-release pages like Foundation and Gold Label Dovetail
have only one). Age is stated two ways ("Matured for N years" on Gold/Gray Label, "N-years-old" on the
generic Whiskey line) or not at all on the annual Batch Bourbon/Rye/New Year blends, whose intro prose
names each component's own age ("12 years old", "5 and 6-year-old barrels") with no aggregate figure —
those per-component ages are stripped out (via the BLEND COMPONENTS...DERIVED MASH BILL span) before
age-matching so they can't be mistaken for the batch's own age, and a lone "N-year(s)-old" is trusted only
when it is the sole such mention (two or more means it's a component list, not a statement). Seagrass,
Dovetail, Vantage, Armida, Private Release and the Cask Finish Series landing page state no proof/age/mash
anywhere — flavor notes and awards only — so they're still crawled (confirming the bottling is still live,
same as any other page) but always parse to a proof-less record; the one-off Cask Finish Series flavors
themselves (Armagnac, P.X. Sherry, Mizunara, ...) are each their own page one level down and are not
crawled, mirroring the Bardstown Collaborative Series exclusion — too many one-off finishes to be "most
available", and the landing page already stands in for the series as a whole. The bottle shot is the first
tall (portrait) wixstatic image whose filename's own batch/release number agrees with the current text's
"Batch N" — pages with no batch number in the text (Foundation, the Gold/Gray Label finishes) accept the
first tall image unconditionally, and a numbered mismatch (the Whiskey page's hero art still shows the
prior Batch 004 while the text has moved to Batch 005) means no image rather than a wrong one.

`tasting_notes` is the CURRENT release's own Nose / Palate / Finish (the first such block on the page; the batch history below it
is older releases, and the Cask Finish Series landing page covers several different finishes, so those pages get None). Each
part is cut to its first sentences (about 300 characters) so the three fit one note; the Appearance line, the intro paragraph
over it, the "with a splash of water" paragraph and the press quotes are not read."""
from __future__ import annotations

import html
import re
import urllib.parse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Barrell"
DELAY = 6
SITEMAP = "https://www.barrellbourbon.com/pages-sitemap.xml"
IMAGE_PREFIX = "https://static.wixstatic.com/"
CATALOG_FAMILIES = ["Barrell"]
PRODUCER_BY_FAMILY = {}

# path → (expression, aliases). expression None is the plain "Barrell" flagship blend.
REFILE = {
    "bourbon": ("Batch Bourbon", ["Barrell Bourbon"]),  # bare "Bourbon" collides with the flagship's blank
    "rye": ("Rye", []),
    "foundation": ("Foundation", []),
    "newyear": ("New Year", []),
    "infinite": ("Infinite Barrel Project", ["Barrell Whiskey: Infinite Barrel Project"]),
    "graylabelbourbon": ("Gray Label", ["Barrell Gray Label Bourbon"]),
    "graylabelwhiskey": ("Gray Label Whiskey", []),
    "goldbourbon": ("Gold Label", ["Barrell Gold Label Bourbon"]),
    "golddovetail": ("Gold Label Dovetail", []),
    "whiskey": (None, []),
    "seagrass": ("Seagrass", []),
    "dovetail": ("Dovetail", []),
    "vantage": ("Vantage", []),
    "armida": ("Armida", []),
    "privaterelease": ("Private Release", []),
    "caskfinish": ("Cask Finish Series", []),
}
NOT_CORE = re.compile(r"new year|infinite|gold label|gray label|armida|private release|cask finish", re.I)
RARITY = [(r"gold label", "unicorn"), (r"private release", "unicorn"), (r"new year|cask finish", "lottery"),
          (r"infinite|gray label|armida", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://www.barrellbourbon.com/{p}" for p in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(page: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _current_block(own: str) -> str:
    """Every batch/release page lists the current bottling first, then its full history — split at the
    second "N proof" mention (a single-release page like Foundation never has one)."""
    hits = list(re.finditer(r"\b\d{2,3}(?:\.\d+)?\s*proof\b", own, re.I))
    return own[: hits[1].start()] if len(hits) >= 2 else own


def _proof(spec: str) -> float | None:
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*proof\b", spec, re.I)
    return float(m.group(1)) if m else None


def _mash(spec: str) -> str | None:
    m = re.search(r"DERIVED MASH BILL:\s*\|?\s*(.*?)\s*\|\s*(?:​\s*\|\s*)?A blend", spec, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def _age(spec: str) -> tuple[float | None, str | None]:
    # per-component ages ("Kentucky: 12 years old") aren't the batch's own age; drop that whole span first.
    stripped = re.sub(r"BLEND COMPONENTS:.*?DERIVED MASH BILL:[^|]*\|", "", spec, flags=re.S)
    m = re.search(r"\bmatured for (\d{1,2}(?:\.\d)?)\s*years?\b", stripped, re.I)
    if not m:
        hits = {float(h) for h in re.findall(r"\b(\d{1,2}(?:\.\d)?)-years?-old\b", stripped, re.I)}
        if len(hits) == 1:  # a repeated mention of the same figure confirms it; two different ones is a component list
            years = next(iter(hits))
            return years, f"{int(years) if years == int(years) else years} yr"
        return None, None
    years = float(m.group(1))
    return years, f"{int(years) if years == int(years) else years} yr"


def _image(page: str, spec: str) -> str | None:
    batch = re.search(r"\bbatch\s*0*(\d+)\b", spec, re.I)
    for m in re.finditer(
        r"https://static\.wixstatic\.com/media/([^\"'\s)]+?~mv2\.(?:png|jpg|jpeg))/v1/crop/x_\d+,y_\d+,w_(\d+),h_(\d+)/fill/[^/\"']+/([^\"'\s)]+\.(?:png|jpg|jpeg))",
        page, re.I,
    ):
        media_id, w, h, fname = m.group(1), int(m.group(2)), int(m.group(3)), urllib.parse.unquote(m.group(4))
        if w < 500 or h < 1.1 * w:
            continue
        if batch:
            fname_num = re.search(r"\b0*(\d{2,3})\b", fname)
            if fname_num and int(fname_num.group(1)) != int(batch.group(1)):
                continue
        return f"https://static.wixstatic.com/media/{media_id}"
    return None


SECTION_END = re.compile(
    r"With (?:a |an )?(?:few |splash|drop|little)[^.:]{0,40}?water|(?:RECENT )?NOTABLE PRESS|\bPRESS\b|Previous|AWARDS|\bBATCH \d")
PART_CHARS = 300


def _tokens_text(own: str) -> str:
    """The page text with `|` fragments rejoined: a fragment that starts lowercase right after a letter with no space
    between ("edg| es.") is the rest of the same word."""
    out, prev_raw = "", ""
    for raw in own.replace("\u200b", "").split("|"):
        tok = raw.strip()
        if not tok:
            continue
        glue = out and not prev_raw.endswith(" ") and tok[0].islower() and out[-1].isalpha()
        out += tok if glue else (" " + tok if out else tok)
        prev_raw = raw
    return out


def _notes(own: str) -> str | None:
    txt = _tokens_text(own)
    m = re.search(r"\bNose\s*:", txt)
    if not m:
        return None
    block = txt[m.start():]
    end = SECTION_END.search(block)
    block = block[: end.start()] if end else block
    parts = re.split(r"\b(Nose|Palate|Finish)\s*:\s*", block)
    out = []
    for label, body in zip(parts[1::2], parts[2::2]):
        sents = re.split(r"(?<=[.!?])\s+", body.strip())
        kept = ""
        for sent in sents:
            if kept and len(kept) + len(sent) + 1 > PART_CHARS:
                break
            kept = f"{kept} {sent}".strip()
        if kept:
            out.append(f"{label}: {kept[:PART_CHARS + 120]}")
    return " ".join(out) or None


def parse(url: str, page: str) -> BottlingRecord | None:
    path = url.rstrip("/").split("/")[-1]
    if path not in REFILE:
        return None
    expression, aliases = REFILE[path]
    name = f"Barrell {expression}" if expression else "Barrell"
    own = _flatten(page).split("Use tab to navigate through the menu items.| ", 1)[-1]
    spec = _current_block(own)
    proof = _proof(spec)
    years, label = _age(spec)
    mash_raw = _mash(spec)
    rye = expression == "Rye"
    bourbon_words = bool(re.search(r"straight bourbon whiskeys?\b", spec, re.I))
    canadian = bool(re.search(r"\bcanada\b|\bcanadian\b", spec, re.I))
    if rye:
        class_raw = "Straight Rye Whiskey"
    elif canadian or (expression in ("Gray Label Whiskey", "Gold Label Dovetail", None) and not bourbon_words):
        class_raw = "Blended American Whiskey"
    else:
        class_raw = "Straight Bourbon Whiskey"
    img = _image(page, spec)
    return BottlingRecord(
        brand_family="Barrell", expression=expression, name=name, source_url=url, proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style=None,
        description=_text(spec[:600]), tasting_notes=_notes(own), image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )
