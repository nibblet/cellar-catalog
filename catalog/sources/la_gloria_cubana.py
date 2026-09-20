"""La Gloria Cubana on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["la-gloria-cubana"]
COUNTRY = None  # Serie R and newer lines are Estelí, the classics Santiago; the copy usually says
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    return base.parse(url, page, globals().get("COUNTRY_BY_LINE"))

# Catalog rows re-filed by hand.
OVERRIDES = {
    "70ee9370-67d9-4ef5-9708-5f7bb04b05a4": {"line": "Esteli", "expression": "Robusto"},                  # "Toro" 4.5x52 has the Robusto's exact dims
    "1e580739-bbc7-4a03-840c-6920bd467a65": {"line": "Serie R Black Maduro", "expression": "No. 58"},     # 6.88x58 Broadleaf is the Black Maduro No. 58
    "adcbc215-2130-4d03-89e2-4dad9312f95c": {"line": "Serie S", "expression": "Robusto Gordo"},          # natural Serie S 5.5x54
}

# CURATED, not maker text: El Credito / General Cigar Dominicana for the classic Santiago lines
# (the Serie S pages name the El Credito binder blend; the Corojo de Oro and Spirit of the Lady pages
# name the factory outright and need no entry), STG Estelí for the Estelí-named lines (the copy
# confirms two of those), and Society Cigar, which the page calls a Honduran puro. The one-off
# trunk-show Ligas, TAA and 8th Street releases stay null.
_DR, _NI, _HN = "Dominican Republic", "Nicaragua", "Honduras"
COUNTRY_BY_LINE = {
    **{l: _DR for l in ("Classic", "Classic Maduro", "Serie R", "Serie R Maduro", "Serie R Black", "Serie R Black Maduro",
                        "Reserva Figurados", "Colección Reserva", "Artesanos de Tabaqueros", "Artesanos Retro Especiale",
                        "Artesanos de Obelisco", "Medio Tiempo", "Serie N", "Serie S", "Serie S Maduro")},
    **{l: _NI for l in ("Esteli", "Serie R Esteli", "Serie R Esteli Maduro", "Gilded Age")},
    "Society Cigar": _HN,
}
