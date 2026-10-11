"""A bourbon diff Report → SQL. Never touches a verified row; every touched row gets source = 'maker'
and the maker's page as source_url. Nothing is deleted; stale rows are flagged discontinued."""
from __future__ import annotations

import json

from ..write import _source_image, q
from .diff import Report

import re

INSERT_COLS = ("type, status, source, specs, name, brand, brand_family, expression, producer, producer_id, proof, age_years, age_label, nas, "
               "expression_type, mash_style, mash_bill, spirit_type, bottled_in_bond, barrel_proof, finish, msrp_usd, is_core_range, "
               "catalog_included, aliases, image_url, source_url, source_checked_at, rarity")


def rarity_for(name: str, table: list[tuple[str, str]]) -> str | None:
    for pattern, value in table:
        if re.search(pattern, name, re.I):
            return value
    return None


def _row(f: dict, producer: str | None, maker_id: str | None, rarity: list[tuple[str, str]] = (), by_family: dict | None = None) -> dict:
    producer, maker_id = (by_family or {}).get(f["family"], (producer, maker_id))
    return {"n": f["name"], "rar": rarity_for(f["name"], list(rarity)), "f": f["family"], "x": f["expression"], "p": f["proof"], "ay": f["age_years"], "al": f["age_label"],
            "nas": (f["age_label"] or "").upper() == "NAS",  # only when the maker says so; silence is not NAS
            "et": f["expression_type"], "ms": f["mash_style"] or "unknown",
            "mb": f["mash_bill"], "st": f["spirit_type"], "bib": f["bottled_in_bond"], "bp": f["barrel_proof"], "fin": f["finish"],
            "msrp": f["msrp"], "core": f["core"], "al2": f["aliases"], "img": f["image"], "u": f["source_url"], "pr": producer, "mk": maker_id}


def insert_batches(additions: list[dict], *, producer: str | None, maker_id: str | None, rarity: list[tuple[str, str]] = (), by_family: dict | None = None, size: int = 40) -> list[str]:
    rows = [_row(f, producer, maker_id, rarity, by_family) for f in additions if f["proof"] is not None]  # no proof on the maker's page: reported, not added
    # image_url stays null and the maker's address goes to specs->>'source_image_url'; see
    # catalog/write.py._source_image for why.
    head = (f"insert into cellar.products ({INSERT_COLS})\n"
            "select 'bourbon', 'confirmed', 'maker', "
            "case when r.img is null then '{}'::jsonb else jsonb_build_object('source_image_url', r.img) end, "
            "r.n, r.f, r.f, r.x, r.pr, r.mk::uuid, r.p, r.ay, r.al, r.nas, "
            "r.et::cellar.expression_type, r.ms::cellar.mash_style, r.mb, r.st::cellar.spirit_type, r.bib, r.bp, r.fin, r.msrp, r.core, "
            "true, coalesce(r.al2, '{}'::text[]), null, r.u, now(), r.rar::cellar.rarity\n"
            "from jsonb_to_recordset($j$")
    tail = ("$j$::jsonb) as r(n text, f text, x text, p numeric, ay numeric, al text, nas bool, et text, ms text, mb text, st text, "
            "bib bool, bp bool, fin text, msrp numeric, core bool, al2 text[], img text, u text, pr text, mk text, rar text)\n"
            "where not exists (select 1 from cellar.products e where e.type = 'bourbon' and e.merged_into is null "
            "and coalesce(e.brand_family, '') = coalesce(r.f, '') and coalesce(e.expression, '') = coalesce(r.x, '') and coalesce(e.release_label, '') = '');")
    return [head + json.dumps(rows[i:i + size], ensure_ascii=False, separators=(",", ":")) + tail for i in range(0, len(rows), size)]


def _promote(f: dict) -> list[str]:
    """A bottling the module calls core and the maker lists becomes core and browsable, even when its seed
    row was filed as a one-off. Never demotes: a row already core stays core."""
    return ["is_core_range = true", "catalog_included = true"] if f.get("core") else ["catalog_included = catalog_included or is_core_range"]


def _rarity(f: dict, table) -> list[str]:
    """Fill a missing rarity on a matched row from the module's own table; never overwrites one that is set."""
    r = rarity_for(f["name"], list(table)) if table else None
    return [f"rarity = coalesce(rarity, {q(r)}::cellar.rarity)"] if r else []


def statements(rep: Report, *, producer: str | None, maker_id: str | None, image_prefix: str, by_family: dict | None = None, rarity=()) -> list[str]:
    out: list[str] = []
    default = (producer, maker_id)
    for f in rep.corrections:
        d = f["diffs"]
        producer, maker_id = (by_family or {}).get(f["family"], default)
        sets = [
            f"proof = {q(f['proof'])}" if "proof" in d else None,
            f"age_years = {q(f['age_years'])}, age_label = {q(f['age_label'])}, nas = false" if "age_years" in d else None,
            f"age_label = {q(f['age_label'])}, nas = false" if "age_label" in d else None,
            f"spirit_type = {q(f['spirit_type'])}" if "spirit_type" in d else None,
            f"mash_style = {q(f['mash_style'])}" if "mash_style" in d else None,
            f"mash_bill = {q(f['mash_bill'])}" if "mash_bill" in d else None,
            "bottled_in_bond = true" if "bottled_in_bond" in d else None,
            "barrel_proof = true" if "barrel_proof" in d else None,
            f"finish = {q(f['finish'])}" if "finish" in d else None,
            f"msrp_usd = {q(f['msrp'])}" if "msrp_usd" in d else None,
            _source_image(q, f["image"]) if "image" in d else None,
            f"name = {q(f['name'])}, expression = {q(f['expression'])}, "
            f"aliases = (select array_agg(distinct a) from unnest(array_append(aliases, {q(f['catalog_name'])})) a)" if "name" in d else None,
            f"producer = coalesce(producer, {q(producer)})" if producer else None,
            f"producer_id = coalesce(producer_id, {q(maker_id)}::uuid)" if maker_id else None,
            "source = 'maker', status = 'confirmed'" if f["proof"] is not None else None,  # a page that states no proof confirms nothing
            f"source_url = {q(f['source_url'])}", "source_checked_at = now()", "discontinued = false",
            *_promote(f),
            *_rarity(f, rarity),
        ]
        out.append(f"update cellar.products set {', '.join(s for s in sets if s)} where id = {q(f['id'])} and facts_verified_at is null;")

    checked = [f["id"] for f in rep.matched + rep.corrections]
    if checked:
        out.append(f"update cellar.products set source_checked_at = now() where id in ({', '.join(q(i) for i in checked)});")
    for f in rep.matched:  # the maker agrees with every fact: confirmed by the maker, whatever seeded it
        producer, maker_id = (by_family or {}).get(f["family"], default)
        sets = [f"source_url = {q(f['source_url'])}", "discontinued = false", *_promote(f), *_rarity(f, rarity)]  # the maker lists it
        if f["proof"] is not None:
            sets.insert(0, "source = 'maker', status = 'confirmed'")  # confirmed only when the page states the proof
        if producer:
            sets.append(f"producer = coalesce(producer, {q(producer)})")
        if maker_id:
            sets.append(f"producer_id = coalesce(producer_id, {q(maker_id)}::uuid)")
        if f["image"]:
            sets.append(_source_image(q, f["image"]))
        out.append(f"update cellar.products set {', '.join(sets)} where id = {q(f['id'])} and facts_verified_at is null;")
    if rep.stale:
        out.append(f"update cellar.products set discontinued = true where id in ({', '.join(q(r['id']) for r in rep.stale)}) and facts_verified_at is null;")
    # No hero-image backfill; see the note in catalog/write.py.
    return out
