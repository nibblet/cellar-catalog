"""CAO on cigarworld.com (General Cigar)."""
from . import cigarworld as base

BRANDS = ["cao", "cao-flavours"]
COUNTRY = None  # CAO lines are rolled in several countries; not stated per line
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    return base.parse(url, page, globals().get("COUNTRY_BY_LINE"))

# Catalog rows re-filed by hand: seed rows that fused the series and the line.
OVERRIDES = {
    "77a00bf1-0fd3-4f57-afe4-35846807dc13": {"line": "Speed Shop", "expression": "Crankshaft"},
    "d2473ead-0b63-47b3-be44-d2480bad5793": {"line": "Steel Horse", "expression": "Roadkill"},
}

# Where each CAO line is rolled. cigarworld.com states it for only a handful of lines (Bones,
# Brazilia Select, Flathead V23); this map fills the rest and is CURATED, not maker text: General
# Cigar's own attributions in its press releases and Cigar World news posts — STG Estelí (Nicaragua)
# for the modern CAO portfolio, STG Danlí (Honduras) for the Honduran-heritage lines, General
# Cigar Dominicana for Flavours. A line missing here stays null rather than guessed.
_ESTELI, _DANLI, _DR = "Nicaragua", "Honduras", "Dominican Republic"
COUNTRY_BY_LINE = {
    **{l: _DR for l in ("Flavours Bella Vanilla", "Flavours Caramelo Joe", "Flavours Cherrybomb", "Flavours Earth Nectar",
                        "Flavours Eileen's Dream", "Flavours Gold Honey", "Flavours Moontrance", "Flavours Solfyre")},
    **{l: _DANLI for l in ("Italia", "Colombia", "OSA SOL", "FASA Sol", "Brazilia Select")},
    **{l: _ESTELI for l in (
        "Flathead", "Flathead V23", "V19", "V21", "Speed Shop", "Steel Horse", "Bones", "Pilón", "Pilón Añejo",
        "Amazon Basin", "Amazon Basin Extra Añejo", "Anaconda", "Orellana", "Fuma Em Corda", "BX3", "Consigliere",
        "Session", "Mortal Coil", "Arcana Stokk", "Arcana Thunder Smoke", "Nicaragua", "Esteli", "Zocalo",
        "Cyclone", "Earthquake", "Heatwave", "Odyssey", "Escaparate TAM.095", "Criollo", "Brazilia",
        "Brazilia Carnivale", "Cameroon", "Cx2", "LX2", "MX2", "Gold", "Gold Maduro", "Gold Vintage", "Black",
        "America", "America 250th Anniversary", "Honor", "Hurricane", "Concert", "Extreme", "Vision",
        "Vision 2020", "Vision 2022", "La Traviata", "La Traviata Maduro", "Soprano", "60", "65th Anniversary",
        "Maduro", "Left Coast", "Right Coast", "FASA Noche", "FASA Sombra", "Nasty Nutcracker", "Rabid Reindeer",
        "Sinister Sam", "Stingy Scrooge", "Wicked Winter", "Evil Snowman", "Angry Santa")},
}
