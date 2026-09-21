"""Diageo's American whiskeys. Bulleit has its own site (bulleit.com, Contentful; a product page with copy,
tasting notes and the legal line "BULLEIT BOURBON Kentucky Straight Bourbon Whiskey. 45% Alc/Vol."). George
Dickel, Blade and Bow and I.W. Harper have no product pages of their own: georgedickel.com redirects each
whisky to Diageo's store, thebar.com (or to a brand/recipes page when the store no longer sells it), whose product pages carry the copy ("This 100 proof whisky has been
matured for 13 years"), a bullet ("One 91 proof 750 ml bottle"), the legal line and a front bottle shot.
thebar.com is Diageo's own store, so it counts as the maker's page for Diageo's brands."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, titlecase

PRODUCER = "Diageo"
DELAY = 6
SITEMAP = "https://www.bulleit.com/en-us/sitemap.xml"
IMAGE_PREFIX = "https://images.ctfassets.net/"
CATALOG_FAMILIES = ["Bulleit", "George Dickel", "Blade and Bow", "I.W. Harper", "Cascade Hollow"]
PRODUCER_BY_FAMILY = {"Bulleit": ("Bulleit", "a45bfe4f-6b86-4253-9579-64227ed4dd36"), "George Dickel": ("George Dickel", "acd69a9c-a047-472a-9018-bae403ef553d"),
                      "I.W. Harper": ("I.W. Harper", "ea82ebe6-6a0f-4b8b-8cf2-bdc8a936cc34"), "Blade and Bow": ("Diageo", None)}

BRAND_PAGES = ["https://www.thebar.com/en-us/brands/blade-and-bow", "https://www.thebar.com/en-us/brands/i-w-harper", "https://www.thebar.com/en-us/brands/george-dickel"]

# slug (last path segment) → (family, expression, aliases). None = the flagship.
REFILE = {
    "bulleit-bourbon": ("Bulleit", "Bourbon", ["Bulleit Bourbon Frontier Whiskey"]),
    "bulleit-bourbon-10-year-old": ("Bulleit", "10 Year", ["Bulleit Bourbon 10 Year Old", "Bulleit 10 Year Aged Bourbon"]),
    "bulleit-rye-whiskey": ("Bulleit", "95 Rye", ["Bulleit Rye", "Bulleit 95 Rye", "Bulleit 95 Whiskey Rye"]),
    "bulleit-barrel-strength": ("Bulleit", "Barrel Strength", ["Bulleit Bourbon Barrel Strength"]),
    "bulleit-american-single-malt": ("Bulleit", "American Single Malt", []),
    "bulleit-rye-10-year-old": ("Bulleit", "95 Rye 10 Year", ["Bulleit 10 Year Aged Rye", "Bulleit Rye 10 Year"]),
    "bulleit-bottled-in-bond": ("Bulleit", "Bottled in Bond", []),
    "bulleit-mesquite-smoked-malt": ("Bulleit", "Mesquite Smoked Malt", []),
    "george-dickel-bourbon-whisky-aged-8-years-750-ml": ("George Dickel", "Bourbon", ["George Dickel Bourbon Whisky Aged 8 Years", "George Dickel 8 Year Bourbon"]),
    "george-dickel-signature-recipe-tennessee-whisky-750-ml": ("George Dickel", "Signature Recipe", ["George Dickel Superior No. 12", "George Dickel No. 12"]),
    "george-dickel-and-leopold-brothers-collaboration-blend-rye-whisky-750-ml": ("George Dickel", "x Leopold Bros. Collaboration Blend Rye", ["George Dickel x Leopold Bros. Collaboration Blend Rye", "Dickel x Leopold Bros Collab Blend"]),
    "george-dickel-barrel-select-750-ml": ("George Dickel", "Barrel Select", []),
    "george-dickel-9-year-old-single-barrel-750-ml": ("George Dickel", "9 Year Single Barrel", []),
    "george-dickel-15-year-old-single-barrel-750-ml": ("George Dickel", "15 Year Single Barrel", []),
    "george-dickel-17-year-old-reserve-tennessee-whisky-750-ml": ("George Dickel", "17 Year Reserve", []),
    "george-dickel-bottled-in-bond-tennessee-whisky-750-ml": ("George Dickel", "Bottled in Bond", ["George Dickel Bottled In Bond"]),
    "george-dickel-rye-whisky-750-ml": ("George Dickel", "Rye", ["George Dickel Rye Whisky"]),
    "blade-bow-kentucky-straight-bourbon-750-ml": ("Blade and Bow", None, ["Blade and Bow Kentucky Straight Bourbon"]),
    "iw-harper-kentucky-straight-bourbon-whiskey-750-ml": ("I.W. Harper", None, ["I.W. Harper Kentucky Straight Bourbon"]),
    "iw-harper-15-year-old-750-ml": ("I.W. Harper", "15 Year", []),
    "i-w-harper-cabernet-cask-reserve-750-ml": ("I.W. Harper", "Cabernet Cask Reserve", []),
}
NOT_CORE = re.compile(r"10 year|12 year|15 year|17 year|18 year|barrel strength|bottled in bond|single barrel|reserve|collab|mesquite|cabernet", re.I)
RARITY = [(r"17 year|18 year|15 year single|collab", "lottery"), (r"barrel strength|10 year|12 year|15 year|single barrel|cabernet", "allocated"), (r"bottled in bond|mesquite|single malt|barrel select", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = set(re.findall(r"<loc>(https://www\.bulleit\.com/whiskeys/[^<]+)</loc>", fetcher.get(SITEMAP)))
    urls -= {u for u in urls if u.endswith("10-year-aged-whiskeys")}  # an index page
    urls |= set(re.findall(r"<loc>(https://www\.georgedickel\.com/whiskies/[^<]+)</loc>", fetcher.get("https://www.georgedickel.com/en-us/sitemap.xml")))
    for b in BRAND_PAGES:  # the store also lists Dickel bottlings the brand site's sitemap sends to a recipes page
        urls |= {"https://www.thebar.com" + p for p in re.findall(r'href="(/en-us/products/[^"?#]+)"', fetcher.get(b))}
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    # georgedickel.com redirects to thebar.com; the canonical link says where it landed (a brand or recipes
    # page for whiskies the store no longer sells, which is not a product page).
    canonical = re.search(r'rel="canonical" href="([^"]+)"', page)
    landed = canonical.group(1) if canonical and "thebar.com" in canonical.group(1) else url
    if "thebar.com" in landed and "/products/" not in landed:
        return None
    slug = urlparse(landed).path.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    family, expression, aliases = REFILE[slug]
    name = f"{family} {expression}" if expression else family
    h1 = _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    # The product's own copy: from its title to the store's boilerplate / the next product.
    start = flat.find(h1) if h1 else 0
    own = re.split(r"Why buy from The Bar|Try This Drink|You may also like|Explore the range|Share on Social Media", flat[start:])[0][:8000]
    # The Bottled-in-Bond Act paragraph ("a minimum of four years") describes the law, not this bottling.
    own = re.sub(r"[^|]*Bottled-in-Bond Act[^|]*\|", "", own)
    # Proof: a "N proof" statement in the copy or bullets, else the legal line's ABV.
    pf = None
    # "distilled to 160 proof (80% abv) or less" is the single-malt definition, not the bottling.
    m = re.search(r"(?<!distilled to )\b(\d{2,3}(?:\.\d+)?)[- ]proof\b", own, re.I)
    if m and not re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}[- ]proof", own, re.I):
        pf = float(m.group(1))
    if pf is None:  # the legal line ("BULLEIT BOURBON Kentucky Straight Bourbon Whiskey. 45% Alc/Vol.") sits past the copy
        m = re.search(r"(\d{2}(?:\.\d+)?)\s*% ?Alc", own) or re.search(r"(\d{2}(?:\.\d+)?)\s*% ?Alc/Vol", flat)
        pf = round(float(m.group(1)) * 2, 1) if m else None
    # Age from the title and description only: the store's tasting notes borrow a sibling's ("I.W. Harper 15-Year-Old").
    years, label = age(" ".join(x for x in (h1, re.split(r"Tasting notes", own[:3000], flags=re.I)[0]) if x))
    if years is None and label is None and expression:
        years, label = age(expression)
    if family == "George Dickel" and "Rye" in (expression or ""):
        class_raw = "Straight Rye Whisky" if expression == "Rye" else "Rye Whisky"
    elif family == "George Dickel":
        class_raw = "Tennessee Whisky" if "Bourbon" not in expression else "Kentucky Straight Bourbon Whisky"
        if "Bourbon" in expression:
            class_raw = "Bourbon Whisky"
    elif re.search(r"rye", name, re.I) and "Bourbon" not in name:
        class_raw = "Kentucky Straight Rye Whiskey"
    elif re.search(r"single malt|smoked malt", name, re.I):
        class_raw = "American Single Malt Whiskey"
    else:
        class_raw = "Kentucky Straight Bourbon Whiskey"
    if re.search(r"bottled in bond", name, re.I):
        class_raw += " Bottled-in-Bond"
    # Image: the store names the bottle shot "<product>_front" / "-front"; bulleit.com has a lifestyle hero, a
    # cocktail, the bottle ("Bulleit Bourbon Whiskey" alt, plain file name) and sibling "-tout" thumbs.
    imgs = []
    for tag in re.findall(r"<img[^>]+>", page):
        src, alt = re.search(r'src="([^"]+)"', tag), re.search(r'alt="([^"]*)"', tag)
        if src and "ctfassets" in src.group(1):
            imgs.append((html.unescape(src.group(1)).split("?")[0], html.unescape(alt.group(1)) if alt else ""))
    if "bulleit.com" in url:  # the plain bottle shot, else the hero (a bottle in a setting) when that is all the page has
        img = next((i for i, a in imgs if not re.search(r"tout|Asset_|hero|lifestyle|cocktail|glass|signup|logo|label|stamp", i + " " + a, re.I)), None) \
            or next((i for i, a in imgs if re.search(r"bottle", a, re.I) and not re.search(r"tout", i)), None)
    else:  # the store's gallery leads with the product's own front shot
        img = next((i for i, a in imgs if re.search(r"bottle", a, re.I) and not re.search(r"hero|[-_]serve|back|side|logo|icon|lifestyle", i, re.I)), None)
    if img and img.startswith("//"):
        img = "https:" + img
    mash_raw = (re.search(r"\d{1,3}% rye[^|.]*", own) or [None])[0]
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw, mash_style="rye" if "Rye" in class_raw else None, description=_text(own[:600]),
        image_url=img, aliases=sorted({*aliases, *([h1] if h1 else [])} - {name}), is_core_range=not NOT_CORE.search(name),
    )
