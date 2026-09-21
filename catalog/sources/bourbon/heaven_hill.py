"""Heaven Hill — heavenhilldistillery.com (one page per flagship bottling) and the brand site
elijahcraig.com for the aged single barrels and Toasted Barrel. All hand-built PHP
pages from one agency: the facts sit in a "Proof: | 94 Proof | Age: | 8-12 Years Old" block, the bottle
in an images/bottles/*.png. The distillery site's sitemap lists a third of its product pages, so the
pages are listed here by hand and cited one by one; a page that stops existing shows up as a fetch
error, not as a silent gap."""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof

PRODUCER = "Heaven Hill"
DELAY = 5
SITEMAP = "https://heavenhilldistillery.com/sitemap.xml"
IMAGE_PREFIX = "https://"
CATALOG_FAMILIES = ["Heaven Hill", "Elijah Craig", "Evan Williams", "Larceny", "Henry McKenna", "Old Fitzgerald", "Rittenhouse", "Pikesville",
                    "Bernheim", "Parker's Heritage", "Mellow Corn", "J.T.S. Brown", "J.W. Dant", "Fighting Cock", "Ezra B", "Quality House",
                    "William Heavenhill", "Old Blowhard", "Grain to Glass"]

# url → (family, expression, aliases). None = the family's flagship.
PAGES = {
    "https://heavenhilldistillery.com/hh-bottled-in-bond.php": ("Heaven Hill", "Bottled-in-Bond", ["Heaven Hill Bottled in Bond", "Heaven Hill 7 Year Bottled in Bond"]),
    "https://heavenhilldistillery.com/double-mash.php": ("Heaven Hill", "Bottled-in-Bond Double Mash", ["Heaven Hill Bottled-in-Bond Double Mash"]),
    "https://heavenhilldistillery.com/kentucky-straight-bourbon-whiskey.php": ("Heaven Hill", "Grain to Glass", ["Heaven Hill Grain to Glass Bourbon"]),
    "https://heavenhilldistillery.com/kentucky-straight-rye-whiskey.php": ("Heaven Hill", "Grain to Glass Rye", []),
    "https://heavenhilldistillery.com/kentucky-straight-wheated-bourbon-whiskey.php": ("Heaven Hill", "Grain to Glass Wheated", []),
    "https://heavenhilldistillery.com/kentucky-straight-bourbon-whiskey-specialty-barrel-series.php": ("Heaven Hill", "Grain to Glass Specialty Barrel Series: Chinquapin Oak", []),
    "https://heavenhilldistillery.com/kentucky-straight-rye-whiskey-specialty-barrel-series.php": ("Heaven Hill", "Grain to Glass Specialty Barrel Series: Chinquapin Oak Rye", []),
    "https://heavenhilldistillery.com/kentucky-straight-wheated-bourbon-whiskey-specialty-barrel-series.php": ("Heaven Hill", "Grain to Glass Specialty Barrel Series: Chinquapin Oak Wheated", []),
    "https://heavenhilldistillery.com/heavenhill-heritage-collection.php": ("Heaven Hill", "Heritage Collection", []),
    "https://heavenhilldistillery.com/henry-mckenna-single-barrel.php": ("Henry McKenna", "Single Barrel", ["Henry McKenna Single Barrel, Bottled-in-Bond", "Henry McKenna 10 Year Bottled in Bond"]),
    "https://heavenhilldistillery.com/bernheim-straight-wheat-whiskey.php": ("Bernheim", None, ["Bernheim Original Wheat Whiskey", "Bernheim Straight Wheat Whiskey", "Bernheim Original"]),
    "https://heavenhilldistillery.com/bernheim-barrel-proof.php": ("Bernheim", "Barrel Proof", ["Bernheim Original Barrel Proof Wheat"]),
    "https://heavenhilldistillery.com/rittenhouse-rye.php": ("Rittenhouse", None, ["Rittenhouse Bottled in Bond Rye", "Rittenhouse Rye", "Rittenhouse Bottled-in-Bond"]),
    "https://heavenhilldistillery.com/pikesville-straight-rye.php": ("Pikesville", None, ["Pikesville 6 Year Rye", "Pikesville Straight Rye"]),
    "https://heavenhilldistillery.com/old-fitzgerald-7-year-old.php": ("Old Fitzgerald", "7 Year", ["Old Fitzgerald 7 Year Old"]),  # the catalog's verified "Old Fitzgerald" is a BiB release, not this
    "https://heavenhilldistillery.com/old-fitzgerald.php": ("Old Fitzgerald", "Bottled-in-Bond", ["Old Fitzgerald Bottled in Bond Edition", "Old Fitzgerald Bottled in Bond 9 Year Release"]),
    "https://heavenhilldistillery.com/parkers-heritage-collection.php": ("Parker's Heritage", None, ["Parker's Heritage Collection"]),
    "https://heavenhilldistillery.com/mellow-corn.php": ("Mellow Corn", None, ["Mellow Corn Bottled in Bond"]),
    "https://heavenhilldistillery.com/elijah-craig-small-batch.php": ("Elijah Craig", "Small Batch", ["Elijah Craig", "EC Small Batch"]),
    "https://heavenhilldistillery.com/elijah-craig-barrel-proof.php": ("Elijah Craig", "Barrel Proof", ["ECBP"]),
    "https://heavenhilldistillery.com/elijah-craig-barrel-proof-rye.php": ("Elijah Craig", "Barrel Proof Rye", []),
    "https://heavenhilldistillery.com/elijah-craig-rye.php": ("Elijah Craig", "Rye", ["Elijah Craig Straight Rye"]),
    "https://heavenhilldistillery.com/elijah-craig-toasted-rye.php": ("Elijah Craig", "Toasted Rye", []),
    "https://heavenhilldistillery.com/elijah-craig-single-barrel18.php": ("Elijah Craig", "18 Year Single Barrel", ["Elijah Craig 18 Year"]),
    "https://heavenhilldistillery.com/elijah-craig-single-barrel23.php": ("Elijah Craig", "23 Year Single Barrel", ["Elijah Craig 23 Year"]),
    # elijahcraig.com pages carry the whole lineup's bottles in their nav; the page's own bottle is named here.
    "https://elijahcraig.com/toasted-barrel.php": ("Elijah Craig", "Toasted Barrel", ["Elijah Craig Toasted Barrel Finish"], "/images/bottles/ec-toasted-barrel.png"),
    "https://elijahcraig.com/15-year-old.php": ("Elijah Craig", "15 Year Single Barrel", ["Elijah Craig 15 Year"], "/images/years-old-15.png"),
    "https://elijahcraig.com/21-year-old.php": ("Elijah Craig", "21 Year Single Barrel", ["Elijah Craig 21 Year"], "/images/bottles/ec-single-barrel-21y.png"),
    "https://heavenhilldistillery.com/evan-williams-bourbon.php": ("Evan Williams", "Black Label", ["Evan Williams", "Evan Williams Bourbon"]),
    "https://heavenhilldistillery.com/ew-bottled-in-bond.php": ("Evan Williams", "Bottled in Bond", ["Evan Williams White Label", "Evan Williams Bottled-in-Bond"]),
    "https://heavenhilldistillery.com/evan-williams-1783-small-batch.php": ("Evan Williams", "1783 Small Batch", ["Evan Williams 1783"]),
    "https://heavenhilldistillery.com/evan-williams-single-barrel-vintage.php": ("Evan Williams", "Single Barrel", ["Evan Williams Single Barrel Vintage"]),
    "https://heavenhilldistillery.com/larceny-bourbon.php": ("Larceny", None, ["Larceny Small Batch", "Larceny Bourbon"]),
    "https://heavenhilldistillery.com/larceny-barrel-proof.php": ("Larceny", "Barrel Proof", []),
}
# The label's class by family where the name doesn't carry it; Bottled-in-Bond where the label says so.
FAMILY_CLASS = {"Rittenhouse": "Kentucky Straight Rye Whiskey Bottled-in-Bond", "Pikesville": "Kentucky Straight Rye Whiskey",
                "Mellow Corn": "Kentucky Straight Corn Whiskey Bottled-in-Bond", "Bernheim": "Kentucky Straight Wheat Whiskey",
                "Henry McKenna": "Kentucky Straight Bourbon Whiskey Bottled-in-Bond", "Old Fitzgerald": "Kentucky Straight Bourbon Whiskey",
                "Larceny": "Kentucky Straight Bourbon Whiskey"}
WHEATED = {"Larceny", "Old Fitzgerald"}
NOT_CORE = re.compile(r"parker's|15 year|18 year|21 year|23 year|12 year|old fitzgerald bottled|double mash|specialty", re.I)
RARITY = [
    (r"parker's|elijah craig (18|21|23)|evan williams 23|old fitzgerald bottled", "lottery"),
    (r"barrel proof|elijah craig 15|henry mckenna single|evan williams 12|double mash", "allocated"),
    (r"toasted|grain to glass", "limited"),
    (r".", "shelf"),
]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(PAGES)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    family, expression, aliases, *fixed_image = PAGES[url]
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    m = re.search(r"Proof:\|\s*([^|]+)\|", flat)
    proof_raw = m.group(1).strip() if m else None
    pf = proof(proof_raw) if proof_raw and not re.search(r"varies", proof_raw, re.I) else None
    m = re.search(r"Age:\|\s*([^|]+)\|", flat)
    age_raw = m.group(1).replace("-->", "").strip() if m else None
    years, label = (None, None)
    if age_raw:
        rng = re.match(r"(\d{1,2})\s*-\s*(\d{1,2})\s*years?", age_raw, re.I)  # "8-12 Years Old" is a range the label doesn't print: display only
        years, label = (None, f"{rng.group(1)}–{rng.group(2)} yr") if rng else age(age_raw)
        if age_raw.upper().startswith("NAS"):
            label = "NAS"
    if years is None and label is None and expression:
        years, label = age(expression)  # "15 Year Single Barrel": the name is the statement
    m = re.search(r"(\d{1,3}%\s*[A-Za-z ]+(?:[,&/]|and)?\s*){2,}", flat)  # a recipe the page states in percentages
    mash_raw = m.group(0).strip(" |,") if m else None
    title = _text((re.search(r"<title>(.*?)</title>", page, re.S) or [None, ""])[1]) or ""
    img = urljoin(url, fixed_image[0]) if fixed_image else None
    for tag in re.findall(r"<img[^>]+>", page) if img is None else []:  # the product's own bottle shot, never a news thumbnail
        src = (re.search(r'src="([^"]+)"', tag) or [None, ""])[1]
        if re.search(r'class="brand-bottle', tag):
            img = urljoin(url, src.split("?")[0])
            break
    if img is None and (m := re.search(r'property="og:image" content="([^"]+)"', page)) and re.search(r"\.(png|jpg|jpeg)", m.group(1), re.I):
        img = m.group(1)
    desc = None
    if (m := re.search(r'name="description" content="([^"]+)"', page)):
        desc = _text(m.group(1))
    name = family if expression is None else f"{family} {expression}"
    class_raw = "Kentucky Straight Rye Whiskey" if re.search(r"\brye\b", name, re.I) else FAMILY_CLASS.get(family, "Kentucky Straight Bourbon Whiskey")
    if re.search(r"bottled[- ]in[- ]bond", name, re.I) and "Bottled-in-Bond" not in class_raw:
        class_raw += " Bottled-in-Bond"
    mash = "wheated" if (family in WHEATED or "Wheated" in name) and "Double Mash" not in name else None  # else from the stated recipe
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style=mash, description=desc, image_url=img,
        aliases=sorted({*aliases, title.split("|")[-1].strip()} - {name, ""}), is_core_range=not NOT_CORE.search(name),
    )
