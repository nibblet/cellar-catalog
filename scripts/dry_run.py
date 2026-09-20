"""Parse every cached page for a source and diff against a catalog export. Writes nothing.
usage: dry_run.py <source> <cache dir> <export.json>"""
import importlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.diff import compare
from catalog import overrides

src = importlib.import_module(f"catalog.sources.{sys.argv[1]}")
f = Fetcher(Path(sys.argv[2]), delay_seconds=getattr(src, "DELAY", 10))
records = []
for u in src.list_urls(f):
    p = f._path(u)
    if p.exists():
        r = src.parse(u, p.read_text(encoding="utf-8"))
        if r:
            records.extend(r if isinstance(r, list) else [r])  # a page may yield one record per wrapper
if hasattr(src, "group"):
    records = src.group(records)  # sources with a page per size
catalog = json.loads(Path(sys.argv[3]).read_text())
override_sql = overrides.apply(catalog, getattr(src, "OVERRIDES", {}))
rep = compare(records, catalog)

print(f"site: {len(records)} lines, {sum(len(r.vitolas) for r in records)} sizes · catalog: {len(catalog)} rows\n")
print(f"MATCHED {len(rep.matched)}")
print(f"CORRECTIONS {len(rep.corrections)}")
for e in rep.corrections:
    print(f"  {e['brand']} / {e['catalog_line']} / {e['size']}  —  " + ", ".join(f"{k}: {a} → {b}" for k, (a, b) in e["diffs"].items()))
print(f"\nADDITIONS {len(rep.additions)}")
by_line = {}
for e in rep.additions:
    by_line.setdefault(f"{e['brand']} — {e['line'] or '(flagship)'}", []).append(f"{e['size']} ({e['dims']})" + (f" [leaf {e['leaf']} from siblings]" if e.get("leaf_inherited") else ""))
for line, sizes in sorted(by_line.items()):
    print(f"  {line}: {', '.join(sizes)}")
print(f"\nOVERRIDES (re-filed by hand in the source module) {len(override_sql)}")
for s in override_sql: print("  " + s)
print(f"\nLINE ALIASES {len(rep.aliases)}")
for a in sorted({(e['brand'], e['line'], e['alias']) for e in rep.aliases}): print(f"  {a[0]} / {a[1]}  ← was '{a[2]}'")
print(f"\nNEW LINES {len(rep.new_lines)}")
for l in rep.new_lines: print("  " + l)
print(f"\nPLACEHOLDERS (line exists, row has no size) {len(rep.placeholders)}")
for r in rep.placeholders: print(f"  {r['brand']} / {r['line']}")
print(f"\nSTALE {len(rep.stale)}")
for r in rep.stale: print(f"  {r['brand']} / {r['line']} / {r['expression']}  {r['length_in']}x{r['ring_gauge']}")
print(f"\nparse gaps: {sum(1 for r in records if not r.body)} without strength, {sum(1 for r in records if not r.wrapper_raw)} without wrapper, {sum(1 for r in records if not r.band_image_url)} without image")
print("\nLINES PARSED"); [print(f"  {r.line}: {len(r.vitolas)} sizes · {r.wrapper_raw} · {r.body}") for r in records]
