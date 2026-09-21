"""What a bourbon importer produces: one record per bottling (the SKU a member orders by name), with
provenance. Batches, years and picks are not records; they live on the bottle."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BottlingRecord:
    brand_family: str            # as the catalog files it; the source module maps the site's brand name
    expression: str | None       # null = the family's flagship ("Buffalo Trace", "Booker's")
    name: str                    # bar-order name: family + expression
    source_url: str
    proof: float | None
    age_years: float | None = None
    age_label: str | None = None  # as printed ("10 yr"); "NAS" only when the maker says there is none
    class_raw: str | None = None  # "Kentucky Straight Bourbon Whiskey" as the label reads
    mash_raw: str | None = None   # "Mash Bill #1", "75% corn, 13% rye, 12% malted barley"
    mash_style: str | None = None # when the maker's named mash bill is known to the source module
    style_raw: str | None = None
    description: str | None = None
    tasting_notes: str | None = None
    image_url: str | None = None
    finish: str | None = None
    msrp_usd: float | None = None
    aliases: list[str] = field(default_factory=list)
    is_core_range: bool = True    # the source module says when a bottling is a release, not a lineup
