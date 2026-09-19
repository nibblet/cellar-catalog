"""Parse every cached Drew Estate page and diff it against a catalog export (JSON). Writes nothing."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.sources.drew_estate import parse
from catalog.diff import compare

cache, catalog_path = Path(sys.argv[1]), Path(sys.argv[2])
f = Fetcher(cache, delay_seconds=10)
urls = sorted(set(re.findall(r"<loc>(https://drewestate\.com/products/[^<]+/)</loc>", f.get("https://drewestate.com/products-sitemap.xml"))))
records = []
for u in urls:
    p = f._path(u)
    if not p.exists():
        continue
    r = parse(u, p.read_text(encoding="utf-8"))
    if r:
        records.append(r)
catalog = json.loads(catalog_path.read_text())
rep = compare(records, catalog)

print(f"site: {len(records)} lines, {sum(len(r.vitolas) for r in records)} sizes · catalog: {len(catalog)} rows\n")
print(f"MATCHED {len(rep.matched)}")
print(f"CORRECTIONS {len(rep.corrections)}")
for e in rep.corrections:
    d = ", ".join(f"{k}: {a} → {b}" for k, (a, b) in e["diffs"].items())
    print(f"  {e['brand']} / {e['catalog_line']} / {e['size']}  —  {d}")
print(f"\nADDITIONS {len(rep.additions)}")
by_line = {}
for e in rep.additions:
    by_line.setdefault(f"{e['brand']} — {e['line'] or '(flagship)'}", []).append(f"{e['size']} ({e['dims']})")
for line, sizes in sorted(by_line.items()):
    print(f"  {line}: {', '.join(sizes)}")
print(f"\nLINE ALIASES {len(rep.aliases)}")
for e in {(e['brand'], e['catalog_line'], e['alias']) for e in rep.aliases}: print(f"  {e[0]} / {e[1]}  ← also '{e[2]}'")
print(f"\nNEW LINES (not in catalog at all) {len(rep.new_lines)}")
for l in rep.new_lines: print("  " + l)
print(f"\nSTALE (in catalog, not on site) {len(rep.stale)}")
for r in rep.stale:
    print(f"  {r['brand']} / {r['line']} / {r['expression']}  {r['length_in']}x{r['ring_gauge']}")
lines_wo_body = [r for r in records if not r.body]
print(f"\nparse gaps: {len(lines_wo_body)} lines without body, {sum(1 for r in records if not r.wrapper_raw)} without wrapper, {sum(1 for r in records if not r.band_image_url)} without band image")
