"""Macanudo on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["macanudo"]
COUNTRY = None  # the classic lines are General Cigar Dominicana; Inspirado is split across three countries and the copy rarely says
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    return base.parse(url, page, globals().get("COUNTRY_BY_LINE"))

# Catalog rows re-filed by hand.
OVERRIDES = {
    "1a26c361-f196-4d2e-ae74-b4b3e5c7dd8b": {"line": "Café", "expression": "Prince Phillip"},   # the site's spelling
    "d732d911-77a8-4821-8b37-f297ab0f3d1d": {"line": "Estate Reserve", "expression": "No. III"},  # "Robusto" 7x52 is nonsense; No. III is the 5x50 robusto
}

# CURATED, not maker text: the Santiago-made classics (General Cigar Dominicana) per General's own
# releases; the Inspirado colours are STG Danlí, Honduras (the Inspirado Orange page says so, and the
# Minis are the same blends), except White and Jamao, which are Dominican. M, Emissary, Mao and the
# Estelí extensions are left to the page copy (Ecuadorian Shade and Sumatra say Estelí).
_DR, _HN = "Dominican Republic", "Honduras"
COUNTRY_BY_LINE = {
    **{l: _DR for l in (
        "Café", "Maduro", "Gold Label", "Robust", "1968", "Cru Royale", "Estate Reserve",
        "Estate Reserve Flint Knoll Release No. 1", "Estate Reserve Flint Knoll Release No. 2", "Estate Reserve Flint Knoll Release No. 3",
        "Vintage 2000", "Vintage 2006", "Vintage 2010", "Vintage Maduro 1997", "Vintage Maduro 2013",
        "Inspirado White", "Inspirado White Minis", "Inspirado Jamao",
    )},
    **{l: _HN for l in (
        "Inspirado Orange", "Inspirado Orange Minis", "Inspirado Black", "Inspirado Green", "Inspirado Red", "Inspirado Red Minis",
        "Inspirado Palladium", "Inspirado Brazilian Shade", "Inspirado Tercio-Aged",
    )},
}
