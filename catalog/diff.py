"""Compare what a source says against what the catalog has. Read-only; produces a report."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import LineRecord
from .normalize import key, shape, strength, wrapper

# Brands the catalog files under a different brand than the maker's site does.
BRAND_ALIASES = {"Drew Estate": None}  # catalog uses 'Drew Estate' as a catch-all; match on line instead


def _line_key(brand: str, line: str | None) -> str:
    return key(brand) + "|" + key(line)


@dataclass
class Report:
    matched: list[dict] = field(default_factory=list)      # same size found; facts agree
    corrections: list[dict] = field(default_factory=list)  # same size found; facts differ
    additions: list[dict] = field(default_factory=list)    # site has it, catalog doesn't
    stale: list[dict] = field(default_factory=list)        # catalog has it, site doesn't
    aliases: list[dict] = field(default_factory=list)      # same product, maker names the line differently
    placeholders: list[dict] = field(default_factory=list) # line-level row with no size; line still exists
    new_lines: list[str] = field(default_factory=list)


def _catalog_index(rows: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for r in rows:
        keys = {_line_key(r["brand"], r["line"])}
        if r["brand"] in BRAND_ALIASES:
            # A row filed under the catch-all brand ("Drew Estate / Herrera Estelí Miami") is keyed
            # by its line text alone, so a real brand's page can claim it. Never for real brands:
            # "Undercrown / Maduro" must not answer to "Factory Smokes / Maduro".
            keys.add("|" + key(r["line"]))
        for k in keys:
            idx.setdefault(k, []).append(r)
    return idx


MADURO_LEAVES = {"connecticut_broadleaf", "brazilian", "san_andres"}


def _wrapper_compatible(r: dict, leaf: str) -> bool:
    """A Maduro row is not a Criollo line's size, however the names line up. Within the maduro
    family (Broadleaf / Brazilian / San Andrés) sources disagree often enough to let it through."""
    a, b = r.get("wrapper_leaf"), leaf
    if not a or not b or a in ("unknown", "other") or b in ("unknown", "other") or a == b:
        return True
    return (a in MADURO_LEAVES) == (b in MADURO_LEAVES)


def _find_line(idx, rec: LineRecord, site_lines: set = frozenset()) -> list[dict]:
    candidates = [
        _line_key(rec.brand, rec.line),
        "|" + key((rec.brand + " " + (rec.line or "")).strip()),   # catch-all rows carry the brand in the line
        "|" + key(rec.brand) if rec.line is None else None,
    ]
    # "UC 10" on the site vs "10" in the catalog: a short letter prefix before a number is the maker's shorthand.
    if rec.line:
        m = re.match(r"^[a-z]{1,3}(\d.*)$", key(rec.line))
        if m:
            candidates.append(_line_key(rec.brand, m.group(1)))
    seen: list[dict] = []
    for c in candidates:
        for r in idx.get(c or "", []):
            if r not in seen:
                seen.append(r)
    if not seen and rec.line:
        # "Unico" on the site, "Unico Serie" in the catalog: one is a prefix of the other, same brand.
        # Fuzzy, so the blend has to agree: "Kristania" (Broadleaf) is not a size of "Kristania Criollo".
        a = key(rec.line)
        leaf = wrapper(rec.wrapper_raw)[0]
        for rows in idx.values():
            for r in rows:
                b = key(r["line"])
                # …but a catalog line the site still lists by that exact name belongs to that page, not to a
                # longer-named sibling ("Excalibur" is not a size of "Excalibur Cameroon").
                if r not in seen and key(r["brand"]) == key(rec.brand) and b and a and (b.startswith(a) or a.startswith(b)) \
                        and _wrapper_compatible(r, leaf) and (key(rec.brand), b) not in site_lines:
                    seen.append(r)
    return seen


GENERIC_SIZES = {"robusto", "toro", "churchill", "torpedo", "belicoso", "corona", "lancero", "gordo", "gordito",
                 "perfecto", "lonsdale", "petitcorona", "coronagorda", "doublecorona", "grantoro", "torogrande", "robustogrande"}


def _line_eq(a: str | None, b: str | None, brand: str = "") -> bool:
    """Same line under the maker's naming habits: 'Unico' ~ 'Unico Serie', 'UC 10' ~ '10', 'Undercrown Shade' ~ 'Shade'."""
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return ka == kb
    kbr = key(brand)
    for k in (ka, kb):
        pass
    def strip(k):
        k = k[len(kbr):] if kbr and k.startswith(kbr) and len(k) > len(kbr) else k
        m = re.match(r"^[a-z]{1,3}(\d.*)$", k)
        return m.group(1) if m else k
    sa, sb = strip(ka), strip(kb)
    return sa == sb or sa.startswith(sb) or sb.startswith(sa)


def _still_listed(r: dict, size: str, site: dict[tuple[str, str], set[str]]) -> bool:
    """Does the site page for this catalog row's own line still list this size name?"""
    b = key(r["brand"])
    for (sb, sl), sizes in site.items():
        if sb == b and _line_eq(r["line"], sl) and key(size) in sizes:
            return True
    return False


def _match_sizes(rec: LineRecord, rows: list[dict], catalog: list[dict], claimed: set[str], site: dict) -> dict[int, dict | None]:
    """Pair each site size with at most one catalog row: exact names first, then names that were
    filed as a line, then dimensions, then a distinctive size name that moved lines. Names beat
    dimensions because seed dimensions are wrong far more often than seed names. Never the same
    row twice; brand-wide passes leave alone rows whose line the site still lists by name."""
    hits: dict[int, dict | None] = {}
    taken: set[str] = set(claimed)
    leaf = wrapper(rec.wrapper_raw)[0]
    own = (key(rec.brand), key(rec.line))

    def take(i, r):
        hits[i] = r; taken.add(r["id"])

    def elsewhere(r):  # the row's own line has a page on the site, and it isn't this one
        return any(sb == key(r["brand"]) and _line_eq(r["line"], sl) and (sb, sl) != own for sb, sl in site)

    def names(v):  # "Serie R No. 6" on a Serie R page is the catalog's "No. 6"
        k, kl = key(v.name), key(rec.line)
        return {k, k[len(kl):]} if kl and k.startswith(kl) and len(k) > len(kl) else {k}

    for i, v in enumerate(rec.vitolas):
        for r in rows:
            if r["id"] not in taken and (key(r["expression"]) in names(v) or (r["expression"] is None and len(rec.vitolas) == 1 and key(r["line"]) in (key(rec.line), key(rec.brand + " " + (rec.line or ""))))):
                take(i, r); break
    for i, v in enumerate(rec.vitolas):
        if i in hits: continue
        for r in catalog:
            if r["id"] in taken or key(r["brand"]) != key(rec.brand) or elsewhere(r): continue  # exact names beat a seed row's wrapper
            # "Blondie" filed as a line; "Blondie Belicoso" filed as line+size; "Ligero Maduro Matador" filed as a line.
            if (key(r["line"]) == key(v.name) and r["expression"] is None) \
               or key((r["line"] or "") + " " + (r["expression"] or "")) == key(v.name) \
               or ((r["expression"] is None or key(r["expression"]) in GENERIC_SIZES) and key(r["line"]) == key((rec.line or "") + " " + v.name)):
                take(i, r); break
    for i, v in enumerate(rec.vitolas):
        if i in hits: continue
        for r in rows:
            if r["id"] not in taken and r["length_in"] and r["ring_gauge"] and v.length_in and abs(float(r["length_in"]) - v.length_in) < 0.13 and abs(int(r["ring_gauge"]) - v.ring_gauge) <= 1:
                take(i, r); break
    for i, v in enumerate(rec.vitolas):
        if i in hits or key(v.name) in GENERIC_SIZES or key(v.name).isdigit(): continue  # "460" is every Nub line's size
        for r in catalog:
            if r["id"] not in taken and key(r["brand"]) == key(rec.brand) and key(r["expression"]) == key(v.name) \
                    and not _still_listed(r, v.name, site) and not elsewhere(r) and _wrapper_compatible(r, leaf):
                take(i, r); break
    return hits


def compare(records: list[LineRecord], catalog: list[dict]) -> Report:
    rep = Report()
    idx = _catalog_index(catalog)
    claimed: set[str] = set()
    site = {(key(r.brand), key(r.line)): {key(v.name) for v in r.vitolas} for r in records}

    for rec in records:
        rows = _find_line(idx, rec, set(site))
        leaf, origin, shade = wrapper(rec.wrapper_raw)
        body = strength(rec.body)
        if not rows:
            rep.new_lines.append(f"{rec.brand} — {rec.line or '(flagship)'}: {len(rec.vitolas)} sizes")
        hits = _match_sizes(rec, rows, catalog, claimed, site)
        # When the maker names only the wrapper's origin, new sizes take the leaf their matched
        # siblings in the same line already agree on (siblings that state the same origin the maker
        # does, so a wrong seed row can't spread), rather than contradicting them.
        sibling_leaves = {hits[i]["wrapper_leaf"] for i in hits if origin and hits[i]["wrapper_origin"] == origin} - {"unknown", "other", None}
        line_leaf = leaf if leaf not in ("unknown", "other") else (sibling_leaves.pop() if len(sibling_leaves) == 1 else leaf)
        for i, v in enumerate(rec.vitolas):
            shp, box = shape(v.name)
            shp = v.shape or shp
            hit = hits.get(i)
            entry = {"brand": rec.brand, "line": rec.line, "size": v.name, "dims": f"{v.length_in} x {v.ring_gauge}", "shape": shp, "box_pressed": box, "country": rec.country,
                     "wrapper": rec.wrapper_raw, "leaf": leaf, "origin": origin, "shade": shade, "body": body,
                     "binder": rec.binder, "filler": rec.filler, "band": rec.band_image_url, "size_image": v.image_url, "source_url": v.source_url or rec.source_url}
            if hit is None:
                if line_leaf != leaf:
                    entry["leaf"], entry["leaf_inherited"] = line_leaf, True
                rep.additions.append(entry)
                continue
            claimed.add(hit["id"])
            diffs = {}
            if v.length_in is not None and (hit["length_in"] is None or abs(float(hit["length_in"]) - v.length_in) >= 0.13):
                diffs["length_in"] = (hit["length_in"], v.length_in)
            if v.ring_gauge is not None and hit["ring_gauge"] != v.ring_gauge:
                diffs["ring_gauge"] = (hit["ring_gauge"], v.ring_gauge)
            if hit["shape"] != shp:
                diffs["shape"] = (hit["shape"], shp)
            if leaf not in ("unknown", "other") and hit["wrapper_leaf"] != leaf:
                diffs["wrapper_leaf"] = (hit["wrapper_leaf"], leaf)
            if origin and hit["wrapper_origin"] != origin:
                diffs["wrapper_origin"] = (hit["wrapper_origin"], origin)
            if shade and hit["wrapper_shade"] != shade:
                diffs["wrapper_shade"] = (hit["wrapper_shade"], shade)
            if body and hit["body"] != body:
                diffs["body"] = (hit["body"], body)
            if rec.country and not hit.get("country"):
                diffs["country"] = (None, rec.country)
            if key(hit["expression"]) != key(v.name):
                diffs["expression"] = (hit["expression"], v.name)
            hl, rl = key(hit["line"]), key(rec.line)
            if hl == key((rec.line or "") + " " + v.name):
                # "Ligero Maduro Matador" filed as a line: it's the Matador size of Ligero Maduro.
                diffs["line"] = (hit["line"], rec.line)
            elif rec.line and hl and hl != rl and rl.startswith(hl) and sum(1 for (b, l) in site if b == key(rec.brand) and l.startswith(hl)) > 1:
                # "Kristania" when the site has Kristania Criollo and Kristania Maduro: the maker's name disambiguates.
                diffs["line"] = (hit["line"], rec.line)
            elif rec.line and hl != rl:
                # The maker's line name wins; the catalog's old name is kept as an alias.
                diffs["line"] = (hit["line"], rec.line)
                if hit["line"]:
                    entry["alias"] = hit["line"]
                    rep.aliases.append(entry)
            if not hit["image_url"] and (v.image_url or rec.band_image_url):
                diffs["image"] = (None, "site has one")
            entry["id"] = hit["id"]; entry["catalog_line"] = hit["line"]; entry["diffs"] = diffs
            (rep.corrections if diffs else rep.matched).append(entry)

    site_lines = {(key(r.brand), key(r.line)) for r in records}
    for r in catalog:
        if r["id"] in claimed:
            continue
        if r["expression"] is None and not r["length_in"] and any(b == key(r["brand"]) and _line_eq(r["line"], l, r["brand"]) for b, l in site_lines):
            rep.placeholders.append(r)   # "Ligero Maduro" with no size: the line lives on; the row needs a human to pick a size
        else:
            rep.stale.append(r)
    return rep
