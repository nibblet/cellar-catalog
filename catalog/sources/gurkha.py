"""gurkhacigars.com — WordPress, one page per line under /cigar-collections/. A Blend block states
Wrapper / Binder / Filler / Origin, then Sizes as "Name - LxR" and a Strength."""
from __future__ import annotations

import html
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 10  # robots.txt asks for a 10 s crawl delay
SITE = "https://gurkhacigars.com"
SITEMAP = SITE + "/product-sitemap.xml"
IMAGE_PREFIX = SITE + "/"
BRAND = "Gurkha"
SKIP = re.compile(r"/shop/?$|/toro-samplers/")  # the shop index and sampler packs


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(u.replace("http://", "https://") for u in re.findall(r"<loc>([^<]+)</loc>", xml)
                  if "/cigar-collections/" in u and not SKIP.search(u))


def _lines(page: str) -> list[str]:
    body = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", page, flags=re.S)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", "\n", body)))
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


# Catalog rows re-filed by hand.
OVERRIDES = {
    "20e04ecf-cf9d-4449-9c02-13665e903a83": {"line": "The Beauty", "expression": "XO"},              # "Beauty / Robusto" 7 x 60 is The Beauty's one size, 6.5 x 60
    "37facd4a-bc82-4072-afb8-fbe59a7571c3": {"expression": "Hedonism"},                            # 6 x 58 is the Hedonism
    "ce71c3bc-d630-45d5-af76-8c50101acc56": {"line": "Cellar Reserve Edición Especial 18 Year", "expression": None},  # no dims: a placeholder
    # merged after apply: "Ghost / Robusto" 6 x 54 is the Ghost Asura. Left alone: Marquesa, San Miguel, Warpig — not on the site
}
DIMS = re.compile(r"(\d+(?:\.\d+)?(?:\s+\d\s*/\s*\d)?)\s*x\s*(\d{2,4})")
FIXES = {"Hendonism": "Hedonism", "Cafe Tabac": "Café Tabac"}  # the site's own typo on three Cellar Reserve pages; the others spell it Hedonism
BODY = {"Strong": "Full"}


def _sizes(block: str, fallback: str) -> list[Vitola]:
    """"Koi - 4x58 Solara - 5x58" → Vitolas. Fractions come through as "6 1 / 2 x60" (sup/sub
    markup); an entry without a name ("7.5x52") is the line's only size and takes the line's name;
    "Solara - Double Robusto - 5x58" keeps the maker's name, not the vitola gloss."""
    out, parts = [], DIMS.split(block)
    for i in range(0, len(parts) - 1, 3):
        name = re.split(r"\s+[-–]\s+", parts[i].strip(" -–:"))[0].strip()
        name = re.sub(r"^Sizes:?\s*", "", name) or (fallback if not out else f"{parts[i + 1]}x{parts[i + 2]}".replace(" ", ""))  # Café Tabac's second size is listed as "4x38" alone
        L, R = dimensions(re.sub(r"\s*/\s*", "/", parts[i + 1]) + f" x {parts[i + 2]}")  # "6 1 / 2" → "6 1/2"
        if R and R > 80:
            R = int(str(R)[:2])  # the Real page prints "6x544"
        if L and R:
            out.append(Vitola(name=FIXES.get(name, name), length_in=L, ring_gauge=R))
    return out


def parse(url: str, page: str) -> LineRecord | list[LineRecord] | None:
    lines = _lines(page)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    line = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h1.group(1)))).strip() if h1 else None
    if not line:
        return None
    line = re.sub(r"^Gurkha\s+", "", line)
    facts: dict[str, str] = {}
    for l in lines:
        m = re.match(r"^(Wrapper|Binder|Filler|Origin)\s*:\s*(.+)$", l, re.I)
        if m:
            facts[m.group(1).lower()] = m.group(2).strip()
    try:
        a, b = lines.index("Sizes"), lines.index("Strength")
    except ValueError:
        return None
    sizes = _sizes(" ".join(lines[a + 1:b]), line)
    if not sizes:
        return None
    strength = lines[b + 1] if b + 1 < len(lines) and not lines[b + 1].startswith("Related") else ""
    body = BODY.get(strength, re.sub(r"[- ]bodied$", "", strength, flags=re.I).strip()) or None
    # og:image is the site-wide logo card; the line's photo is an upload named for the line (the page
    # also carries the nav's menu art, an age-gate popup and the related lines' photos)
    slug_words = [w for w in url.rstrip("/").split("/")[-1].split("-") if len(w) >= 3 and w not in ("the", "gurkha")]
    photos = [i for i in re.findall(r'<img[^>]+src="([^"]+/wp-content/uploads/[^"]+)"', page)
              if any(w in i.rsplit("/", 1)[-1].lower() for w in slug_words)]
    image = photos[0] if photos else None
    wrapper = facts.get("wrapper")
    if wrapper and re.search(r"varies|proprietary", wrapper, re.I):
        wrapper = None
    common = dict(brand=BRAND, line=line, source_url=url, binder=facts.get("binder"), filler=facts.get("filler"), body=body,
                  band_image_url=image, country=facts.get("origin"),
                  box_pressed=bool(re.search(r"box[- ]?press", " ".join(lines), re.I)) or None)
    if wrapper is None and facts.get("wrapper", "").lower() == "varies":
        # Volition America: one size per wrapper, named for the wrapper
        return [LineRecord(wrapper_raw=v.name, vitolas=[v], **common) for v in sizes]
    return LineRecord(wrapper_raw=wrapper, vitolas=sizes, **common)
