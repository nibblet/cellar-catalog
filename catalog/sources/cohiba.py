"""Cohiba on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["cohiba"]
COUNTRY = "Dominican Republic"  # General rolls Cohiba in Santiago, DR
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


parse = base.parse
