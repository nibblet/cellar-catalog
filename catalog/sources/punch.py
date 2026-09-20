"""Punch on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["punch"]
COUNTRY = "Honduras"  # General rolls Punch in Danlí, Honduras
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


parse = base.parse
