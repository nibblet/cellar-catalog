"""mayflowercigars.com — BigCommerce, one product page per *size*. Facts sit in a
productView-info list (Size / Length / Ring Gauge / Wrapper / Binder / Filler / Body).
Pages are grouped into lines here, since the rest of the pipeline thinks per line."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import clean_value, dimensions

BRAND = "Mayflower"
COUNTRY = None  # the site never says where the cigars are rolled; pass --country if known
DELAY = 10  # robots.txt asks 10 s of AI crawlers; we oblige
SITEMAP = "https://mayflowercigars.com/xmlsitemap.php?type=products&page=1"
IMAGE_PREFIX = "https://cdn11.bigcommerce.com/s-wmtyhjau0f/"

# Samplers, bundles and accessories are product pages too; they have no Ring Gauge field.
SKIP = re.compile(r"assortment|bundle|trinity|lighter|cutter|jacket|pack", re.I)


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = re.findall(r"<loc>(https://mayflowercigars\.com/[^<]+/)</loc>", xml)
    return sorted(u for u in set(urls) if not SKIP.search(u))


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").strip()


def _fields(page: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'<span class="productView-info-name[^"]*">(.*?)</span>\s*<span class="productView-info-value[^"]*">(.*?)</span>', page, re.S):
        out[_text(m.group(1)).rstrip(":").lower()] = _text(m.group(2))
    return out


def parse_page(url: str, page: str) -> tuple[str, Vitola, dict] | None:
    """→ (line, vitola, blend fields) for one size page, or None for non-cigar pages."""
    f = _fields(page)
    if "ring gauge" not in f:
        return None
    title = re.search(r'<h1 class="productView-title">(.*?)</h1>', page, re.S)
    name = _text(title.group(1)) if title else ""
    # "Mayflower Dream Box Pressed Toro (6 x 52)" → line "Dream", size "Box Pressed Toro"
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)
    if name.lower().startswith(BRAND.lower()):
        name = name[len(BRAND):].strip()
    size = f.get("size") or ""
    line = name
    # the title may spell the size more fully than the Size field ("Box Pressed Toro" vs "Toro")
    m = re.search(r"^(.*?)\s*((?:box[- ]pressed\s+)?" + re.escape(size) + r")$", name, re.I) if size else None
    if m:
        line, size = m.group(1).strip(), m.group(2)
    length, ring = dimensions(f"{f.get('length', '')} x {f['ring gauge']}")
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    v = Vitola(name=size or f"{length}x{ring}", length_in=length, ring_gauge=ring,
               image_url=og.group(1) if og else None, source_url=url)
    blend = {k: clean_value(f.get(k)) for k in ("wrapper", "binder", "filler", "body")}
    return line, v, blend


def parse(url: str, page: str) -> LineRecord | None:
    """One page = one size; the line record carries just that size. See `group`."""
    hit = parse_page(url, page)
    if not hit:
        return None
    line, v, b = hit
    return LineRecord(brand=BRAND, line=line, source_url=url, wrapper_raw=b["wrapper"], binder=b["binder"],
                      filler=b["filler"], body=b["body"], band_image_url=v.image_url, vitolas=[v])


def group(records: list[LineRecord]) -> list[LineRecord]:
    """Merge per-size records into one record per line (facts from the first page seen)."""
    by_line: dict[str, LineRecord] = {}
    for r in records:
        k = (r.line or "").lower()
        if k in by_line:
            by_line[k].vitolas.extend(r.vitolas)
        else:
            by_line[k] = LineRecord(brand=r.brand, line=r.line, source_url=re.sub(r"[^/]+/$", "", r.source_url),
                                    wrapper_raw=r.wrapper_raw, binder=r.binder, filler=r.filler, body=r.body,
                                    band_image_url=r.band_image_url, vitolas=list(r.vitolas))
    for rec in by_line.values():
        rec.vitolas.sort(key=lambda v: (v.length_in or 0, v.ring_gauge or 0))
    return list(by_line.values())
