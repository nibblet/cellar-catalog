"""Emit the SQL for the Drew Estate import (stdout). Apply it yourself; this script never connects."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher
from catalog.sources.drew_estate import parse
from catalog.diff import compare
from catalog.write import statements

cache, catalog_path, maker_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
f = Fetcher(cache, delay_seconds=10)
urls = sorted(set(re.findall(r"<loc>(https://drewestate\.com/products/[^<]+/)</loc>", f.get("https://drewestate.com/products-sitemap.xml"))))
records = [r for u in urls if f._path(u).exists() for r in [parse(u, f._path(u).read_text())] if r]
rep = compare(records, json.loads(catalog_path.read_text()))

NICARAGUA = {"Liga Privada", "Undercrown", "Herrera Esteli", "Nica Rustica", "Kentucky Fire Cured", "Tabak Especial",
             "Pappy Van Winkle", "Blackened", "20 Acre Farm", "Acid", "MUWAT", "Larutan", "Natural", "Ambrosia", "Java", "Factory Smokes"}
sql = statements(rep, maker_id=maker_id, country_by_brand={b: "Nicaragua" for b in NICARAGUA},
                 series_brands={"Acid"}, keep_line_for={"Liga Privada"} if False else set())
print("begin;")
print("\n".join(sql))
print("commit;")
print(f"-- {len(rep.corrections)} corrections, {len(rep.additions)} additions, {len(rep.stale)} discontinued, {len(rep.aliases)} aliases", file=sys.stderr)
