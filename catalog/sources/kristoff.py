"""kristoff.com — WooCommerce, one product page per line. Blend facts in a "Blend" list
(Wrapper:/Binder:/Filler:/Strength Profile: N out of 5), sizes in a "Sizes" list as "Name – L x R"."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import clean_value, dimensions, size_name

BRAND = "Kristoff"
COUNTRY = "Dominican Republic"
DELAY = 5
SITEMAP = "https://kristoff.com/product-sitemap.xml"

STRENGTH_1_5 = {"1": "Mild", "2": "Mild-Medium", "3": "Medium", "4": "Medium-Full", "5": "Full"}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(set(re.findall(r"<loc>(?:<!\[CDATA\[)?(https://kristoff\.com/product/[^<\]]+/)", xml)))


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").strip()


def _field(block: str, label: str) -> str | None:
    m = re.search(rf"\b{label}\s*:\s*(.*?)(?:</|\s{{2,}}|$)", block, re.I | re.S)
    return clean_value(_text(m.group(1))) if m else None


def parse(url: str, page: str) -> LineRecord | None:
    title = re.search(r'class="product_title[^"]*"[^>]*>(.*?)</h1>', page, re.S)
    if not title:
        return None
    line = _text(title.group(1))
    if line.lower().startswith(BRAND.lower()):
        line = line[len(BRAND):].strip(" -–—:") or None

    blend = re.search(r"<h4>\s*<strong>\s*Blend\s*</strong>\s*</h4>\s*<ul>(.*?)</ul>", page, re.S)
    # Sizes come as "Name – L x R", "Name: L x R", "Name L x R" or a bare "L x R", in <li>s or prose,
    # under a "Sizes" or "Size" heading. Read the text after the heading up to the next section.
    heading = re.search(r"<h4>\s*<strong>\s*Sizes?\s*</strong>\s*</h4>", page)
    if not heading:
        return None  # samplers, accessories, pages with no published sizes
    tail = page[heading.end():]
    tail = tail[:tail.find("<section")] if "<section" in tail else tail[:3000]
    text = _text(re.sub(r"</(li|p|span|div)>", " | ", tail))
    sizes = []
    for m in re.finditer(r"([A-Za-z][A-Za-z()' .-]{0,40}?)?\s*[:–—-]?\s*(\d(?:\.\d+)?(?:\s+\d/\d+)?\s*x\s*\d{2,3})", text):
        length, ring = dimensions(m.group(2))
        if ring is None:
            continue
        name = size_name((m.group(1) or "").strip(" |:–—-")) or f"{m.group(2).replace(' ', '')}"
        sizes.append(Vitola(name=name, length_in=length, ring_gauge=ring))
    if not sizes:
        return None

    # Blend facts: labelled fields in the page text, each running to the next label.
    body_text = _text(re.sub(r"</(li|p|span|div|h\d)>", " | ", page[page.find("<body"):]))
    def field(label):
        m = re.search(rf"\b{label}\s*:\s*(.+?)\s*(?:\||Wrapper:|Binder:|Filler:|Strength|Sizes?\b|$)", body_text, re.I)
        return clean_value(m.group(1).strip(" |")) if m else None
    strength = None
    m = re.search(r"Strength[^:]*:\s*(\d)\s*(?:out of|/)\s*5", body_text, re.I)
    if m:
        strength = STRENGTH_1_5.get(m.group(1))
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    # Kristoff names most lines after the wrapper; when the wrapper text only gives the origin
    # ("Ecuadorian" on the Connecticut page), the line name carries the leaf.
    wrapper_raw = field("Wrapper")
    if wrapper_raw and line and not re.search(r"connecticut|broadleaf|habano|corojo|criollo|sumatra|cameroon|san andr|maduro|candela|shade", wrapper_raw, re.I):
        wrapper_raw = f"{wrapper_raw} {line}"

    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=wrapper_raw, binder=field("Binder"), filler=field("Filler"),
        body=strength, band_image_url=og.group(1) if og else None, vitolas=sizes,
    )
