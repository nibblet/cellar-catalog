"""rockypatel.com — WordPress/Beaver Builder, one page per line. A "Cigar Details" block lists
SIZES as "Name (L x R)" lines; newer pages also state COUNTRY OF ORIGIN, WRAPPER, BINDER & FILLER
and Strength, older ones only sizes and ratings. Country for every line comes from the site's own
Honduran / Nicaraguan collection pages (the `cigar-category` taxonomy), and a mild / medium / full
category gives body where the page doesn't."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions, shape

DELAY = 5
SITE = "https://www.rockypatel.com"
SITEMAP = SITE + "/cigar-sitemap.xml"
IMAGE_PREFIX = SITE + "/"
BRAND = "Rocky Patel"
# the maker's collection pages come first: they say which country each line is made in and how strong it is
COLLECTIONS = [SITE + "/cigar-category/honduran-cigars/", SITE + "/cigar-category/nicaraguan-cigars/",
               SITE + "/cigar-category/nicaraguan-cigars/page/2/"]
SKIP = {"cigar", "cigar-smoking-world-championship"}  # the archive page and an event
CATEGORY = {"honduran-cigars": ("country", "Honduras"), "nicaraguan-cigars": ("country", "Nicaragua"),
            "mild-cigar": ("body", "Mild"), "mild-cigars-by-rocky-patel": ("body", "Mild"),
            "medium-cigars": ("body", "Medium"), "medium-cigars-by-rocky-patel": ("body", "Medium"),
            "full-cigars-by-rocky-patel": ("body", "Full")}
_TAXONOMY: dict[str, dict[str, str]] = {}  # slug → {country, body}, filled from the collection pages

# page slug → (brand, line). Java is Rocky Patel's coffee-infused brand (rolled by Drew Estate); the
# rest are Rocky Patel lines named as the site titles them.
BRANDS = {
    "java-latte": ("Java", "Latte"), "java-maduro": ("Java", "Maduro"), "java-mint": ("Java", "Mint"), "java-red": ("Java", "Red"),
    "tavicusa": ("Rocky Patel", "Tavicusa"), "bold-by-nish-patel": ("Nish Patel", "Bold"),
}
# Catalog rows re-filed by hand: the seed dropped "The" from the Edge lines and filed a Vintage 1990 by its wrapper.
OVERRIDES = {
    "6074c732-74bf-4936-8478-9639045e7c2f": {"line": "The Edge Connecticut"},
    "5936c949-4185-4a8a-ae0e-a97135c0346e": {"line": "The Edge Maduro"},
    "f86761e5-770c-4a97-8b6b-7e61bf297b86": {"line": "Vintage 1990 Broadleaf"},   # "Broadleaf / Toro" 6.5 x 52, Honduras
    # the site names the Vintage lines by wrapper; re-filed here so the Broadleaf Toro above doesn't stop the diff's prefix match
    "6722a2b4-2357-41c1-af55-7dfa69c5e63f": {"line": "Vintage 1990 Broadleaf"},
    "90f4ceb9-de6f-4aef-96c6-a9f6cd126d9c": {"line": "Vintage 1990 Broadleaf"},
    # left alone: Royale, Cuban Blend (not on the site); Gold Label and Thirtieth Anniversary (pages list no sizes)
}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", xml) if u.rstrip("/").split("/")[-1] not in SKIP]
    return COLLECTIONS + sorted(urls)


def _text(fragment: str) -> str:
    t = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))  # composed é, plain spaces
    return re.sub(r"\s+", " ", t).strip()


def _line_name(page: str, slug: str) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    t = _text(h1.group(1)) if h1 else slug.replace("-", " ").title()
    t = re.sub(r"^Rocky Patel ", "", t).replace("’", "'")
    return t.title() if t.isupper() and t.isalpha() and len(t) > 3 else t  # "SIXTY" → "Sixty"; DBS and LB1 stay


LABELS = {"COUNTRY OF ORIGIN", "COUNTRY", "STRENGTH", "WRAPPER", "BINDER", "BINDERS", "DUAL BINDERS", "FILLER", "FILLERS",
          "BINDER & FILLER", "FILLER & BINDER", "WRAPPER, BINDER, FILLER", "CONSTRUCTION", "INFORMATION", "SHAPE", "FORMAT",
          "AGED", "AGED TOBACCO", "FACTORY", "PACKAGING", "RARE", "RATED", "AWARDS", "SIZES", "SIZE"}
_INLINE = r"(?i)\b(" + "|".join(sorted((re.escape(l) for l in LABELS), key=len, reverse=True)) + r")\s*:\s*"
DIMS = r"(\d(?:\.\d+)?(?:\s*(?:½|¼|¾|⅛|⅝|\d/\d))?\s*(?:inches|in\.?|\")?\s*(?:x|×|by)\s*(\d{2,3})(?:\s*/\s*(\d{2}))?)"
# "Robusto (5 x 50)", "Robusto 5 1/2 x 50", "Robusto : 5 1/2 inches by 50 ring gauge", "Bala (5 ¾ x 58/50)"
SIZE = re.compile(r"([A-Za-z][A-Za-z0-9'’.\- ]{1,30}?)\s*(?:\(|:)?\s*" + DIMS + r"(?:\s*ring gauge)?\)?", re.I)
SIZE_AFTER = re.compile(DIMS + r"\s+([A-Za-z][A-Za-z\- ]{2,30})", re.I)  # "7 x 48 Box-Pressed Churchill"


def _us(v: str) -> str:
    """Year of the Snake states a US and an International blend; the catalog is the US one."""
    m = re.search(r"USA\s*:?\s*(.+?)\s*\|?\s*International\b.*$", v)
    return m.group(1).strip() if m else v


def _leaf(v: str) -> str:
    """Prose to a fact: "Ecuadorian Habano wrapper" → "Ecuadorian Habano"; "one from Nicaragua and another from Mexico" → "Nicaragua and Mexico"."""
    v = re.sub(r"\s+(wrapper|binders?|fillers?)$", "", v, flags=re.I)
    v = re.sub(r"^one from\s+", "", v, flags=re.I).replace("another from ", "")
    return v


TOBACCO = re.compile(r"^(?:ecuador(?:ian)?|nicaraguan?|honduran?|mexic(?:o|an)|brazil(?:ian)?|dominican|cameroon|connecticut|sumatran?|"
                     r"habano(?:-seed)?|corojo|criollo|candela|broadleaf|maduro|oscuro|shade(?:-grown)?|san|andr[eé]s|pennsylvania|"
                     r"costa|rican|paraguay(?:an)?|jamastran|est[eé]l[ií]|jalapa|peru(?:vian)?|and|&)$", re.I)
NO_PROSE = {"winter-collection"}  # describes last year's wrapper next to this year's


def _prose(page: str, part: str, line: str | None) -> str | None:
    """The page copy names the leaf where the details block doesn't: "a 12-year-old Honduran Broadleaf
    wrapper" → "Honduran Broadleaf". Only tobacco words survive, in the maker's order. When the line is
    named for its wrapper (The Edge Sumatra), the sentence naming that leaf wins over one recalling
    the other Edge wrappers."""
    i, j = page.find("</h1>"), page.find("Cigar Details")
    text = _text(re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page[i:j], flags=re.S))
    tail = r"(?:\s+(?:grown in|from)\s+(?:the\s+)?((?:[\w’'-]+\s*){1,3}))?" if part == "wrapper" else "()"
    found = []
    for m in re.finditer(r"((?:[\w’'&-]+[ ,]+){1,6})" + part + r"s?\b" + tail, text, re.I):
        before = re.split(r"\b(?:wrapper|binder|filler)s?\b|,", m.group(1), flags=re.I)[-1]  # not the previous fact's words
        if line and line.lower() in before.lower():
            before = before.lower().split(line.lower())[-1]  # the page repeats its own title before the copy
        words = [w.strip(",.").replace("-seed", "") for w in (before + " " + (m.group(2) or "")).split()]
        kept = [w for w in words if TOBACCO.match(w)]
        while kept and kept[0].lower() in ("and", "&"):
            kept.pop(0)
        while kept and kept[-1].lower() in ("and", "&"):
            kept.pop()
        if kept and any(w.lower() not in ("and", "&") for w in kept):
            found.append(" ".join(kept))
    own = [w for w in (line or "").split() if TOBACCO.match(w) and w.lower() not in ("and", "&", "san")]
    for f in found:
        if own and own[-1].lower() in f.lower():
            return f
    return found[0] if found else None


def _details(page: str) -> dict[str, str]:
    """The Cigar Details block as {LABEL: text}. Labels are <h3> headings (sometimes wrapped in <strong>,
    sometimes with a colon); a label's value is everything up to the next label."""
    i = page.find("Cigar Details")
    if i < 0:
        return {}
    j = page.find("Continue Exploring", i)
    block = re.sub(r"<(?:br\s*/?|/p|/div|/h\d|/li)>", "\n", page[i:j if j > 0 else None])
    lines = [_text(l) for l in block.split("\n")]
    facts, label = {}, None
    for l in lines:
        if not l or l.startswith("Ever wonder how"):
            if l:
                label = None
            continue
        k = l.upper().rstrip(":").strip()
        if k in LABELS:
            label = k
            facts.setdefault(label, "")
        elif label:
            facts[label] = (facts[label] + " " + l.lstrip(": ")).strip()
        elif re.match(_INLINE, l):
            label = None
            facts.setdefault("", "")
            facts[""] += " " + l  # "Country of Origin: Nicaragua" on one line, handled below
    # a value may carry its own "Label : value" pairs (Year of the Snake's INFORMATION and CONSTRUCTION blocks)
    for k, v in list(facts.items()):
        parts = re.split(_INLINE, v)
        if len(parts) > 1:
            head = parts[0].strip()
            facts[k] = head if k else ""
            for lab, val in zip(parts[1::2], parts[2::2]):
                facts.setdefault(lab.upper().rstrip(":").strip(), val.strip())
    facts.pop("", None)
    return {k: v for k, v in facts.items() if v}


def parse(url: str, page: str) -> LineRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if "/cigar-category/" in url:
        for m in re.finditer(r'class="fl-post-grid-post[^"]*?((?:cigar-category-[a-z0-9-]+\s*)+)"[^>]*>\s*<meta[^>]*itemid="[^"]*/cigar/([a-z0-9-]+)/"', page):
            facts = _TAXONOMY.setdefault(m.group(2), {})
            for cat in re.findall(r"cigar-category-([a-z0-9-]+)", m.group(1)):
                if cat in CATEGORY:
                    facts[CATEGORY[cat][0]] = CATEGORY[cat][1]
        return None
    brand, line = BRANDS.get(slug, (BRAND, _line_name(page, slug)))
    facts = _details(page)
    sizes = []
    raw_sizes = facts.get("SIZES") or facts.get("SIZE") or ""
    found = SIZE.findall(raw_sizes) or [(n, d, r, r2) for d, r, r2, n in SIZE_AFTER.findall(raw_sizes)]
    for name, dims, ring, ring2 in found:
        L, R = dimensions(re.sub(r"\bby\b", "x", dims, flags=re.I))
        if L is None or R is None:
            continue
        name = re.sub(r"\s*box[- ]?pressed\s*", " ", name, flags=re.I).strip(" ,;")  # "Box-Pressed Churchill": the press is the line's
        name = name.title() if name[0].islower() else name  # Java's "x-press"
        shp = shape(name)[0]
        sizes.append(Vitola(name=name, length_in=L, ring_gauge=R, shape="figurado" if ring2 and shp == "parejo" else None))
    if not sizes:
        return None  # a few pages (Dark Star, Conviction) describe the blend but list no sizes
    # the headings drift page to page: WRAPPER / BINDER & FILLER, "Fillers", "Filler & Binder", or one
    # CONSTRUCTION block reading "Wrapper: … Binder: … Filler: …"
    blend = {}
    for k, v in facts.items():
        v = _us(v)
        if re.match(r"aged\b", v, re.I):
            continue  # "BINDERS: Aged 7+ years" is an age, not a leaf
        if k in ("WRAPPER", "BINDER", "BINDERS", "DUAL BINDERS", "FILLER", "FILLERS", "BINDER & FILLER", "FILLER & BINDER"):
            for part in re.findall(r"WRAPPER|BINDER|FILLER", k):
                blend.setdefault(part, v)
    blend = {k: _leaf(v) for k, v in blend.items() if not re.search(r"trade secret|undisclosed", v, re.I)}
    if slug not in NO_PROSE:
        for part in ("WRAPPER", "BINDER", "FILLER"):
            if not blend.get(part):
                blend[part] = _prose(page, part.lower(), line)
    img = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    tax = _TAXONOMY.get(slug, {})
    body = _us(facts.get("STRENGTH", "")) or tax.get("body")
    body = re.sub(r"\s+plus$", "-Plus", re.sub(r"[- ]bodied$", "", body.strip(), flags=re.I), flags=re.I) if body else None  # "Medium Plus", "Medium to Full-Bodied"
    country = facts.get("COUNTRY OF ORIGIN") or facts.get("COUNTRY") or tax.get("country")
    box = bool(re.search(r"box[- ]?pressed", " ".join(facts.get(k, "") for k in ("SHAPE", "FORMAT", "SIZES", "SIZE")), re.I)) or None
    return LineRecord(brand=brand, line=line, source_url=url, wrapper_raw=blend.get("WRAPPER"), binder=blend.get("BINDER"), filler=blend.get("FILLER"),
                      body=body, band_image_url=img.group(1) if img else None, vitolas=sizes, country=country,
                      box_pressed=box)
