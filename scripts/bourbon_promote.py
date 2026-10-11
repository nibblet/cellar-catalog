"""One-time backfill for rows matched by earlier runs. For every live catalog row a source module matches it prints
(1) UPDATEs filling a missing rarity from that module's own RARITY table (never overwrites one that is set) and
(2) one UPDATE promoting rows the module calls core that are still hidden or not marked core.
The writer now does both per run (catalog/bourbon/write.py). Reads the live catalog, never writes.
usage: bourbon_promote.py <module>:<cache dir> ...   (CELLAR_ENV_FILE must be set, as for export.py)"""
import importlib, json, subprocess, sys, tempfile
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.bourbon.diff import compare
from catalog.bourbon.write import rarity_for

rarity_ids: dict[str, dict[str, str]] = defaultdict(dict)  # rarity → {id: label}
promote: dict[str, tuple[str, str]] = {}                   # id → (label, rarity or '')
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
    table = list(getattr(src, "RARITY", ()))
    for r in compare(records, list(catalog.values())).matched + compare(records, list(catalog.values())).corrections:
        row = catalog[r["id"]]
        if row.get("facts_verified_at") or row.get("discontinued"):
            continue
        rar = rarity_for(r["name"], table)
        if rar and not row.get("rarity"):
            rarity_ids[rar][r["id"]] = f"{module}: {row['name']}"
        if r.get("core") and not (row.get("is_core_range") and row.get("catalog_included")):
            promote[r["id"]] = (f"{module}: {row['name']} [{'hidden' if not row.get('catalog_included') else 'visible'}]", rar if rar and not row.get("rarity") else "")
for rar, d in rarity_ids.items():
    print(f"-- rarity {rar}: {len(d)} rows")
for i, (n, _) in promote.items():
    print(f"-- promote {n}")
print(f"-- {sum(len(d) for d in rarity_ids.values())} rarity fills, {len(promote)} promotions")
for rar, d in rarity_ids.items():
    print(f"update cellar.products set rarity = '{rar}'::cellar.rarity where rarity is null and id in (" + ", ".join(f"'{i}'" for i in d) + ") and facts_verified_at is null;")
if promote:
    print("update cellar.products set is_core_range = true, catalog_included = true where id in (" + ", ".join(f"'{i}'" for i in promote) + ") and facts_verified_at is null;")
