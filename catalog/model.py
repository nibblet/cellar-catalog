"""What an importer produces: one record per (brand, line, size), with provenance."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Vitola:
    name: str                 # marketed size name as printed ("Corona Viva", "No. 4")
    length_in: float | None
    ring_gauge: int | None
    image_url: str | None = None


@dataclass
class LineRecord:
    brand: str
    line: str | None          # null = the brand's flagship
    source_url: str
    wrapper_raw: str | None = None
    binder: str | None = None
    filler: str | None = None
    body: str | None = None   # as the maker labels it: Mild … Full
    band_image_url: str | None = None
    vitolas: list[Vitola] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
