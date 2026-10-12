"""luckysevenspirits.com (Lucky Seven Spirits — a Kentucky sourcing and blending company; no distillery of its
own, blending and bottling are contracted to Bardstown Bourbon Company per its FAQ). WordPress/Salient. The
18+ "Are you over 21?" overlay is client-side markup inside every page's static HTML, not a server gate: the
importer reads what any plain request is served and clicks nothing. The sitemap lists only marketing pages; the
bottlings live on two of them, so two pages are read and merged:

* /our-collection/ — one long page, a section per bottling ("The Hold Up| ► WATCH THE LAUNCH FILM| BUY NOW|
  9 Year| Kentucky Straight Bourbon| 100 Proof — 50% Alc. by Vol"). The only place a mash bill appears (The New
  Yorker's spec block: Classification / Proof / Age / Mashbill) and where the finishes are described.
* /buy-now/ — the store: Gold Label and The Workhorse (neither on the collection page for Gold Label), a proof for
  each finished and small-batch bottle, and a bottle shot (a lazy-loaded `data-src` immediately before each title).

The pages disagree about The New Yorker (117.2 in the collection page's spec block, "117" in the store's prose, 117.4
in a bundle table); the spec block is the label-style statement and matches the seed, so it wins. The store also
quotes a proof for individual single barrels (The Proprietor 6yr "Barrel #53, 122.4", The Holiday Toast and The
Frenchman single barrels) — a barrel's proof is not the bottling's, so The Proprietor states none and the
single-barrel variants are not rows. The collection page says The Hold Up is a 9 Year (the seed's 12 was the first
batch). The Jokester has only a video-embed page and is on neither the collection nor the store page: the seed row
is left alone, not flagged (a page that exists is not gone).

Pages are merged through module state: the collection page's records are held and the store page's parse returns the
combined list (the diff's `_dedupe` keeps the last record per bottling).

`tasting_notes` is the "Tasting Notes:" line under each bottle's own tile on the store page (the Gold Label's is the
blender's). The collection page's quoted reviews (Binny's, Bounty Hunter, Whisky Advocate) are retailers' and critics'
words, the single-barrel tiles describe one barrel, and a tile whose note names no actual flavor (The Holiday Toast's, The Frenchman's) keeps none."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Lucky Seven"
DELAY = 6
SITEMAP = "https://luckysevenspirits.com/page-sitemap.xml"
IMAGE_PREFIX = "https://luckysevenspirits.com/"
CATALOG_FAMILIES = ["Lucky Seven"]
PRODUCER_BY_FAMILY = {}
COLLECTION = "https://luckysevenspirits.com/our-collection/"
STORE = "https://luckysevenspirits.com/buy-now/"
BASE = "Kentucky Straight Bourbon Whiskey"

# page title → (expression, aliases, finish, extra class text). expression None is not used: Lucky Seven has no flagship.
REFILE = {
    "The Hold Up": ("The Hold Up", [], None, ""),
    "The Holiday Toast": ("The Holiday Toast", [], "Toasted New American Oak", ""),
    "The Frenchman": ("The Frenchman", [], "New French Oak", ""),
    "The New Yorker": ("The New Yorker", [], "Amburana Casks", ""),
    "The Workhorse": ("The Workhorse", [], None, ""),
    "Lucky Seven Small Batch": ("Gold Label", ["Lucky Seven Small Batch", "Lucky Seven Gold Label Small Batch"], None, ""),
}
PROPRIETOR = {"6": "The Proprietor 6 Year", "14": "The Proprietor 14 Year"}
CORE = {"The Hold Up", "The Frenchman", "The New Yorker", "The Workhorse", "Gold Label", "The Proprietor 6 Year", "The Proprietor 14 Year"}
RARITY = [(r"proprietor|holiday toast", "allocated"), (r"new yorker|frenchman", "limited"), (r".", "shelf")]
MASH_BILLS = {}

_state: dict[str, list[BottlingRecord]] = {}


def list_urls(fetcher) -> list[str]:
    return [COLLECTION, STORE]  # collection first: the store's parse merges what the collection page held


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"(\|\s*)+", "| ", t)


def _text(frag: str | None) -> str | None:
    t = re.sub(r"\s+", " ", (frag or "").replace("|", " ")).strip(" |")
    return t or None


def _rec(expr: str, aliases: list[str], proof, age_years, age_label, class_raw: str, mash_raw, finish, url, img, desc) -> BottlingRecord:
    return BottlingRecord(
        brand_family="Lucky Seven", expression=expr, name=f"Lucky Seven {expr}", source_url=url, proof=proof,
        age_years=age_years, age_label=age_label, class_raw=class_raw, mash_raw=mash_raw, finish=finish,
        description=desc, image_url=img, aliases=sorted(set(aliases)),
        is_core_range=expr in CORE,
    )


def _collection(page: str) -> list[BottlingRecord]:
    own = _flat(page)
    starts = list(re.finditer(r"(The Hold Up|The Holiday Toast|The Frenchman|The Workhorse|The Proprietor|The New Yorker)\|\s*(?:► WATCH THE LAUNCH FILM\|\s*)?BUY NOW\|", own))
    out = []
    for i, m in enumerate(starts):
        title = m.group(1)
        sec = own[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(own)]
        sec = sec.split("Sign Up Now &")[0]
        pm = re.search(r"Proof:\s*(\d{2,3}(?:\.\d+)?)", sec) or re.search(r"(\d{2,3}(?:\.\d+)?)\s*Proof", sec)
        proof = float(pm.group(1)) if pm else None
        if title == "The Proprietor":
            am = re.search(r"(?:^|\|)\s*(\d{1,2}) Year Single Barrel\|", sec)
            if not am or am.group(1) not in PROPRIETOR:
                continue
            years = float(am.group(1))
            expr = PROPRIETOR[am.group(1)]
            cs = bool(re.search(r"(?:^|\|)\s*Cask Strength\|", sec))
            out.append(_rec(expr, [], None, years, f"{int(years)} yr", BASE + " Single Barrel" + (" Cask Strength" if cs else ""), None, None, COLLECTION, None,
                            _text(re.sub(r"AWARDS|\"|”", " ", sec.split("special bottle", 1)[0][-420:]))))
            continue
        expr, aliases, finish, _ = REFILE[title]
        years = label = None
        ym = re.search(r"\|\s*(\d{1,2}) Year\|", sec)
        if ym:
            years, label = float(ym.group(1)), f"{ym.group(1)} yr"
        mash = None
        if title == "The New Yorker":
            nm = re.search(r"Age:\s*NAS", sec)
            label = "NAS" if nm else label
            mm = re.search(r"Mashbill:\s*([^|]+)", sec)
            mash = mm.group(1).strip() if mm else None
            cm = re.search(r"Classification:\s*([^|]+)", sec)
            if cm and "Finished" in cm.group(1):
                finish = "Amburana Casks"
        out.append(_rec(expr, aliases, proof, years, label, BASE, mash, finish, COLLECTION, None, None))
    return out


def _store_images(page: str) -> dict[str, str]:
    """The bottle shot is the `data-src` image immediately before each product's title in the store listing."""
    out = {}
    for m in re.finditer(r'data-src="(https://[^"?]*/uploads/[^"?]+\.(?:png|jpe?g))[^"]*"[^>]*>\s*(?:</[a-z0-9]+>\s*)*<h4[^>]*>([^<]+)</h4>', page):
        out[html.unescape(m.group(2)).strip()] = m.group(1)
    for m in re.finditer(r'data-src="(https://[^"?]*/uploads/[^"?]+\.(?:png|jpe?g))[^"]*"[^>]*/?>\s*(?:</[a-z0-9]+>\s*)*(?:<[^>]+>\s*)*?(The Workhorse|The Hold Up 9yrs|Lucky Seven Small Batch)\b', page):
        out.setdefault(m.group(2), m.group(1))
    return out


_TILE_END = r"(?=\|\s*(?:Small Batch Expressions|Single Barrel Expressions|The Workhorse|The Hold Up 9yrs|Lucky Seven Small Batch|The New Yorker|The Holiday Toast|The Frenchman)\b|$)"
_FLAVOR = re.compile(r"\b(?:fruit|spice|allspice|caramel|vanilla|pears?|pecans?|cinnamon|sugar|tobacco|cherry|cherries|jam|mint|honey|chocolate|citrus)\b", re.I)


def _tile_notes(region: str, key: str) -> str | None:
    """The "Tasting Notes:" line of the store tile whose title is `key`, up to the next tile or section heading."""
    m = re.search(re.escape(key) + r"\|.*?Tasting Notes:\|\s*(.*?)" + _TILE_END, region, re.S)
    if not m:
        return None
    t = re.sub(r"\s+", " ", m.group(1).replace("|", " ")).strip()
    t = re.sub(r'^\(from the Blender\):\s*', "", t).strip('" ')
    return t[:900] if _FLAVOR.search(t) else None


def _store(page: str) -> list[BottlingRecord]:
    own = _flat(page)
    imgs = _store_images(page)
    # the three table rows and the product tiles; read the tiles ("Small Batch Expressions" onward)
    out = []
    gm = re.search(r"Lucky Seven Small Batch\|\s*750 ml\s*[–-]\s*ABV\s*(\d+(?:\.\d+)?)%?\s*│\s*(\d{2,3}(?:\.\d+)?)\s*Proof", own)
    if gm:
        expr, aliases, finish, _ = REFILE["Lucky Seven Small Batch"]
        out.append(_rec(expr, aliases, float(gm.group(2)), None, None, BASE + " Small Batch", None, finish, STORE,
                        imgs.get("Lucky Seven Small Batch"), None))
        out[-1].tasting_notes = _tile_notes(own, "Lucky Seven Small Batch")
    for title, key in (("The Workhorse", "The Workhorse"), ("The Hold Up", "The Hold Up 9yrs"), ("The New Yorker", "The New Yorker"),
                       ("The Holiday Toast", "The Holiday Toast"), ("The Frenchman", "The Frenchman")):
        expr, aliases, finish, _ = REFILE[title]
        # the tiles sit after the "Barrel Finished Expressions" heading; the bundle tables before it name the same bottles
        tiles = own.split("Barrel Finished Expressions", 1)[-1].split("Single Barrel Expressions", 1)[0]
        tm = re.search(re.escape(key) + r"\|[^|]*?(?:Proof\s*(\d{2,3}(?:\.\d+)?)|(\d{2,3}(?:\.\d+)?)\s*Proof)", tiles)
        proof = float(tm.group(1) or tm.group(2)) if tm else None
        ym = re.search(r"(\d{1,2})yrs", key)
        out.append(_rec(expr, aliases, proof, float(ym.group(1)) if ym else None, f"{ym.group(1)} yr" if ym else None, BASE, None, finish, STORE,
                        imgs.get(key), None))
        out[-1].tasting_notes = _tile_notes(tiles, key)
    return out


def parse(url: str, page: str) -> list[BottlingRecord] | None:
    if url == COLLECTION:
        _state["collection"] = _collection(page)
        return []  # reported through the store page's merged list, so nothing is counted twice
    if url != STORE:
        return None
    held = {r.expression: r for r in _state.get("collection", [])}
    merged = []
    for s in _store(page):
        c = held.pop(s.expression, None)
        if c is None:
            merged.append(s)
            continue
        # the collection page's spec block wins where both state a figure (The New Yorker 117.2 vs the store's 117 / 117.4)
        merged.append(BottlingRecord(
            brand_family=s.brand_family, expression=s.expression, name=s.name, source_url=c.source_url,
            proof=c.proof if c.proof is not None else s.proof, age_years=c.age_years if c.age_years is not None else s.age_years,
            age_label=c.age_label or s.age_label, class_raw=c.class_raw, mash_raw=c.mash_raw, finish=c.finish or s.finish,
            description=c.description, tasting_notes=s.tasting_notes, image_url=s.image_url, aliases=sorted(set(c.aliases) | set(s.aliases)), is_core_range=s.is_core_range))
    return merged + list(held.values())  # the Proprietors: on the collection page only
