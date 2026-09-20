"""Rows a human has already re-filed against a source. A source module may define
OVERRIDES = {catalog row id: {"line": ..., "expression": ...}}; the export is rewritten so the
diff matches those rows by name, and the SQL that records the decision is emitted with part1."""
from __future__ import annotations

from .write import _name, q


def apply(catalog: list[dict], overrides: dict[str, dict], series_brands: set[str] = frozenset()) -> list[str]:
    sql: list[str] = []
    for r in catalog:
        o = overrides.get(r["id"])
        if not o:
            continue
        sets = []
        if "line" in o and o["line"] != r["line"]:  # an explicit None re-files the row as the flagship
            sets.append(f"line = {q(o['line'])}")
            if r["line"]:
                sets.append(f"aliases = (select array_agg(distinct a) from unnest(array_append(aliases, {q(r['line'])})) a)")
            r["line"] = o["line"]
        if o.get("expression") and o["expression"] != r["expression"]:
            sets.append(f"expression = {q(o['expression'])}")
            r["expression"] = o["expression"]
        if sets:
            sets.append(f"name = {q(_name(r['brand'], r['line'], r['expression'], series_brands))}")
            sql.append(f"update cellar.products set {', '.join(sets)} where id = {q(r['id'])};")
    return sql
