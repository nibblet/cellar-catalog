"""Export the catalog rows a source will be diffed against, as export.json. Reads the service-role key
from the environment (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) or from --env-file (a Next-style
.env.local also works: NEXT_PUBLIC_SUPABASE_URL is accepted). Read-only.

usage: export.py --type bourbon --families "Eagle Rare,Weller" [--producer "Buffalo Trace"] out.json
       export.py --type cigar --brands "Padron" out.json
       export.py --type bourbon --source bourbon.buffalo_trace out.json   # families from the module
"""
import argparse, importlib, json, os, sys, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BOURBON_COLS = ("id,name,brand,brand_family,expression,release_label,producer,producer_id,proof,age_years,age_label,nas,"
                "spirit_type,mash_style,mash_bill,expression_type,bottled_in_bond,barrel_proof,finish,msrp_usd,rarity,"
                "image_url,source,source_url,source_checked_at,aliases,facts_verified_at,catalog_included,is_core_range,discontinued,status,"
                "source_image:specs->>source_image_url")  # the maker's image address lives in specs now, not image_url
CIGAR_COLS = ("id,name,brand,line,expression,length_in,ring_gauge,shape,box_pressed,wrapper_leaf,wrapper_origin,wrapper_shade,"
              "strength,body,binder,filler,country,producer_id,image_url,source,source_url,aliases,facts_verified_at,catalog_included,discontinued")


def load_env(path: str | None):
    if path:
        for line in Path(path).read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or --env-file)")
    return url.rstrip("/"), key


def fetch(url, key, table, params, page=1000):
    rows, start = [], 0
    while True:
        q = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        req = urllib.request.Request(f"{url}/rest/v1/{table}?{q}", headers={
            "apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": "cellar",
            "Range-Unit": "items", "Range": f"{start}-{start + page - 1}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            batch = json.loads(r.read())
        rows.extend(batch)
        if len(batch) < page:
            return rows
        start += page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, choices=["bourbon", "cigar"])
    ap.add_argument("--families", help="comma-separated brand_family values (bourbon)")
    ap.add_argument("--brands", help="comma-separated brand values (cigar)")
    ap.add_argument("--producer", help="also every row with this producer text (bourbon)")
    ap.add_argument("--source", help="a source module; its CATALOG_FAMILIES / PRODUCER (bourbon) or BRAND (cigar) set the filter")
    ap.add_argument("--env-file", default=os.environ.get("CELLAR_ENV_FILE"))
    ap.add_argument("out")
    a = ap.parse_args()
    url, key = load_env(a.env_file)

    families, brands, producer = set(), set(), a.producer
    if a.source:
        src = importlib.import_module(f"catalog.sources.{a.source}")
        families |= set(getattr(src, "CATALOG_FAMILIES", []))
        producer = producer or getattr(src, "PRODUCER", None)
        if getattr(src, "BRAND", None):
            brands.add(src.BRAND)
    families |= {f.strip() for f in (a.families or "").split(",") if f.strip()}
    brands |= {b.strip() for b in (a.brands or "").split(",") if b.strip()}

    cols = BOURBON_COLS if a.type == "bourbon" else CIGAR_COLS
    ors = []
    if families:
        ors.append("brand_family.in.(" + ",".join('"' + f.replace('"', '\\"') + '"' for f in sorted(families)) + ")")
    if brands:
        ors.append("brand.in.(" + ",".join('"' + b + '"' for b in sorted(brands)) + ")")
    if producer and a.type == "bourbon":
        ors.append(f'producer.eq."{producer}"')
    if not ors:
        sys.exit("nothing to filter on: give --families / --brands / --producer / --source")
    params = {"select": cols, "type": f"eq.{a.type}", "merged_into": "is.null", "or": "(" + ",".join(ors) + ")", "order": "name"}
    rows = fetch(url, key, "products", params)
    Path(a.out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{len(rows)} rows → {a.out}  (families: {len(families)}, producer: {producer or '-'})")


if __name__ == "__main__":
    main()
