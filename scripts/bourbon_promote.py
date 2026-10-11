"""List the live catalog rows a source module calls core that are still hidden or not marked core, and print one
UPDATE that promotes them. The writer now does this per run (catalog/bourbon/write.py); this is the one-time backfill
for rows matched by earlier runs. Reads the live catalog, never writes.
usage: bourbon_promote.py <module>:<cache dir> ...   (CELLAR_ENV_FILE must be set, as for export.py)"""
import importlib, json, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.bourbon.diff import compare

ids: dict[str, str] = {}
for pair in sys.argv[1:]:
    module, cache = pair.split(":")
    src = importlib.import_module(f"catalog.sources.{module}")
    out = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    subprocess.run([sys.executable, str(Path(__file__).parent / "export.py"), "--type", "bourbon", "--source", module, out], check=True, capture_output=True)
    f = Fetcher(Path(cache), delay_seconds=getattr(src, "DELAY", 10))
    records = []
    for u in src.list_urls(f):
        if f._path(u).exists():
            r = src.parse(u, f._path(u).read_text(encoding="utf-8"))
            if r:
                records.extend(r if isinstance(r, list) else [r])
    catalog = {r["id"]: r for r in json.loads(Path(out).read_text())}
    rep = compare(records, list(catalog.values()))
    for r in rep.matched + rep.corrections:
        row = catalog[r["id"]]
        if r.get("core") and not row.get("facts_verified_at") and not row.get("discontinued") and not (row.get("is_core_range") and row.get("catalog_included")):
            ids[r["id"]] = f"{module}: {row['name']}"
for i, n in ids.items():
    print(f"-- {n}")
print(f"-- {len(ids)} rows")
if ids:
    print("update cellar.products set is_core_range = true, catalog_included = true where id in (" + ", ".join(f"'{i}'" for i in ids) + ") and facts_verified_at is null;")
