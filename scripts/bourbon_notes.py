"""The maker's own tasting notes, from the pages the importers already cached, as `product_reviews` rows that the web
app's wheel extraction (`pnpm seed:enrich --type bourbon`, gpt-5-nano) turns into a baseline taste wheel.

    bourbon_notes.py measure            read-only: how many live rows without a wheel have maker notes with real flavors
    bourbon_notes.py emit <out.sql>     the idempotent INSERTs (one review per product and page; source = the maker's domain)

Nothing here crawls: each module's `list_urls` runs against a no-network fetcher that looks in every cache directory,
and a bottling is only read when its page is already cached. The notes are `rec.tasting_notes or rec.description`
(modules that parse neither contribute nothing). A blurb counts only if it names at least MIN_TERMS distinct flavors
from the wheel's own leaves and synonyms, grain, oak and 'smoke' excluded because mash bills and cask lines name them
without describing taste. Rows that already have a real wheel are skipped; the wheel extraction only targets empty ones.
Env as export.py: CELLAR_ENV_FILE=/Volumes/Lexar/cellar/apps/web/.env.local"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pkgutil
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalog.bourbon.diff import compare  # noqa: E402
from catalog.fetch import Fetcher  # noqa: E402
import catalog.sources.bourbon as bourbon_pkg  # noqa: E402

WHEEL = Path("/Volumes/Lexar/cellar/apps/web/src/lib/wheel/data/bourbon-wheel-v1.json")
NOT_FLAVOR = {"corn", "rye", "malt", "oak", "charred-oak", "smoke", "bread"}  # named by mash bills and cask lines
MIN_TERMS = 3
MAX_CHARS = 1200


def _load_export():
    spec = importlib.util.spec_from_file_location("export_mod", ROOT / "scripts" / "export.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flavor_terms() -> dict[str, re.Pattern]:
    leaves = json.loads(WHEEL.read_text())["leaves"]
    out = {}
    for leaf in leaves:
        if leaf["id"] in NOT_FLAVOR:
            continue
        words = {leaf["label"].lower(), *(s.lower() for s in leaf["synonyms"])}
        out[leaf["id"]] = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")s?\b", re.I)
    return out


class OfflineFetcher(Fetcher):
    """Serves any cached page from any cache directory; never touches the network."""

    def __init__(self, dirs: list[Path]):
        super().__init__(dirs[0], delay_seconds=0)
        self.dirs = dirs

    def _find(self, url: str) -> Path | None:
        name = self._path(url).name
        for d in self.dirs:
            if (d / name).exists():
                return d / name
        return None

    def get(self, url, *, refresh=False):
        p = self._find(url)
        if p is None:
            raise FileNotFoundError(url)
        return p.read_text(encoding="utf-8")

    def post(self, key_, url, body, headers, *, refresh=False):
        p = self._find(key_)
        if p is None:
            raise FileNotFoundError(key_)
        return p.read_text(encoding="utf-8")


def read_pages():
    """(module name, module, [(url, page text)]) for every importer whose pages are cached."""
    dirs = [d for d in sorted((ROOT / "cache").iterdir()) if d.is_dir()]
    fetcher = OfflineFetcher(dirs)
    for info in pkgutil.iter_modules(bourbon_pkg.__path__):
        name = info.name
        try:
            src = importlib.import_module(f"catalog.sources.bourbon.{name}")
            urls = src.list_urls(fetcher)
        except Exception:
            continue
        pages = []
        for u in urls:
            p = fetcher._find(u)
            if p is not None:
                pages.append((u, p.read_text(encoding="utf-8")))
        if pages:
            yield name, src, pages


def notes_of(rec) -> str | None:
    text = rec.tasting_notes or rec.description
    if not text:
        return None
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    return text[:MAX_CHARS] if text else None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "measure"
    ex = _load_export()
    url, svc = ex.load_env(os.environ.get("CELLAR_ENV_FILE"))
    terms = flavor_terms()

    def hits(text: str) -> list[str]:
        return [leaf for leaf, pat in terms.items() if pat.search(text)]

    rows_by_id: dict[str, dict] = {}
    per_module = []
    candidates: dict[str, dict] = {}  # product_id -> best note

    for name, src, pages in read_pages():
        records = []
        for u, page in pages:
            try:
                r = src.parse(u, page)
            except Exception:
                continue
            if r:
                records.extend(r if isinstance(r, list) else [r])
        if not records:
            continue
        fams = sorted(set(getattr(src, "CATALOG_FAMILIES", [])) | {r.brand_family for r in records})
        ors = ["brand_family.in.(" + ",".join('"' + f.replace('"', '\\"') + '"' for f in fams) + ")"]
        producer = getattr(src, "PRODUCER", None)
        if producer:
            ors.append(f'producer.eq."{producer}"')
        params = {"select": ex.BOURBON_COLS + ",wheel_vector", "type": "eq.bourbon", "merged_into": "is.null", "or": "(" + ",".join(ors) + ")"}
        rows = ex.fetch(url, svc, "products", params)
        rep = compare(records, rows)
        by_key = {}
        for rec in records:
            n = notes_of(rec)
            if n:
                by_key[(rec.source_url, rec.name)] = (n, rec)
        n_notes = sum(1 for n, _ in by_key.values() if len(hits(n)) >= MIN_TERMS)
        covered = new = 0
        for f in rep.matched + rep.corrections:
            row = next((r for r in rows if r["id"] == f["id"]), None)
            if row is None:
                continue
            rows_by_id[row["id"]] = row
            got = by_key.get((f["source_url"], f["name"]))
            if not got or len(hits(got[0])) < MIN_TERMS:
                continue
            covered += 1
            has_wheel = bool(row.get("wheel_vector"))
            if row.get("catalog_included") and not has_wheel:
                new += 1
                candidates[row["id"]] = {
                    "product_id": row["id"], "name": row["name"], "text": got[0], "source_url": f["source_url"],
                    "source": urlparse(f["source_url"]).netloc.removeprefix("www."), "reviewer": producer or name,
                    "terms": hits(got[0]),
                }
        per_module.append((name, len(records), len(by_key), n_notes, covered, new))

    print(f"{'module':24} {'recs':>5} {'notes':>5} {'flavor':>6} {'matched':>7} {'new wheels':>10}")
    for r in sorted(per_module, key=lambda r: -r[5]):
        print(f"{r[0]:24} {r[1]:5} {r[2]:5} {r[3]:6} {r[4]:7} {r[5]:10}")
    tot = Counter()
    for r in per_module:
        tot.update({"recs": r[1], "notes": r[2], "flavor": r[3], "new": r[5]})
    live_no_wheel = [r for r in rows_by_id.values() if r.get("catalog_included") and not r.get("wheel_vector")]
    print(f"\n{len(per_module)} importers with cached pages; {tot['recs']} records; {tot['notes']} with any notes text; "
          f"{tot['flavor']} with >= {MIN_TERMS} flavors; {len(candidates)} live rows without a wheel would get a maker-notes review "
          f"(of {len(live_no_wheel)} live importer-matched rows without a wheel)")
    cnt = Counter(t for c in candidates.values() for t in c["terms"])
    print("flavors named most:", ", ".join(f"{k} {v}" for k, v in cnt.most_common(12)))

    if mode == "emit":
        out = Path(sys.argv[2])
        payload = [{k: c[k] for k in ("product_id", "source", "source_url", "reviewer", "text")} for c in candidates.values()]
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        print(f"{len(payload)} reviews → {out}")


if __name__ == "__main__":
    main()
