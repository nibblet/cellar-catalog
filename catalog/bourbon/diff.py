"""Compare what a distillery's site says against what the catalog has. Read-only; produces a report.

Matching is by brand family, then expression. A site bottling claims at most one catalog row:
  1. the same expression key ("10 Year" ~ "Aged 10 Years" ~ "10 Yr"), or the family flagship on both sides;
  2. the bottling's name (or one of the site's title variants) equals a row's name or one of its aliases;
  3. one expression key contains the other and the proofs agree ("Single Barrel" ~ "10 Year Single Barrel").
A row with a release_label is a variant filed on purpose and is never claimed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..normalize import key
from .model import BottlingRecord
from .normalize import expression_key, expression_tokens, expression_type, finish, flags, mash_bill, mash_style, spirit_type


@dataclass
class Report:
    matched: list[dict] = field(default_factory=list)      # same bottling; facts agree
    corrections: list[dict] = field(default_factory=list)  # same bottling; facts differ
    additions: list[dict] = field(default_factory=list)    # site has it, catalog doesn't
    stale: list[dict] = field(default_factory=list)        # catalog has it (in a family the site covers), site doesn't
    renames: list[dict] = field(default_factory=list)      # maker's name differs from the catalog's; old name kept as alias
    new_families: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)       # site pages that are not whiskey


def _facts(rec: BottlingRecord) -> dict:
    st = spirit_type(rec.class_raw, rec.name)
    bib, bp = flags(rec.name, rec.class_raw, rec.proof)
    return {
        "family": rec.brand_family, "expression": rec.expression, "name": rec.name, "proof": rec.proof,
        "age_years": rec.age_years, "age_label": rec.age_label, "spirit_type": st,
        "mash_style": rec.mash_style or mash_style(rec.mash_raw, st, rec.name), "mash_bill": mash_bill(rec.mash_raw),
        "expression_type": expression_type(rec.name), "bottled_in_bond": bib, "barrel_proof": bp,
        "finish": rec.finish or finish(rec.name, rec.description), "msrp": rec.msrp_usd, "image": rec.image_url,
        "source_url": rec.source_url, "aliases": [a for a in rec.aliases if a and a != rec.name], "core": rec.is_core_range,
        "class": rec.class_raw, "mash_raw": rec.mash_raw,
    }


def _candidates(rec: BottlingRecord, rows: list[dict], taken: set[str]) -> list[dict]:
    fam = key(rec.brand_family)
    return [r for r in rows if key(r["brand_family"]) == fam and r["id"] not in taken and not r.get("release_label")]


def _pass(rec: BottlingRecord, rows: list[dict], taken: set[str], n: int, site_count: int) -> dict | None:
    """One matching pass. Pass 1 is exact, later passes looser; every bottling gets a pass before
    any bottling gets the next, so a loose match never steals a row an exact one is about to claim."""
    mine = _candidates(rec, rows, taken)
    ek = expression_key(rec.expression)
    if n == 1:  # same expression, or the flagship on both sides
        for r in mine:
            if (rec.expression is None and r["expression"] is None) or (ek and expression_key(r["expression"]) == ek):
                return r
    elif n == 2:  # the bottling's name (or a title variant) is the row's name or one of its aliases
        names = {key(rec.name)} | {key(a) for a in rec.aliases}
        for r in mine:
            if key(r["name"]) in names or names & {key(a) for a in (r.get("aliases") or [])}:
                return r
        if rec.expression is None:  # a flagship page vs a row named "<Family> Bourbon"
            for r in mine:
                if expression_key(r["name"]) == expression_key(rec.brand_family) or expression_key(r["expression"]) in ("", expression_key(rec.brand_family)):
                    return r
    elif n == 3:  # one expression's words inside the other's, and the proof agrees ("9 Year" ~ "Small Batch 9 Year")
        et = expression_tokens(rec.expression)
        for r in mine:
            rt = expression_tokens(r["expression"]) or expression_tokens(r["name"].replace(r["brand_family"], ""))
            if et and rt and (et <= rt or rt <= et) and (rec.proof is None or r["proof"] is None or abs(float(r["proof"]) - rec.proof) < 0.6):
                return r
    elif n == 4:  # the site lists one bottling for the family and the catalog holds one row: the same bottle
        if site_count == 1 and len(mine) == 1:
            return mine[0]
    return None


def _dedupe(records: list[BottlingRecord]) -> list[BottlingRecord]:
    """Several pages may describe one bottling (each Booker's batch has a page). The last one on the
    site wins the facts (batches are listed oldest first); the others' titles become aliases."""
    by_key: dict[tuple[str, str], BottlingRecord] = {}
    for rec in records:
        k = (key(rec.brand_family), expression_key(rec.expression))
        if k in by_key:
            prev = by_key[k]
            rec.aliases = sorted(set(rec.aliases) | set(prev.aliases) | ({prev.name} if prev.name != rec.name else set()))
        by_key[k] = rec
    return list(by_key.values())


def compare(records: list[BottlingRecord], catalog: list[dict]) -> Report:
    rep = Report()
    records = _dedupe(records)
    taken: set[str] = set()
    families = {key(r["brand_family"]) for r in catalog}
    site_families = set()
    per_family: dict[str, int] = {}
    for rec in records:
        per_family[key(rec.brand_family)] = per_family.get(key(rec.brand_family), 0) + 1
    facts = {}
    names = {key(r.name) for r in records}
    shared: dict[str, int] = {}
    for r in records:
        for a in {key(a) for a in r.aliases}:
            shared[a] = shared.get(a, 0) + 1
    for rec in records:
        f = _facts(rec)
        # Another bottling's name is never an alias, nor is a title two pages share (Weller Special Reserve / Colorado).
        f["aliases"] = [a for a in f["aliases"] if key(a) not in names and shared.get(key(a), 0) < 2]
        if f["spirit_type"] is None:
            rep.skipped.append(f"{rec.name} — {rec.class_raw}")
            continue
        facts[id(rec)] = f
        site_families.add(key(rec.brand_family))
        if key(rec.brand_family) not in families and rec.brand_family not in rep.new_families:
            rep.new_families.append(rec.brand_family)
    hits: dict[int, dict] = {}
    for n in (1, 2, 3, 4):
        for rec in records:
            if id(rec) in facts and id(rec) not in hits:
                hit = _pass(rec, catalog, taken, n, per_family[key(rec.brand_family)])
                if hit is not None:
                    hits[id(rec)] = hit
                    taken.add(hit["id"])
    for rec in records:
        if id(rec) not in facts:
            continue
        f, hit = facts[id(rec)], hits.get(id(rec))
        if hit is None:
            rep.additions.append(f)
            continue
        d = {}
        if rec.proof is not None and (hit["proof"] is None or abs(float(hit["proof"]) - rec.proof) >= 0.05):
            d["proof"] = (hit["proof"], rec.proof)
        if rec.age_years is not None and (hit["age_years"] is None or abs(float(hit["age_years"]) - rec.age_years) >= 0.05):
            d["age_years"] = (hit["age_years"], rec.age_years)
        elif rec.age_years is None and rec.age_label and rec.age_label != "NAS" and hit["age_years"] is None and (hit.get("age_label") or "").upper() in ("", "NAS"):
            d["age_label"] = (hit.get("age_label"), rec.age_label)  # "8–12 yr": the maker's range, no number to filter on
        if f["spirit_type"] and hit["spirit_type"] != f["spirit_type"]:
            d["spirit_type"] = (hit["spirit_type"], f["spirit_type"])
        if f["mash_style"] and hit["mash_style"] != f["mash_style"]:
            d["mash_style"] = (hit["mash_style"], f["mash_style"])
        if f["mash_bill"] and not hit.get("mash_bill"):
            d["mash_bill"] = (None, f["mash_bill"])
        if f["bottled_in_bond"] and not hit["bottled_in_bond"]:
            d["bottled_in_bond"] = (False, True)
        if f["barrel_proof"] and not hit["barrel_proof"]:
            d["barrel_proof"] = (False, True)
        if f["finish"] and not hit.get("finish"):
            d["finish"] = (None, f["finish"])
        if f["msrp"] and not hit.get("msrp_usd"):
            d["msrp_usd"] = (None, f["msrp"])
        if f["image"] and not hit.get("image_url"):
            d["image"] = (None, "site has one")
        if key(hit["name"]) != key(rec.name):
            d["name"] = (hit["name"], rec.name)
            rep.renames.append({"id": hit["id"], "old": hit["name"], "new": rec.name})
        f["id"], f["catalog_name"], f["diffs"], f["verified"] = hit["id"], hit["name"], d, bool(hit.get("facts_verified_at"))
        (rep.corrections if d else rep.matched).append(f)

    for r in catalog:
        if r["id"] in taken or r.get("release_label") or key(r["brand_family"]) not in site_families:
            continue
        rep.stale.append(r)
    return rep
