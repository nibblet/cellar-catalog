"""Turn a diff Report into SQL. Never touches a verified row; every touched row gets source_url."""
from __future__ import annotations

from .diff import Report
from .normalize import shape


def q(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _name(brand: str, line: str | None, size: str, series_brands: set[str]) -> str:
    # Catalog convention: name = line + size, without the brand. For series-style brands
    # (ACID Blue / Blondie) the size *is* the product name.
    if brand in series_brands or not line:
        return size
    if size.lower().startswith(line.lower()) or line.lower().startswith(size.lower()):
        return size  # "Papas Fritas Collection" / "Papas Fritas"
    return f"{line} {size}"


def statements(rep: Report, *, maker_id: str | None, country_by_brand: dict[str, str], series_brands: set[str],
               image_prefix: str, keep_line_for: set[str] = frozenset()) -> list[str]:
    out: list[str] = []
    # Where the catalog already names a line differently, new sizes join it under the catalog's name.
    line_of = {(e["brand"], e["line"]): e["catalog_line"] for e in rep.aliases}

    for e in rep.corrections:
        shp, box = shape(e["size"])
        sets = [
            f"length_in = {q(float(e['dims'].split(' x ')[0]))}" if e["dims"].split(" x ")[0] != "None" else None,
            f"ring_gauge = {q(int(e['dims'].split(' x ')[1]))}" if e["dims"].split(" x ")[1] != "None" else None,
            f"shape = {q(shp)}", f"box_pressed = {q(box)}",
            f"wrapper_leaf = {q(e['leaf'])}" if e["leaf"] not in ("unknown", "other") else None,
            f"wrapper_origin = coalesce({q(e['origin'])}, wrapper_origin)",
            f"wrapper_shade = coalesce({q(e['shade'])}, wrapper_shade)",
            f"body = coalesce({q(e['body'])}, body)", f"strength = coalesce(strength, {q(e['body'])})",
            f"binder = coalesce({q(e['binder'])}, binder)", f"filler = coalesce({q(e['filler'])}, filler)",
            f"expression = {q(e['size'])}",
            f"image_url = coalesce(image_url, {q(e['size_image'] or e['band'])})",
            f"source = 'maker'", f"source_url = {q(e['source_url'])}",
        ]
        line_change = e["diffs"].get("line")
        if line_change and e["brand"] not in keep_line_for:
            sets.append(f"line = {q(line_change[1])}")
            sets.append(f"name = {q(_name(e['brand'], line_change[1], e['size'], series_brands))}")
        elif "expression" in e["diffs"]:
            sets.append(f"name = {q(_name(e['brand'], e['catalog_line'], e['size'], series_brands))}")
        out.append(f"update cellar.products set {', '.join(s for s in sets if s)} where id = {q(e['id'])} and facts_verified_at is null;")

    for e in rep.additions:
        shp, box = shape(e["size"])
        length, ring = e["dims"].split(" x ")
        country = country_by_brand.get(e["brand"])
        e = {**e, "line": line_of.get((e["brand"], e["line"]), e["line"])}
        out.append(
            "insert into cellar.products (type, name, brand, line, expression, length_in, ring_gauge, shape, box_pressed, "
            "wrapper_leaf, wrapper_origin, wrapper_shade, body, strength, binder, filler, country, producer_id, image_url, "
            "source, source_url, status, catalog_included, specs) values ("
            + ", ".join([
                "'cigar'", q(_name(e["brand"], e["line"], e["size"], series_brands)), q(e["brand"]), q(e["line"]), q(e["size"]),
                q(float(length)) if length != "None" else "null", q(int(ring)) if ring != "None" else "null", q(shp), q(box),
                q(e["leaf"] if e["leaf"] != "other" else "unknown"), q(e["origin"]), q(e["shade"]), q(e["body"]), q(e["body"]),
                q(e["binder"]), q(e["filler"]), q(country), q(maker_id),
                q(e["size_image"] or e["band"]), "'maker'", q(e["source_url"]), "'confirmed'", "true", "'{}'::jsonb",
            ]) + ");"
        )

    for e in rep.aliases:
        out.append(f"update cellar.products set aliases = (select array_agg(distinct a) from unnest(array_append(aliases, {q(e['alias'])})) a) where id = {q(e['id'])};")

    if rep.stale:
        ids = ", ".join(q(r["id"]) for r in rep.stale)
        out.append(f"update cellar.products set discontinued = true where id in ({ids});")

    # Hero images for anything that now has a site image and no product_images row.
    out.append(
        "insert into cellar.product_images (product_id, image_url, is_hero) "
        "select p.id, p.image_url, true from cellar.products p "
        f"where p.type = 'cigar' and p.source = 'maker' and p.image_url like {q(image_prefix + '%')} "
        "and not exists (select 1 from cellar.product_images i where i.product_id = p.id);"
    )
    return out
