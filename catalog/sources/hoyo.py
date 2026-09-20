"""Hoyo de Monterrey + Excalibur on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["hoyo-de-monterrey", "excalibur"]
COUNTRY = "Honduras"  # General rolls Hoyo and Excalibur in Danlí; the site's own copy says "Honduran"
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


parse = base.parse

# Catalog rows re-filed by hand: the maker files these sizes under a line.
OVERRIDES = {
    "45d2ce95-319a-4108-8211-3d3d204f5639": {"line": "Maduro", "expression": "Rothschild"},   # "Rothschild Maduro" is the Maduro line's Rothschild
    "ea5facba-1f64-4bb9-8ec0-cd672db623a7": {"line": "Sumatra", "expression": "Sabrosos"},    # plain "Sabroso" is the natural (Sumatra) Sabrosos
}
