"""us.davidoffgeneva.com — Davidoff of Geneva USA, a Next.js storefront over BigCommerce. Product
facts live in BigCommerce custom fields and metafields, read through the site's own
`bigCommerceRestAPI` server action (the same call the product page makes). The action id comes
from the page's JS and may change on a deploy; ACTION_ID is the only thing to update then.

One product per size. Own brands only: Davidoff, AVO, Camacho, Zino, Griffin's; the store also
carries Plasencia, Oliva, Ferio Tego and others, which stay with their makers."""
from __future__ import annotations

import json
import re
import unicodedata

from ..model import LineRecord, Vitola
from ..normalize import shape

SITE = "https://us.davidoffgeneva.com"
ACTION_ID = "40dd258988147a0f6e7010af14117175fa5e7c1f77"  # createServerReference(..., "bigCommerceRestAPI")
DELAY = 4
SITEMAP = SITE + "/sitemap.xml"  # only for IMAGE_PREFIX derivation in scripts
IMAGE_PREFIX = "https://p-cdn.davidoffgeneva.com/"
API = SITE + "/__api"  # synthetic URL prefix: everything after it is the BigCommerce path

BRANDS = {"Davidoff": "Davidoff", "Avo": "Avo", "Camacho": "Camacho", "Zino": "Zino", "Zino Platinum": "Zino Platinum", "Griffin's": "Griffin's"}
SKIP_LINES = {"Gift Selections", "Gift Sets"}
SKIP_NAMES = re.compile(r"Assortment|Gift Selection|\d Pack|Collector's Edition|–\s*(Father's Day|Happy New Year|Christmas|Mother's Day)\s+Band", re.I)  # samplers and band-only variants
# The store files some products with no Line; the line is the name's leading words.
LINE_PREFIXES = {
    "Davidoff": ["702 Series", "Voyager's Selection", "Maduro", "Signature", "Primeros by Davidoff", "Winston Churchill The Original Series", "Winston Churchill The Late Hour Series"],
    "Avo": ["Syncro Nicaragua Fogata", "Syncro Nicaragua", "Syncro South America Ritmo", "Syncro Caribe", "Syncro", "Heritage"],
    "Camacho": ["Ecuador"],
    "Zino": ["Nicaragua"],
    "Zino Platinum": ["Scepter", "Crown", "Z-Class"],
}
NO_EXTEND = {"Limited Edition", "Year of Edition", "Chefs Edition"}  # a release bucket, not a name fragment: the size is the whole name
LEAF_WORDS = r"connecticut broadleaf|broadleaf|connecticut|cameroon|sumatra|habano|corojo|criollo|candela|maduro|oscuro|colorado claro|sun ?grown"
# CURATED, not maker text (approved 2026-09-20): the store has no origin field and its copy names a
# country for three products only. Davidoff, AVO and Zino Platinum are rolled at Davidoff's own
# factories in Santiago, Dominican Republic; Camacho and Zino at Camacho's factory in Danlí,
# Honduras. The copy wins where it speaks (AVO Expresivo: "from Honduras").
COUNTRY_BY_BRAND = {"Davidoff": "Dominican Republic", "Avo": "Dominican Republic", "Zino Platinum": "Dominican Republic",
                    "Griffin's": "Dominican Republic", "Camacho": "Honduras", "Zino": "Honduras"}
COUNTRY_IN_COPY = re.compile(r"(?i)(?:hand-?made|hand-?crafted|crafted|made|rolled|produced|cigar)\s+(?:in|from)\s+(?:the\s+)?(Dominican Republic|Honduras|Nicaragua)")


def _intensity(v: str | None) -> str | None:
    """The store's 0–5 intensity (halves allowed) → the catalog's five words."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return "Mild" if x < 2 else "Mild-Medium" if x < 3 else "Medium" if x < 4 else "Medium-Full" if x < 5 else "Full"

# Catalog rows re-filed by hand: seed rows filed under a size or a half-line.
OVERRIDES = {
    "4cf3abcb-ee68-4ccc-bada-feca9d3fc6b6": {"line": "Classic", "expression": "No. 2"},         # Avo "Classic No. 2 / Toro"
    "911533ad-d080-4c6b-b336-00477978abdc": {"line": "XO", "expression": "Intermezzo"},        # Avo "XO Intermezzo"
    "850343c8-af70-4357-a174-0eb56f06c7f7": {"line": "Nicaragua", "expression": "Box Pressed Robusto"},
    "cdd9c949-3f20-4477-8f8f-d578c23d2072": {"line": "Signature", "expression": "2000"},
    "42590f89-2300-4d17-b7a8-acc6dfc836b9": {"line": "Winston Churchill The Original Series", "expression": "Churchill"},  # 6.88 x 47 is the Churchill, not a Toro
}

_META: dict[int, dict] = {}  # product id → {Wrapper, Binder, Filler}, filled by the metafields pages


def fetch(fetcher, url: str) -> str:
    """Synthetic URL → the site's server action → BigCommerce JSON (RSC-wrapped)."""
    path = url[len(API):]
    body = json.dumps([{"method": "GET", "url": path}])
    return fetcher.post(url, SITE + "/product/avo-expresivo-toro", body,  # any page path answers the action; a trailing-slash path 308s
                        {"Next-Action": ACTION_ID, "Content-Type": "text/plain;charset=UTF-8", "Accept": "text/x-component"})


def _flight(text: str) -> dict:
    """React flight format: `id:json` lines, with long strings hoisted into `id:T<hexlen>,<bytes>` chunks
    that the JSON refers to as "$id"."""
    data = text.encode("utf-8")
    chunks: dict[str, object] = {}
    i = 0
    while i < len(data):
        colon = data.index(b":", i)
        cid = data[i:colon].decode()
        if data[colon + 1:colon + 2] == b"T":
            comma = data.index(b",", colon)
            n = int(data[colon + 2:comma], 16)
            chunks[cid] = data[comma + 1:comma + 1 + n].decode("utf-8", errors="replace")
            i = comma + 1 + n
            if data[i:i + 1] == b"\n":
                i += 1
        else:
            nl = data.find(b"\n", colon)
            nl = len(data) if nl < 0 else nl
            raw = data[colon + 1:nl].decode("utf-8", errors="replace")
            try:
                chunks[cid] = json.loads(raw)
            except ValueError:
                chunks[cid] = raw
            i = nl + 1

    def resolve(v):
        if isinstance(v, str) and v.startswith("$") and v[1:] in chunks:
            return resolve(chunks[v[1:]])
        if isinstance(v, list):
            return [resolve(x) for x in v]
        if isinstance(v, dict):
            return {k: resolve(x) for k, x in v.items()}
        return v
    return resolve(chunks["1"])


def _body(text: str) -> dict:
    d = _flight(text)
    if d.get("status") != 200:
        raise RuntimeError(f"davidoff action returned {d.get('status')}")
    return d["body"]


def list_urls(fetcher) -> list[str]:
    products = f"{API}/v3/catalog/products?limit=250&include=custom_fields,primary_image&is_visible=true&page="
    first = _body(fetch(fetcher, products + "1"))
    pages = first["meta"]["pagination"]["total_pages"]
    urls = [products + str(n) for n in range(1, pages + 1)]
    ids = []
    for u in urls:
        for p in _body(fetch(fetcher, u))["data"]:
            f = {c["name"]: c["value"] for c in p.get("custom_fields", [])}
            if f.get("type") == "cigar" and f.get("Brand") in BRANDS:
                ids.append(p["id"])
    meta = [f"{API}/v3/catalog/products/metafields?key:in=Wrapper,Binder,Filler&limit=250&resource_id:in=" + ",".join(map(str, ids[i:i + 80]))
            for i in range(0, len(ids), 80)]
    return meta + urls  # metafields first: parse() needs them before the product pages


def parse(url: str, text: str):
    body = _body(text)
    if "/metafields?" in url:
        for m in body["data"]:
            if m["key"] in ("Wrapper", "Binder", "Filler"):
                _META.setdefault(m["resource_id"], {})[m["key"]] = m["value"]
        return None
    recs = []
    for p in body["data"]:
        f = {c["name"]: c["value"] for c in p.get("custom_fields", [])}
        if f.get("type") != "cigar" or f.get("Brand") not in BRANDS:
            continue
        brand = BRANDS[f["Brand"]]
        name = re.sub(r"[«»]", "", f.get("frontend_name") or p["name"]).strip()
        if (f.get("Line") or "").strip() in SKIP_LINES or SKIP_NAMES.search(name):
            continue
        line, size = _split(brand, f.get("Line") or "", name)
        if not size:
            continue
        L = float(f["Cigar length (in)"]) if f.get("Cigar length (in)") else None
        R = max(int(float(x)) for x in re.findall(r"\d+(?:\.\d+)?", f["Ring Gauge (RG)"])) if f.get("Ring Gauge (RG)") else None  # "50-61" perfectos
        if L is None or R is None:
            continue  # three store entries carry no dimensions at all; nothing to file
        fmt = (f.get("Shape and Format") or "").strip()
        shp = shape(fmt)[0] if fmt else None
        meta = _META.get(p["id"], {})
        # the store names wrapper origin; the line name sometimes carries the leaf ("Corojo", "Connecticut", "Triple Maduro")
        hint = " ".join(dict.fromkeys(w.lower() for w in re.findall(LEAF_WORDS, line or "", re.I)))
        wrapper_raw = " ".join(x for x in (meta.get("Wrapper"), hint) if x) or None
        text = re.sub(r"<[^>]+>", " ", p.get("description") or "") + " " + (p.get("meta_description") or "")
        country = (COUNTRY_IN_COPY.search(text) or [None, None])[1] or COUNTRY_BY_BRAND.get(brand)
        img = f.get("single_cigar_image_url") or ""
        if not re.search(r"\.(png|jpe?g|webp)(\?.*)?$", img, re.I):  # some DAM links are .psd/.tif masters
            img = (p.get("primary_image") or {}).get("url_zoom") or None
        url = SITE + "/product" + p["custom_url"]["url"]
        recs.append(LineRecord(
            brand=brand, line=line, source_url=url, wrapper_raw=wrapper_raw, binder=meta.get("Binder"), filler=meta.get("Filler"),
            body=_intensity(f.get("Intensity (0-5)")), country=country,
            vitolas=[Vitola(name=size, length_in=L, ring_gauge=R, image_url=img, source_url=url, shape=shp if shp and shp != "parejo" else None)],
        ))
    return recs


def _fold(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _split(brand: str, line: str, name: str) -> tuple[str | None, str]:
    """The store's Line field and marketing name → (catalog line, size name). The Line is often a
    fragment ("Nicaragua" for "Syncro Nicaragua Robusto", "The Original Series" for the Winston
    Churchill series): the catalog line is the name up to the end of that fragment, or a longer
    known prefix when the store's fragment is too short ("Primeros" for "Primeros by Davidoff")."""
    line = re.sub(r"[«»]", "", line).strip()
    if _fold(name).startswith(_fold(brand) + " "):
        name = name[len(brand) + 1:]  # "Griffin's Classic Robusto"
    if line == "Year of Edition":  # the store's bucket; the maker's names are "Year of the Dragon …"
        m = re.match(r"(Year of the \w+)\s*(.*)", name)
        if m:
            return m.group(1), (m.group(2) or m.group(1))
    if line in NO_EXTEND or (not line and "Limited Edition" in name):
        return (line or "Limited Edition"), name
    if line.endswith(" Series") and "Series" not in name:
        line = line[: -len(" Series")]  # "Classic Series" files "Classic No. 2"
    if line and _fold(line) in _fold(name):
        end = _fold(name).index(_fold(line)) + len(line)
        line = name[:end].strip()  # the name's own words and capitalisation
    # else: the store's Line stands even when the name doesn't repeat it ("Mini Cigarillos" / "Demi Tasse")
    for pfx in LINE_PREFIXES.get(brand, []):  # a longer known prefix beats the store's fragment
        if (_fold(name) + " ").startswith(_fold(pfx) + " ") and len(pfx) > len(line):
            line = name[: len(pfx)]
            break
    if line.isupper() and len(line) > 3:
        line = line.title()  # "EXPRESIVO" is marketing caps; "XO" is a name
    size = name[len(line):].strip(" –-") if line and _fold(name).startswith(_fold(line)) else name
    return (line or None), (size or (line or name))


def group(records: list[LineRecord]) -> list[LineRecord]:
    """One record per (brand, line, blend): a real line shares its facts, a release bucket like
    "Limited Edition" or "Primeros by Davidoff" holds several blends and keeps them apart. Each
    product page stays the row's own source."""
    by: dict[tuple, LineRecord] = {}
    for r in records:
        k = (r.brand, (r.line or "").lower(), r.wrapper_raw, r.binder, r.filler, r.body, r.country)
        if k in by:
            seen = {v.name.lower() for v in by[k].vitolas}
            by[k].vitolas.extend(v for v in r.vitolas if v.name.lower() not in seen)  # the store lists some sizes twice
        else:
            by[k] = LineRecord(brand=r.brand, line=r.line, source_url=r.source_url, wrapper_raw=r.wrapper_raw, binder=r.binder,
                               filler=r.filler, body=r.body, country=r.country, vitolas=list(r.vitolas))
    return list(by.values())
