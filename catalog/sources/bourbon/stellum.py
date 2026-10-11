"""stellum.com (Stellum Spirits — Barrell Craft Spirits' sister brand). Wix; one page per bottling, no cart.
The pages state no proof or age in text; the proof is printed on the bottle label in the page's own solo
bottle photo ("57.49% ALC/VOL (114.98 PROOF)"). The label is the maker's legal statement and sits on the
maker's own page, so it counts, but we do not OCR: each proof below was READ BY HAND from the full-size
photo (the Wix media id is the evidence) and the module only uses it while that same media id is still in
the cached page — if the maker swaps the photo, the proof silently drops instead of going stale. The six
readings land within 0.06 of the seeded Breaking Bourbon proofs, which corroborates them. Cask-strength
blends vary by batch, so each proof is "as pictured" (rounded to the column's one decimal).
Skipped: /singlebarrel (a per-barrel program; the pictured barrel 'Serpens A0' says 120 proof, 60% ABV and
is not the program's proof), /shop and the cocktail pages. Romulan and the other seeds are not on the site."""
from __future__ import annotations

import html

from ...bourbon.model import BottlingRecord

PRODUCER = "Stellum Spirits"
DELAY = 6
SITEMAP = "https://www.stellum.com/sitemap.xml"
IMAGE_PREFIX = "https://static.wixstatic.com/"
CATALOG_FAMILIES = ["Stellum"]
PRODUCER_BY_FAMILY = {}

# A cask-strength blend of straight bourbons is a straight bourbon (High West lesson): class_raw carries the label class
# so spirit_type() does not read the word "blend".
BOURBON = "Straight Bourbon Whiskey"
RYE = "Straight Rye Whiskey"
# slug → (expression, aliases, class, label media id, proof read from that label)
PAGES = {
    "bourbon": ("Bourbon", [], BOURBON, "12d4f8_2653f84dfaaf4d33ae09f930814a4374", 114.98),
    "rye": ("Rye", [], RYE, "12d4f8_cb2a02476e734c4098e41f998ef80a96", 116.24),
    "stellumblackbourbon": ("Black Bourbon", [], BOURBON, "12d4f8_c0b11a3c96ae42d6827fbba97e3ab26c", 109.22),
    "stellumblackrye": ("Black Rye", [], RYE, "12d4f8_ddccaf0784f1463896b99d57ef216c8c", 114.26),
    "equinox": ("Equinox Blend", ["Stellum Equinox Blend #1"], BOURBON, "12d4f8_ad66b7adfafe4770a9063e2ff1d75da4", 117.26),
    "fibonacci": ("Fibonacci Blend", ["Stellum Black Rye Fibonacci Blend", "Stellum Fibonacci Blend #1"], RYE, "12d4f8_35477f77261f4866897a6c3f32ed3014", 115.12),
    "huntersmoon": ("Hunter's Moon", [], BOURBON, "12d4f8_051bb084f196454f84284b863a5515a7", 115.52),
}
CORE = {"Bourbon", "Rye"}
RARITY = [(r"equinox|fibonacci|hunter", "limited"), (r"black", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://www.stellum.com/{slug}" for slug in PAGES]


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, media, proof = PAGES[slug]
    name = f"Stellum {expression}"
    stated = media in page  # the label photo this proof was read from must still be on the page
    return BottlingRecord(
        brand_family="Stellum", expression=expression, name=name, source_url=url,
        proof=round(proof, 1) if stated else None, class_raw=class_raw,
        image_url=f"https://static.wixstatic.com/media/{media}~mv2." + ("png" if slug in ("equinox", "fibonacci", "huntersmoon") else "jpg") if stated else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
