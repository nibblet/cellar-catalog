"""Parse every cached page for a bourbon source and diff against a catalog export. Writes nothing.
usage: bourbon_dry_run.py <source> <cache dir> <export.json>     e.g. bourbon.buffalo_trace cache/bt export.json"""
import importlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.bourbon.diff import compare
from catalog.bourbon.write import rarity_for

src = importlib.import_module(f"catalog.sources.{sys.argv[1]}")
f = Fetcher(Path(sys.argv[2]), delay_seconds=getattr(src, "DELAY", 10))
records, missing = [], 0
for u in src.list_urls(f):
    p = f._path(u)
    if not p.exists():
        missing += 1; continue
    r = src.parse(u, p.read_text(encoding="utf-8"))
    if r:
        records.extend(r if isinstance(r, list) else [r])
catalog = json.loads(Path(sys.argv[3]).read_text())
rep = compare(records, catalog)

def fx(f):  # one line of facts
    return f"{f['proof']} pf · {f['age_label'] or 'no age'} · {f['spirit_type']} · {f['mash_style'] or 'mash ?'}" + (" · BiB" if f['bottled_in_bond'] else "") + (" · BP" if f['barrel_proof'] else "") + (f" · finish {f['finish']}" if f['finish'] else "")

print(f"site: {len(records)} bottlings ({missing} pages not cached) · catalog: {len(catalog)} rows\n")
print(f"MATCHED {len(rep.matched)}")
for e in rep.matched: print(f"  {e['name']}  ← {e['catalog_name']}" + ("  [verified]" if e['verified'] else ""))
print(f"\nCORRECTIONS {len(rep.corrections)}")
for e in rep.corrections:
    print(f"  {e['catalog_name']}" + ("  [verified — will be skipped]" if e['verified'] else "") + "\n      " + ", ".join(f"{k}: {a} → {b}" for k, (a, b) in e["diffs"].items()))
print(f"\nADDITIONS {len(rep.additions)}")
for e in rep.additions: print(f"  {e['name']}  —  {fx(e)} · {rarity_for(e['name'], getattr(src, 'RARITY', [])) or 'rarity ?'}" + ("" if e['core'] else "  [not core]"))
print(f"\nNEW FAMILIES {len(rep.new_families)}"); [print("  " + x) for x in rep.new_families]
print(f"\nSTALE (in a family the site covers, not on the site) {len(rep.stale)}")
for r in rep.stale: print(f"  {r['name']}  [{r['source']}{', included' if r['catalog_included'] else ''}]  {r['id']}")
print(f"\nSKIPPED (not whiskey) {len(rep.skipped)}"); [print("  " + x) for x in rep.skipped]
print(f"\nparse gaps: {sum(1 for r in records if r.proof is None)} without proof, {sum(1 for r in records if r.age_years is None)} without an age, "
      f"{sum(1 for r in records if not r.mash_raw)} without a mash statement, {sum(1 for r in records if not r.image_url)} without image")
print("\nBOTTLINGS PARSED"); [print(f"  {r.brand_family} › {r.expression or '(flagship)'}: {r.proof} pf · {r.age_label or '—'} · {r.class_raw} · {r.mash_raw}") for r in records]
