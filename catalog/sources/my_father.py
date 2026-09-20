"""myfathercigars.com — WordPress/Elementor, one page per line. Sizes are <h3>Name L x R</h3>
headings, each under its cigar image; a blend line reads "Wrapper – … | Binder – … | Filler – … |
Handcrafted in Nicaragua". Body is in the prose ("Full-Bodied blend").

My Father Cigars makes several brands and the site lists them together; BRANDS files each page
under the brand a smoker would look for (Don Pepin Garcia, Flor de las Antillas, La Dueña …)."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola
from ..normalize import clean_value, dimensions, shape, size_name

VITOLA_WORDS = r"robusto|toro gordo|toro grande|toro|belicoso|churchill|torpedo|corona gorda|gran corona|petit lancero|petit belicoso|petit robusto|lancero|corona|crema|toros|belicosos|selectos|salomones"

DELAY = 5
SITEMAP = "https://myfathercigars.com/wp-sitemap-posts-cigar-1.xml"
IMAGE_PREFIX = "https://myfathercigars.com/"

# page slug → (brand, line); None line is the brand's flagship
BRANDS = {
    "my-father": ("My Father", None),
    "my-father-le-bijou-1922": ("My Father", "Le Bijou 1922"),
    "my-father-connecticut": ("My Father", "Connecticut"),
    "my-father-mf-the-judge": ("My Father", "The Judge"),
    "my-father-la-opulencia": ("My Father", "La Opulencia"),
    "my-father-la-gran-oferta": ("My Father", "La Gran Oferta"),
    "my-father-la-promesa": ("My Father", "La Promesa"),
    "my-father-blue": ("My Father", "Blue"),
    "my-father-la-lealtad": ("My Father", "La Lealtad"),
    "tabacos-baez-serie-sf": ("Tabacos Baez", "Serie SF"),
    "don-pepin-garcia-original": ("Don Pepin Garcia", "Original"),
    "don-pepin-garcia-cuban-classic": ("Don Pepin Garcia", "Cuban Classic"),
    "don-pepin-garcia-series-jj": ("Don Pepin Garcia", "Series JJ"),
    "don-pepin-garcia-vegas-cubanas": ("Don Pepin Garcia", "Vegas Cubanas"),
    "don-pepin-vintage-edition": ("Don Pepin Garcia", "Vintage Edition"),
    "don-pepin-garcia-e-r-h": ("Don Pepin Garcia", "E.R.H."),
    "la-duena": ("La Dueña", None),
    "la-antiguedad": ("La Antiguedad", None),
    "fonseca": ("Fonseca", None),
    "fonseca-mexico-edition": ("Fonseca", "Mexico Edition"),
    "flor-de-las-antillas": ("Flor de las Antillas", None),
    "flor-de-las-antillas-maduro": ("Flor de las Antillas", "Maduro"),
    "el-centurion": ("El Centurion", None),
    "el-centurion-h-2k-ct": ("El Centurion", "H-2K-CT"),
    "jaime-garcia-reserva-especial": ("Jaime Garcia", "Reserva Especial"),
    "jaime-garcia-r-e-connecticut": ("Jaime Garcia", "Reserva Especial Connecticut"),
    # "samplers-and-humidified-bags" is packaging, not a line
}
# Catalog rows re-filed by hand: the seed filed the maker's other brands under "My Father".
OVERRIDES = {
    "5fc6b5d9-3c48-4f1d-b7af-2a6f4c5984f3": {"brand": "Don Pepin Garcia", "line": "Original", "expression": "Generosos"},   # 6 x 50 is the Generosos
    "5a8c776b-8110-4255-baa0-664f7d53a57c": {"line": "Original"},                                                           # "Blue Label Generosos" at 5.63 x 46 is the Exquisitos by size; the diff decides
    "319ae248-6da4-4f22-96fe-34ecd395ed58": {"line": "Cuban Classic", "expression": "1950"},
    "48eb5592-acf7-4ee5-8291-6b7769c40ece": {"brand": "Don Pepin Garcia", "line": "Series JJ", "expression": "Toros"},
    "d3e209d5-f2c5-4d71-be9f-3898d71f1a14": {"brand": "El Centurion", "line": None, "expression": "Robusto"},              # 5.75 x 50 is the Robusto, not a Toro
    "367bc95d-1588-4637-b6dd-df0eb7735e0b": {"expression": "Torpedo Box Pressed"},                                          # the AI placeholder said torpedo
    "0eb6339d-ae74-400d-b718-42fb4762685d": {"expression": "Toro"},
    "449a42be-737b-4b86-808f-d5e17a31f7c6": {"brand": "Jaime Garcia", "line": "Reserva Especial"},
    "69d0928b-0cbf-4874-89d3-d6980ab7e189": {"brand": "Jaime Garcia", "line": "Reserva Especial"},
    "0aa6bc22-227b-4ed8-87e8-1a2ab7a7626f": {"line": None, "expression": "No. 1 Robusto"},
    # merged after apply (duplicates of rows the maker's page matches): "My Father / Flor de Las Antillas / Robusto, Toro",
    # "My Father / Don Pepin Garcia Blue Generosos", "Flor de las Antillas / Sun Grown" (the plain Robusto, 5 x 50).
    # left alone: "No. 1 / Lonsdale 7 x 44", "No. 4 / Belicoso", "Le Bijou 1922 / Robusto", "La Promesa / Robusto",
    # "Garcia y Garcia / Toro" — none match a size the maker lists; they stay as seed rows.
    # country: the writer only fills blanks, so the three Original / Series JJ seed rows that guessed Nicaragua were
    # set to United States by hand after apply — the maker says "HandCrafted in the USA" on both pages.
}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(u for u in set(re.findall(r"<loc>(https://myfathercigars\.com/cigar/[^<]+/)</loc>", xml)) if u.rstrip("/").split("/")[-1] in BRANDS)


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").strip()


def parse(url: str, page: str) -> LineRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in BRANDS:
        return None
    brand, line = BRANDS[slug]
    sizes = []
    for m in re.finditer(r"<img[^>]+src=\"([^\"]+)\"[^>]*>(?:(?!<img).)*?<h3[^>]*>([^<]*?\d[^<]*[xX]\s*\d{2,3}[^<]*)</h3>", page, re.S):
        label = re.sub(r"\s+", " ", _text(m.group(2)).replace("½", " 1/2").replace("¼", " 1/4"))
        dm = re.search(r"(\d+(?:\s+\d/\d+)?(?:\.\d+)?)\s*[xX]\s*(\d{2,3})", label)
        if not dm or re.match(r"(?i)(petaca|tin of|tubos)", label):
            continue  # packs and tins are packaging, not sizes
        L, R = dimensions(f"{dm.group(1)} x {dm.group(2)}")
        raw = label[: dm.start()].strip(" -–")
        raw = re.sub(rf"^{re.escape(brand)}\s+", "", raw, flags=re.I)  # "My Father No.1 Robusto"
        raw = re.sub(r"\bNo\.\s*(?=\d)", "No. ", raw)
        shp = shape(raw)[0]
        # "Invictos - Robusto": the maker's size name plus the vitola it is; "Toro - Maduro": the line repeated
        parts = [x.strip() for x in raw.split(" - ")]
        if len(parts) == 2:
            first, second = parts
            if second.lower() == "box pressed":
                raw = f"{first} Box Pressed"
            elif line and second.lower() == line.lower():
                raw = first
            elif re.fullmatch(VITOLA_WORDS, second.lower()):
                raw = first
            else:
                raw = f"{first} {second}"
        name = size_name(raw) or f"{dm.group(1)}x{dm.group(2)}"
        if re.search(r"[a-z][A-Z]", name):
            name = name.title()  # "TorO"
        sizes.append(Vitola(name=name, length_in=L, ring_gauge=R, image_url=m.group(1), shape=shp if shp != "parejo" else None))
    if not sizes:
        return None
    text = re.sub(r"\s+", " ", _text(page))
    blend = re.search(r"Wrapper\s*[–-]\s*(.*?)\s*\|\s*Binder\s*[–-]\s*(.*?)\s*\|\s*Filler\s*[–-]\s*(.*?)(?:\s*\||\s+Handcrafted|\s+Designed|$)", text)
    wrapper_raw = binder = filler = None
    if blend:
        wrapper_raw, binder, filler = (clean_value(x.strip(" .")) for x in blend.groups())
        if wrapper_raw:
            wrapper_raw = re.sub(r"\bCT\b", "Connecticut", wrapper_raw).replace("Broad Leaf", "Broadleaf")
    made = re.search(r"(?i)hand\s*-?\s*(?:made|crafted)\s+in\s+(?:the\s+)?(Nicaragua|Honduras|Dominican Republic|USA)", text)
    country = {"USA": "United States"}.get(made.group(1), made.group(1)) if made else None
    body = re.search(r"\b(mild to medium|medium to full|mild|medium|full)[- ]bod", text, re.I)
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    return LineRecord(brand=brand, line=line, source_url=url, wrapper_raw=wrapper_raw, binder=binder, filler=filler,
                      body=body.group(1).title() if body else None, band_image_url=og.group(1) if og else None,
                      vitolas=sizes, country=country)
