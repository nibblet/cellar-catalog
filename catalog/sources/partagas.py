"""Partagas on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["partagas"]
COUNTRY = "Dominican Republic"  # General Cigar Dominicana, Santiago; a few lines are rolled elsewhere and say so in the copy
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    return base.parse(url, page, globals().get("COUNTRY_BY_LINE"))

# Catalog rows re-filed by hand.
OVERRIDES = {
    "353c3c5c-06eb-4b50-91e0-a4bf5d5aaf49": {"expression": "Robusto"},                          # 1845 Extra Fuerte 5.5x52 is the 5.5x50 Robusto
    "e8716b1a-f0ce-4550-9e3a-cbf703669c4b": {"line": "Legend", "expression": "Toro Leyenda"},   # "Legendario" 6x54 is Legend's Toro Leyenda
}
