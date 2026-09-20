"""CAO on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["cao", "cao-flavours"]
COUNTRY = None  # CAO lines are rolled in several countries; not stated per line
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


parse = base.parse
