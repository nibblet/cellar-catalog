"""padron.com — WordPress/Elementor, one page per series. Every size is a text block: the marketed
name in one <p> and "ring x length" in the next ("46 x 6 7/8"; figurados print two rings,
"52 x 42 x 6 7/8"). A cigar photo precedes each block; its alt is the maker's full name.

Padrón publishes almost no blend facts per line. What it does state, company-wide, on
https://padron.com/vertically-integrated/ is that every cigar is made "at our facility in
Nicaragua" from the family's own Nicaraguan "sun-grown habano" tobacco — so country, wrapper origin
and leaf, binder and filler come from that page for every series except Dámaso, whose own page
names an Ecuadorian Connecticut wrapper. Most series come "in natural and maduro": one row per
wrapper, "No. 1 Natural" / "No. 1 Maduro", the way retailers and smokers name them."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import dimensions, shape

BRAND = "Padron"
COUNTRY = "Nicaragua"  # https://padron.com/vertically-integrated/: "the manufacturing process at our facility in Nicaragua"
DELAY = 5
SITEMAP = "https://padron.com/cigar-offering/"
IMAGE_PREFIX = "https://padron.com/"
TOBACCO = "Nicaraguan sun-grown habano"  # same page: "sun-grown habano wrapper leaves", "Padrón's Nicaraguan farms"

# Page slug → catalog line. None is the flagship: "Padrón 2000", not "Padrón Padrón Series 2000".
SERIES = {
    "padron-series": None,
    "damaso-series": "Dámaso",
    "padron-1964-anniversary-series": "1964 Anniversary",
    "padron-1926-serie": "1926 Serie",
    "padron-family-reserve": "Family Reserve",
    "padron-5oth-anniversary-humidor": "50th Anniversary",
    "60th-anniversary": "60th Anniversary",
    # "special-releases" (No. 97, No. 99) publishes no sizes
}

# Catalog rows re-filed by hand: seed rows carried the wrapper in the line name, or no wrapper at all;
# each is assigned the variant its wrapper_shade said it was.
OVERRIDES = {
    "a2278c9e-69c3-4e22-b657-a35cd17cdb50": {"line": None, "expression": "2000 Maduro"},
    "3df2aee8-1e4f-49a3-8d13-464787a4e775": {"line": None, "expression": "3000 Natural"},
    "c87654ea-c294-4dcc-82ed-9bd9c1709b5b": {"line": None, "expression": "4000 Natural"},   # shade colorado
    "f8b55c40-5623-4c40-80d7-7022e72ee784": {"line": None, "expression": "5000 Maduro"},
    "f5e0c459-8728-4031-9bad-1cf7cfe839e3": {"line": None, "expression": "6000 Natural"},   # shade colorado
    "776ee4ec-0dc8-47b9-81ab-a3aaa0862253": {"line": None, "expression": "7000 Natural"},
    "dd345ff2-c1b8-4c0e-b02a-6878cbb069d0": {"line": None, "expression": "Londres Maduro"},
    "6f4ff0cc-4172-4800-b2e7-5e75c55e7771": {"expression": "No. 40 Maduro"},                # "40th Anniversary" is the maker's No. 40
    "7c8b0851-769c-427a-9262-684263851859": {"expression": "No. 1 Maduro"},
    "6a5e5969-a7fc-46ed-ba5f-c41382ed3eda": {"expression": "No. 2 Maduro"},
    "d07dfc12-7f94-41b7-a953-be06a02ff7ab": {"expression": "No. 35 Maduro"},                # seed shade said colorado, but its five line-mates are maduro and the Natural No. 35 already exists
    "43287c77-6809-47b1-813a-c4660260c9e9": {"expression": "No. 6 Maduro"},
    "15446c87-3778-4dbf-8385-e20954551faa": {"expression": "No. 9 Maduro"},
    "934904ae-52f6-4829-8995-fa36f76e63c4": {"line": "Dámaso"},                                # the maker's accent
    "a2ac0fed-7791-4f96-aeb3-42bac259ce45": {"line": "Dámaso"},
    "877d6998-f58c-4efc-a1f1-da2d98f0d489": {"line": "1926 Serie", "expression": "No. 1 Natural"},
    "379b8b92-26ed-44fd-aee0-d5ebd3fbf290": {"line": "1926 Serie", "expression": "No. 2 Natural"},
    "e14a99f5-7f87-42f6-8d09-8ff94916ac09": {"line": "1926 Serie", "expression": "No. 35 Natural"},
    "4143f29e-b66d-498c-9971-a13a5799d3b0": {"expression": "Diplomatico Natural"},          # shade colorado
    "4a7d42f3-62a4-4e3f-9195-a686e71f1907": {"expression": "Exclusivo Maduro"},
    "befe37b9-2728-469a-b1a6-34e840723ba4": {"expression": "Imperial Maduro"},
    "18998ed8-1ac5-4988-a1e6-c5f4729f8572": {"expression": "Monarca Natural"},              # shade colorado
    "4c2f5a8a-d9ae-488f-8dc8-2d9a8dd520a7": {"expression": "Presidente Maduro"},
    "66fd2b18-86e9-40f8-adac-263bf3eaadd9": {"expression": "No. 45 Maduro"},
    "70f6be6c-a0af-49e2-a3ee-f31afd6fc68a": {"expression": "No. 85 Natural"},               # shade colorado
    "e4041476-80c7-4a24-a603-53d72e54906f": {"line": "Family Reserve", "expression": "No. 45 Natural"},
    "95574b59-d338-4977-9839-a8446172cd41": {"line": "Family Reserve", "expression": "No. 50 Natural"},
}


def list_urls(fetcher) -> list[str]:
    page = fetcher.get(SITEMAP)
    slugs = {s.strip("/") for s in re.findall(r'href="(/[a-z0-9-]+/?)"', page)}
    return sorted(f"https://padron.com/{s}/" for s in slugs if s in SERIES)


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").strip()


def _size_name(raw: str) -> str:
    n = re.sub(r"\s+", " ", _text(raw)).strip("“”\"' ")
    return re.sub(r"^No\.?\s*(?=\d)", "No. ", n)  # "No 17" → "No. 17"


def parse(url: str, page: str) -> LineRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in SERIES:
        return None
    line = SERIES[slug]
    # description: the first long paragraph after the page heading
    desc = " ".join(_text(p) for p in re.findall(r"<p>([^<]{120,})</p>", page)[:3])
    sizes = []
    for m in re.finditer(r'<p>([^<]{1,40})</p>\s*</div>\s*</div>\s*<div[^>]*>\s*<div[^>]*>\s*<p>(\d{2}(?: x \d{2})? x \d[^<]*)</p>', page):
        name = _size_name(m.group(1))
        rings = [int(r) for r in re.findall(r"\b(\d{2})\b(?= x)", m.group(2))]
        length_txt = re.sub(r"^(\d{2} x )+", "", _text(m.group(2)))
        length, _ = dimensions(f"{length_txt.split('  ')[0].strip()} x {max(rings)}")  # "6 7/8" → 6.875
        img = [re.sub(r"-\d+x\d+(?=\.\w+$)", "", i) for i in re.findall(r'<img[^>]+src="([^"]+)"', page[max(0, m.start() - 4000):m.start()])]  # the original, not a resized variant
        # two ring gauges printed is the maker saying it tapers; otherwise the shape is the name's to say
        shp = ("figurado" if shape(name)[0] == "parejo" else shape(name)[0]) if len(rings) > 1 else None
        sizes.append(Vitola(name=name, length_in=length, ring_gauge=max(rings), image_url=img[-1] if img else None, shape=shp))
    if not sizes:
        return None
    body = re.search(r"\b(mild to medium|medium-? to full|mild|medium|full)[- ](?:bod|flavor)", desc, re.I)
    body = body.group(1).replace("- to", " to").title() if body else None
    box = bool(re.search(r"box[- ]press", desc, re.I))
    common = dict(brand=BRAND, line=line, source_url=url, body=body, box_pressed=box, country=COUNTRY,
                  binder=TOBACCO, filler=TOBACCO)
    if slug == "damaso-series":
        # "made with Ecuadorian Connecticut wrapper"; the Red Label sizes are described only as "more robust"
        plain = [v for v in sizes if "red label" not in v.name.lower()]
        red = [v for v in sizes if "red label" in v.name.lower()]
        recs = [LineRecord(**common, wrapper_raw="Ecuadorian Connecticut", vitolas=plain)]
        if red:
            recs.append(LineRecord(**common, wrapper_raw=None, vitolas=red))
        return recs
    if re.search(r"natural (?:and|or) maduro", page, re.I):
        # one row per wrapper: the same size, the maker's two wrappers
        return [
            LineRecord(**common, wrapper_raw=f"{TOBACCO} natural", vitolas=[Vitola(f"{v.name} Natural", v.length_in, v.ring_gauge, v.image_url, shape=v.shape) for v in sizes]),
            LineRecord(**common, wrapper_raw=f"{TOBACCO} maduro", vitolas=[Vitola(f"{v.name} Maduro", v.length_in, v.ring_gauge, v.image_url, shape=v.shape) for v in sizes]),
        ]
    return LineRecord(**common, wrapper_raw=TOBACCO, vitolas=sizes)
