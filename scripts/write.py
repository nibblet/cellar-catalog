"""Emit SQL for a source's import: part1 (corrections, aliases, discontinued, images) and JSON insert
batches. Never connects. usage: write.py <source> <cache> <export.json> <out dir> [--maker UUID] [--country X] [--stale-only id,id]"""
import argparse, importlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.diff import compare
from catalog import overrides
from catalog.normalize import shape
from catalog.write import _name, statements

ap = argparse.ArgumentParser()
ap.add_argument("source"); ap.add_argument("cache"); ap.add_argument("export"); ap.add_argument("out")
ap.add_argument("--maker"); ap.add_argument("--country"); ap.add_argument("--series", default="")
ap.add_argument("--stale-only", help="comma-separated ids allowed to be marked discontinued (default: all stale)")
a = ap.parse_args()
src = importlib.import_module(f"catalog.sources.{a.source}")
f = Fetcher(Path(a.cache), delay_seconds=getattr(src, "DELAY", 10))
records = []
for u in src.list_urls(f):
    if f._path(u).exists():
        r = src.parse(u, f._path(u).read_text())
        if r:
            records.extend(r if isinstance(r, list) else [r])  # a page may yield one record per wrapper
if hasattr(src, "group"):
    records = src.group(records)  # sources with a page per size
catalog = json.loads(Path(a.export).read_text())
series = set(a.series.split(",")) if a.series else set()
override_sql = overrides.apply(catalog, getattr(src, "OVERRIDES", {}), series)
rep = compare(records, catalog)
if a.stale_only is not None:
    allowed = set(a.stale_only.split(",")) if a.stale_only else set()
    rep.stale = [r for r in rep.stale if r["id"] in allowed]
country = a.country or getattr(src, "COUNTRY", None)
brands = {r.brand for r in records}
image_prefix = getattr(src, "IMAGE_PREFIX", "https://" + src.SITEMAP.split("/")[2] + "/")
stmts = statements(rep, maker_id=a.maker, country_by_brand={b: country for b in brands} if country else {}, series_brands=series, image_prefix=image_prefix)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
(out / "part1.sql").write_text("\n".join(override_sql + [s for s in stmts if not s.startswith("insert into cellar.products (")]))
line_of = {}
rows = []
for e in rep.additions:
    shp, box = e["shape"], e["box_pressed"]; L, R = e["dims"].split(" x ")
    line = line_of.get((e["brand"], e["line"]), e["line"])
    rows.append({"n": _name(e["brand"], line, e["size"], series), "b": e["brand"], "l": line, "x": e["size"],
                 "len": float(L) if L != "None" else None, "rg": int(R) if R != "None" else None, "sh": shp, "bp": box,
                 "wl": e["leaf"] if e["leaf"] != "other" else "unknown", "wo": e["origin"], "ws": e["shade"], "bd": e["body"],
                 "bi": e["binder"], "fi": e["filler"], "c": e.get("country") or country, "img": e["size_image"] or e["band"], "u": e["source_url"]})
maker_sql = f"'{a.maker}'::uuid" if a.maker else "null"
# image_url stays null: the crawled address is the maker's, not ours to display, and not ours
# to rely on. It is kept in specs as source_image_url — see catalog/write.py._source_image.
head = ("insert into cellar.products (type, name, brand, line, expression, length_in, ring_gauge, shape, box_pressed, wrapper_leaf, wrapper_origin, wrapper_shade, body, strength, binder, filler, country, producer_id, image_url, source, source_url, source_checked_at, status, catalog_included, specs)\n"
        f"select 'cigar', r.n, r.b, r.l, r.x, r.len, r.rg, r.sh::cellar.cigar_shape, r.bp, r.wl::cellar.wrapper_leaf, r.wo, r.ws::cellar.wrapper_shade, r.bd::cellar.cigar_strength, r.bd::cellar.cigar_strength, r.bi, r.fi, r.c, {maker_sql}, null, 'maker', r.u, now(), 'confirmed', true,\n"
        "       case when r.img is null then '{{}}'::jsonb else jsonb_build_object('source_image_url', r.img) end\n"
        "from jsonb_to_recordset($j$")
tail = "$j$::jsonb) as r(n text, b text, l text, x text, len numeric, rg int, sh text, bp bool, wl text, wo text, ws text, bd text, bi text, fi text, c text, img text, u text);"
for i in range(0, len(rows), 45):
    (out / f"inserts_{i // 45 + 1}.sql").write_text(head + json.dumps(rows[i:i + 45], ensure_ascii=False, separators=(",", ":")) + tail)
print(f"{len(rep.corrections)} corrections, {len(rows)} additions in {(len(rows) + 44) // 45} batches, {len(rep.stale)} discontinued, {len(rep.aliases)} aliases, {len(rep.placeholders)} placeholders left alone")
