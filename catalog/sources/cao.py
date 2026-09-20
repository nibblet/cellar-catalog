"""CAO on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["cao", "cao-flavours"]
COUNTRY = None  # CAO lines are rolled in several countries; not stated per line
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


parse = base.parse

# Catalog rows re-filed by hand: seed rows that fused the series and the line.
OVERRIDES = {
    "77a00bf1-0fd3-4f57-afe4-35846807dc13": {"line": "Speed Shop", "expression": "Crankshaft"},
    "d2473ead-0b63-47b3-be44-d2480bad5793": {"line": "Steel Horse", "expression": "Roadkill"},
}
