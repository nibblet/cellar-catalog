"""Punch on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["punch"]
COUNTRY = "Honduras"  # General rolls Punch in Danlí, Honduras
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    return base.parse(url, page, globals().get("COUNTRY_BY_LINE"))

# Catalog rows re-filed by hand: seed rows that named a size as if it were a line.
OVERRIDES = {
    "5f103b1e-299f-4254-8773-0161ecd56ab9": {"line": "Clásico", "expression": "Champions"},           # "Champion" 4.5x60 Sumatra is the Clásico Champions, not Dad Bod
    "39a7c19b-ff72-4d7b-b4ec-9e3ea25e5124": {"line": "Clásico", "expression": "London Club"},
    "e0b6a0f3-7298-4bf4-9b2c-d77e4e6c00bd": {"line": "Clásico", "expression": "Rothschild"},
    "961f28b5-0d11-49f5-91f1-65fb52fcedc1": {"line": "Clásico Maduro", "expression": "After Dinner"},
    "0298abab-99a8-4b6f-b81c-bd9c28394d16": {"line": "Egg Roll", "expression": "Egg Roll"},          # 4.5x50 is the Egg Roll; the XL is 6x60
}
