"""alecbradley.com — Nuxt 3 / Strapi CMS. Every /cigars/<slug> page embeds its full product record
as a devalue-serialized array in a <script id="__NUXT_DATA__"> tag: wrapper/binder/filler/body as
plain strings, sizes as a markdown list ("- Robusto — 5 X 50"). Fine & Rare's annual releases are
filed as child products with `parent` pointing at the "Fine & Rare" line; every other product page
is its own line, named after its own title. No page states where the cigar is rolled (only, on a
few pages, the province a tobacco was grown in), so country stays unknown throughout."""
from __future__ import annotations

import json
import re

from ..model import LineRecord, Vitola
from ..normalize import dimensions

DELAY = 3  # robots.txt states no crawl-delay
SITE = "https://www.alecbradley.com"
SITEMAP = SITE + "/sitemap.xml"
IMAGE_PREFIX = "https://d25bsrltkk1hnl.cloudfront.net/public/gccstrapi/"
BRAND = "Alec Bradley"

_SPECIAL_REFS = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef", "NuxtError"}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(u for u in re.findall(r"<loc>([^<]+)</loc>", xml) if re.search(r"/cigars/[^/]+$", u))


def _resolve(arr: list, i: int, seen: frozenset = frozenset()):
    if i in seen:
        return None
    v = arr[i]
    if isinstance(v, list):
        if v and isinstance(v[0], str) and v[0] in _SPECIAL_REFS:
            return _resolve(arr, v[1], seen | {i})
        return [_resolve(arr, x, seen | {i}) if isinstance(x, int) else x for x in v]
    if isinstance(v, dict):
        return {k: (_resolve(arr, x, seen | {i}) if isinstance(x, int) else x) for k, x in v.items()}
    return v


def _product(page: str) -> dict | None:
    m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        return None
    arr = json.loads(m.group(1))
    root = _resolve(arr, 1)
    keys = [k for k in root if k.startswith("product-")]
    return root[keys[0]] if keys else None


NAME_FIX = re.compile(r"\*+$")  # footnote markers on a size name ("Perfecto*")


def _sizes(text: str | None, prefix: str | None) -> list[Vitola]:
    vitolas = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = re.match(r"-\s*(.+?)\s*—\s*(.+)$", line)
        if not m:
            continue
        name, dims = m.groups()
        name = NAME_FIX.sub("", name).strip()
        # a handful of lines shout their size names in full caps; title-case real words back to the
        # site's own normal style, but leave short codes and anything with a digit/parenthesis alone
        # (XL, PL #4, DBL Churchill) rather than mangle an abbreviation into "Xl" or "Pl #4"
        if name.isupper() and not re.search(r"[\d#()]", name) and len(re.sub(r"[ -]", "", name)) > 3:
            name = name.title()
        length_in, ring = dimensions(dims)
        if length_in is None or ring is None:
            continue
        vitolas.append(Vitola(name=f"{prefix} {name}" if prefix else name, length_in=length_in, ring_gauge=ring))
    return vitolas


def parse(url: str, page: str) -> LineRecord | None:
    prod = _product(page)
    if not prod:
        return None
    parent = prod.get("parent")
    if isinstance(parent, dict):
        line = parent.get("title")
        code = re.sub(r"^\s*" + re.escape(line or "") + r"\s*", "", prod.get("title") or "", flags=re.I).strip()
    else:
        line = prod.get("title")
        code = None
    vitolas = _sizes(prod.get("sizes"), code)
    if not vitolas:
        return None
    body = (prod.get("body") or "").replace("Mellow", "Mild")
    stick = prod.get("stick") or prod.get("thumbnail") or {}
    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=prod.get("wrapper"), binder=prod.get("binder"), filler=prod.get("filler"),
        body=body or None, band_image_url=stick.get("url"), vitolas=vitolas,
    )
