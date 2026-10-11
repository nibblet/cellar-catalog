"""Emit SQL for a bourbon source's import: part1.sql (corrections, confirmations, discontinued, images)
and inserts_N.sql batches. Never connects.
usage: bourbon_write.py <source> <cache> <export.json> <out dir> [--maker UUID] [--stale-only id,id]"""
import argparse, importlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.bourbon.diff import compare
from catalog.bourbon.write import insert_batches, statements

ap = argparse.ArgumentParser()
ap.add_argument("source"); ap.add_argument("cache"); ap.add_argument("export"); ap.add_argument("out")
ap.add_argument("--maker", help="cellar.makers id for producer_id on touched rows")
ap.add_argument("--stale-only", help="comma-separated ids allowed to be marked discontinued (default: none)", default="")
a = ap.parse_args()
src = importlib.import_module(f"catalog.sources.{a.source}")
f = Fetcher(Path(a.cache), delay_seconds=getattr(src, "DELAY", 10))
records = []
for u in src.list_urls(f):
    if f._path(u).exists():
        r = src.parse(u, f._path(u).read_text(encoding="utf-8"))
        if r:
            records.extend(r if isinstance(r, list) else [r])
catalog = json.loads(Path(a.export).read_text())
rep = compare(records, catalog)
allowed = {i for i in a.stale_only.split(",") if i}
rep.stale = [r for r in rep.stale if r["id"] in allowed]  # a maker's site is not exhaustive; stale is opt-in
producer = getattr(src, "PRODUCER", None)
image_prefix = getattr(src, "IMAGE_PREFIX", "https://" + src.SITEMAP.split("/")[2] + "/")
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
by_family = getattr(src, "PRODUCER_BY_FAMILY", {})  # a family with its own maker record (Maker's Mark under Beam)
(out / "part1.sql").write_text("\n".join(statements(rep, producer=producer, maker_id=a.maker, image_prefix=image_prefix, by_family=by_family, rarity=getattr(src, "RARITY", ()))))
for i, sql in enumerate(insert_batches(rep.additions, producer=producer, maker_id=a.maker, rarity=getattr(src, "RARITY", ()), by_family=by_family), 1):
    (out / f"inserts_{i}.sql").write_text(sql)
print(f"{len(rep.corrections)} corrections, {len(rep.matched)} confirmed, {len(rep.additions)} additions, {len(rep.stale)} discontinued → {out}")
