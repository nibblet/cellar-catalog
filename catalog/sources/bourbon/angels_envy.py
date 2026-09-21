"""angelsenvy.com (Bacardi; WordPress + Gutenberg, US pages under /us/en/). /our-whiskey/ links a page per
collection and each collection page links its bottlings (/whiskeys/<collection>/<slug>/). Every bottling
page carries a schema.org Product (name, alternateName, description, images) and marketing copy; the
proof, where stated, is in prose ("Bottled at 117.8 Proof (58.9% ABV)"). The Signature Series flagships
(port-finished bourbon, rum-finished rye) state no proof anywhere on the site, so they are listed but not
confirmed. Cask Strength keeps every edition's page: the newest edition is the bottling. The Cellar
Collection is one bottling whose current volume is the newest page. The Distillery Series (gift-shop
releases on one index page) and the private-selection barrel program are not catalog bottlings."""
from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, titlecase

PRODUCER = "Angel's Envy"
DELAY = 6
SITEMAP = "https://www.angelsenvy.com/us/en/page-sitemap.xml"
IMAGE_PREFIX = "https://d3cqmwe6z7cbal.cloudfront.net/"
INDEX = "https://www.angelsenvy.com/us/en/our-whiskey/"
CATALOG_FAMILIES = ["Angel's Envy"]
PRODUCER_BY_FAMILY = {}
COLLECTIONS = ["signature-series", "cask-strength", "cellar-collection", "bottled-in-bond"]

# slug → (expression, aliases). Older Cask Strength editions map to the same expression; the newest page wins.
REFILE = {
    "port-wine-finished-bourbon": ("Port Finish", ["Angel's Envy Port Barrel Finish", "Angel's Envy Bourbon", "Angel's Envy Kentucky Straight Bourbon Finished in Port Wine Barrels", "Angel's Envy Port Wine Finish"]),
    "rum-cask-finished-rye": ("Rye", ["Angel's Envy Rye Finished in Rum Casks", "Angel's Envy Rum Finish Rye", "Angel's Envy Rye Rum Cask Finish"]),
    "triple-oak-bourbon": ("Triple Oak", ["Angel's Envy Triple Oak Bourbon"]),
    "11th-edition-port-wine-cask": ("Cask Strength", []),
    "12th-edition-port-wine-cask": ("Cask Strength", []),
    "13th-edition-cask-strength-bourbon": ("Cask Strength", []),
    "15th-edition-cask-strength-bourbon": ("Cask Strength", ["Angel's Envy Cask Strength Bourbon", "Angel's Envy Cask Strength Port Finish"]),
    "12th-edition-cask-strength-rye": ("Cask Strength Rye", ["Angel's Envy Cask Strength Rye 1st Edition"]),
    "14th-edition-cask-10": ("10 Year Cask Strength", ["Angel's Envy 10 Cask Strength", "Angel's Envy 10 Cask Strength Bourbon"]),
    "10-cask-rye": ("10 Year Cask Strength Rye", ["Angel's Envy 10 Cask Strength Rye"]),
    "cask-strength-bottled-in-bond": ("Bottled in Bond", ["Angel's Envy Bottled-in-Bond", "Angel's Envy Cask Strength Bottled-in-Bond"]),
}
CELLAR = re.compile(r"^\d{4}-")  # cellar-collection/<year>-<finish>: one bottling, newest year current
NOT_CORE = re.compile(r"cask strength|cellar collection|bottled in bond", re.I)
RARITY = [(r"cellar collection|10 year", "unicorn"), (r"cask strength|bottled in bond", "lottery"), (r"triple oak", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = set()
    for c in COLLECTIONS:
        page = fetcher.get(f"https://www.angelsenvy.com/us/en/whiskeys/{c}/")
        for u in re.findall(rf'href="(https://www\.angelsenvy\.com/us/en/whiskeys/{c}/[a-z0-9-]+/)"', page):
            slug = u.rstrip("/").split("/")[-1]
            if slug in REFILE or (c == "cellar-collection" and CELLAR.match(slug)):
                urls.add(u)
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace(" ", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _product(page: str) -> dict:
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        for it in d.get("@graph", [d]) if isinstance(d, dict) else d:
            if isinstance(it, dict) and it.get("@type") == "Product":
                return it
    return {}


def parse(url: str, page: str) -> BottlingRecord | None:
    parts = urlparse(url).path.rstrip("/").split("/")
    collection, slug = parts[-2], parts[-1]
    if slug in REFILE:
        expression, aliases = REFILE[slug]
    elif collection == "cellar-collection" and CELLAR.match(slug):
        expression, aliases = "Cellar Collection", []
    else:
        return None
    name = f"Angel's Envy {expression}"
    prod = _product(page)
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'").replace(" ", " ")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = re.split(r"Cask Strength Series|Our whiskey collection|Angel's Envy Articles|Cocktails for every occasion|Become a Part of 500 Main", flat)[0]
    own = own.split("| Menu Item| ")[-1]  # after the navigation
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?) ?proof\b", own, re.I)
    pf = float(m.group(1)) if m else None
    body = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)
    desc = _text(prod.get("description")) or _text((re.search(r'class="[^"]*block-cover__description[^"]*"[^>]*>(.*?)</', body, re.S) or [None, ""])[1])
    title = _text(prod.get("name")) or _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    years, label = age(expression)
    if years is None:
        m = re.search(r"aged (?:for )?(?:a )?(?:combined|cumulative) (\d{1,2}) years", own, re.I)
        if m:
            years, label = float(m.group(1)), f"{m.group(1)} yr"
    if years is None and label is None:
        m = re.search(r"aged up to (\d{1,2}) years", own, re.I)
        if m:
            label = f"up to {m.group(1)} yr"
    if years is None and label is None:
        years, label = age(desc or "")
    rye = bool(re.search(r"\brye\b", f"{expression} {title or ''}", re.I)) or bool(re.search(r"Straight Rye Whiskey", own[:2500]))
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"
    if expression == "Bottled in Bond":
        class_raw += " Bottled-in-Bond"
    if expression == "Cellar Collection" and re.search(r"Bourbon", title or "", re.I):
        class_raw = "Kentucky Straight Bourbon Whiskey"
    # Finish: the maker's wording ("Finished in Port Wine Barrels", "Finished in French Oak Extra Añejo Tequila Barrels").
    fm = re.search(r"finished in ([\w'&\- ]+? (?:barrels|casks))", f"{title or ''} {own[:1500]}", re.I)
    finish = fm.group(1).strip().title().replace("Anejo", "Añejo").replace(" And ", " and ") if fm else ("Port Wine Barrels" if "Cask Strength" in expression and "Rye" not in expression else None)
    if expression == "Rye" and not fm:
        finish = "Rum Casks"
    if expression == "Triple Oak":
        finish = "Triple Oak"
    if expression == "Bottled in Bond":
        finish = None
    imgs = [i for i in prod.get("image", []) if isinstance(i, str)] + re.findall(r'(?:data-src|src)="([^"]+cloudfront[^"]+\.(?:png|jpg|jpeg|webp))', page)
    img = next((i for i in imgs if re.search(r"bottle|producthero|packshot", i, re.I) and not re.search(r"nav|menu|meta|320x480|banner", i, re.I)), None) \
        or next((i for i in imgs if re.search(r"hero", i, re.I) and not re.search(r"nav|menu|meta|320x480|banner", i, re.I)), None) \
        or next((i for i in imgs if not re.search(r"nav|menu|meta|logo|icon|320x480|cocktail|article|distillery|brandmark", i, re.I)), None)
    aliases = set(aliases)
    for raw in (title, prod.get("alternateName")):  # page titles are marketing lines as often as names
        raw = _text(raw)
        if not raw or re.search(r"[!.]|distinctly|remastering|^envy\b", raw, re.I) or not re.search(r"bourbon|rye|cask|cellar|bottled|oak|finish", raw, re.I):
            continue
        if re.search(r"[a-z]\d|inmadeira|strengthrye|collectionseries", raw, re.I):
            continue  # the site's schema names lose the space at a line break ("Bourbon11th edition")
        aliases.add("Angel's Envy " + titlecase(re.sub(r"(?i)^angel'?s envy\s*", "", raw)))
    if expression == "Cellar Collection":
        aliases.add(f"Angel's Envy Cellar Collection {slug[:4]}")
    return BottlingRecord(
        brand_family="Angel's Envy", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style="rye" if rye else None, description=desc, image_url=html.unescape(img) if img else None,
        finish=finish, aliases=sorted(a for a in aliases if a and a != name), is_core_range=not NOT_CORE.search(name),
    )
