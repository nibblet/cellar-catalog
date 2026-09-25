"""aganorsaleaf.com — WordPress + Elementor (PowerPack "Advanced Tabs" widget). One page per
`/cigars/<slug>/` under the "Cigars" nav (no cigar_product sitemap — hand-listed from the page
sitemap). Every page states a "Blend Summary" (Capa/Banda y Capote/Tripa = wrapper/binder/filler)
and a "Sizes Available..." list; strength is a scale rendered as an image, its filename literally
encoding the number ("strength-4-150x25-1.jpg", or "strength-3-5-...jpg" for a half-point 3.5).

Several pages hold more than one wrapper as PowerPack tabs on one page (Corojo/Maduro/Connecticut/
25th...), each its own Blend Summary + size block; the wrapper tag folds into each size's own name
("Corojo Robusto") rather than inventing a name for the shared line. Other conceptual lines are
instead split across SEPARATE pages, one per wrapper or release (JFR Corojo/Maduro/Connecticut;
Lunatic Habano/Maduro; the three Guardian of the Farm releases) — LINE_OVERRIDES unifies those the
same way, keyed by slug.

Brand routing: "Lunatic" and "JFR" already file under the catalog's "JFR" brand; "Guardian of the
Farm" is a Warped collaboration and files under "Warped" (its existing brand), not Aganorsa Leaf —
the rest of Warped's catalog still comes from its own queued warpedcigars.com import. The site
states its cigars are "rolled in our factories in Nicaragua and Miami" without saying which per
product, so country stays unknown throughout. "New Cuba" and "New Cuba Superior" publish no spec
data at all (marketing copy only) and are skipped."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 5  # robots.txt states no crawl-delay
SITE = "https://www.aganorsaleaf.com"
SITEMAP = SITE + "/wp-sitemap-posts-page-1.xml"

# No cigar-specific sitemap; hand-listed from the page sitemap's "Cigars" nav entries.
# "new-cuba" / "new-cuba-superior" excluded: marketing copy only, no Blend Summary or sizes.
SLUGS = [
    "lunatic-locos", "lunatic-torch", "rare-leaf-corojo-and-maduro", "aniversario-series",
    "guardian-of-the-farm-cerberus", "lunatic-habano", "guardian-of-the-farm-apollo-seleccion-de-warped",
    "guardian-of-the-farm-nightwatch", "lunatic-maduro", "aganorsa-leaf-signature-corojo",
    "aganorsa-leaf-supreme-leaf", "la-validacion-series", "jfr-corojo", "jfr-maduro", "jfr-connecticut",
    "aganorsa-leaf-arsenio", "jfr-20th-anniversary",
]

BRAND_PREFIX = (("jfr-", "JFR"), ("lunatic-", "JFR"), ("guardian-of-the-farm-", "Warped"))

# A conceptual line the site splits across several single-wrapper PAGES rather than tabs on one
# page: (line, wrap tag folded into each size's own name).
LINE_OVERRIDES = {
    "jfr-corojo": ("JFR", "Corojo"), "jfr-maduro": ("JFR", "Maduro"), "jfr-connecticut": ("JFR", "Connecticut"),
    "lunatic-habano": ("Lunatic", "Habano"), "lunatic-maduro": ("Lunatic", "Maduro"),
    "guardian-of-the-farm-cerberus": ("Guardian of the Farm", "Cerberus"),
    "guardian-of-the-farm-apollo-seleccion-de-warped": ("Guardian of the Farm", "Apollo"),
    "guardian-of-the-farm-nightwatch": ("Guardian of the Farm", "NightWatch"),
}

STRENGTH_SCALE = {1: "mild", 2: "mild_medium", 3: "medium", 4: "medium_full", 5: "full"}
DIMS_LINE = re.compile(r"^\d.*[x×]\s*\d", re.I)


def list_urls(fetcher) -> list[str]:
    return [f"{SITE}/cigars/{slug}/" for slug in SLUGS]


def _brand(slug: str) -> str:
    for prefix, brand in BRAND_PREFIX:
        if slug.startswith(prefix):
            return brand
    return "Aganorsa Leaf"


def _lines(text: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", text, flags=re.S)
    flat = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    out = [re.sub(r"\s+", " ", l).strip() for l in flat.split("\n") if l.strip()]
    merged = []  # "25<sup>th</sup>" splits into two lines; rejoin the bare ordinal suffix
    for l in out:
        if merged and re.fullmatch(r"st|nd|rd|th", l) and re.fullmatch(r"\d+", merged[-1]):
            merged[-1] += l
        else:
            merged.append(l)
    return merged


def _strength(block_html: str) -> str | None:
    m = re.search(r"strength-(\d)(?:-(\d))?(?:-\d+x\d+)?(?:-\d+)?\.\w+", block_html)
    if not m:
        return None
    n = int(m.group(1)) + (int(m.group(2)) / 10 if m.group(2) else 0)
    return STRENGTH_SCALE.get(round(n))


def _facts(lines: list[str]) -> dict[str, str]:
    facts = {}
    for label, key in (("Capa", "wrapper"), ("Banda y Capote", "binder"), ("Tripa", "filler")):
        if label in lines:
            i = lines.index(label)
            if i + 1 < len(lines):
                facts[key] = lines[i + 1]
    return facts


def _fold(tag: str | None, name: str) -> str:
    if not tag:
        return name
    if tag.split()[0].lower() in name.lower():  # "Apollo" the release naming its own "Apollo" size
        return name
    return f"{tag} {name}"


def _sizes(lines: list[str], wrap_tag: str | None) -> list[Vitola]:
    """Name / [an optional "(released ...)" aside] / Dims, repeating; a page may state several
    "Sizes Available..." sub-headers in a row (by box count, or by release date) that all belong
    to the same wrapper block, so a header only opens scanning, it never resets it."""
    vitolas = []
    started = False
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("Sizes Available"):
            started, i = True, i + 1
            continue
        if not started or l == "The Latest from":
            if l == "The Latest from":
                break
            i += 1
            continue
        j = i + 1
        if j < len(lines) and lines[j].startswith("("):
            j += 1
        if j < len(lines) and DIMS_LINE.match(lines[j]):
            length_in, ring = dimensions(lines[j])
            # "Maduro Size that shall not be named (1-Cnt) / 10 x 100" on the Lunatic Maduro page is
            # a joke entry, not a real SKU — its own ring gauge falls outside the catalog's range.
            if length_in is not None and (ring is None or 20 <= ring <= 80):
                vitolas.append(Vitola(name=_fold(wrap_tag, l), length_in=length_in, ring_gauge=ring))
            i = j + 1
            continue
        i += 1
    return _dedup(vitolas)


def _dedup(vitolas: list[Vitola]) -> list[Vitola]:
    """Supreme Leaf (released twice a year in a new vitola) has reused the same size name across
    two different release years at two different ring gauges ("Robusto (box pressed)" 5x54 and
    5x52); tag every same-named vitola after the first with its own ring gauge to keep them
    distinct, since the catalog is unique on (brand, line, expression)."""
    seen: dict[str, int] = {}
    out = []
    for v in vitolas:
        n = seen.get(v.name, 0)
        seen[v.name] = n + 1
        name = v.name if n == 0 else f"{v.name} ({v.ring_gauge} RG)"
        out.append(Vitola(name=name, length_in=v.length_in, ring_gauge=v.ring_gauge, image_url=v.image_url))
    return out


def _blocks(page: str) -> list[tuple[str | None, str]]:
    """(wrap_tag, html_chunk) per wrapper-variant PowerPack tab; a single (None, page) when the
    page has no tabs widget at all."""
    titles_raw = re.findall(r'pp-advanced-tabs-title-text">(.*?)</', page, re.S)
    chunks = re.split(r'id="pp-advanced-tabs-content-\d+"[^>]*>', page)[1:]
    if not titles_raw or not chunks:
        return [(None, page)]
    # the site renders each tab label twice (desktop nav + a mobile-responsive duplicate)
    if len(titles_raw) == 2 * len(chunks):
        titles_raw = titles_raw[:len(chunks)]
    titles = [" ".join(_lines(raw)) for raw in titles_raw]
    if len(titles) != len(chunks) or not all(titles):
        return [(None, page)]
    return list(zip(titles, chunks))


def parse(url: str, page: str) -> LineRecord | list[LineRecord] | None:
    slug = url.rstrip("/").split("/")[-1]
    brand = _brand(slug)
    t = re.search(r"<title>(.*?)</title>", page, re.S)
    if not t:
        return None
    title = re.sub(r"\s*[–—|].*$", "", html.unescape(t.group(1))).strip()
    if title.lower().startswith(brand.lower()):
        title = title[len(brand):].strip(" -–—:")
    override = LINE_OVERRIDES.get(slug)
    blocks = _blocks(page)
    records = []
    for tag, chunk in blocks:
        lines = _lines(chunk)
        wrap = override[1] if override else (tag if len(blocks) > 1 else None)
        vitolas = _sizes(lines, wrap)
        if not vitolas:
            continue
        facts = _facts(lines)
        line = override[0] if override else (title or None)
        records.append(LineRecord(
            brand=brand, line=line, source_url=url,
            wrapper_raw=facts.get("wrapper"), binder=facts.get("binder"), filler=facts.get("filler"),
            body=_strength(chunk), vitolas=vitolas,
        ))
    return records or None
