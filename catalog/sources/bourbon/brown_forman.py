"""Brown-Forman's American whiskey sites — oldforester.com and cooperscraft.com (WordPress, one product
page each; proof in the copy or the title), woodfordreserve.com (WordPress; a "Proof | 90.4 °" tasting
note; the og:image is a seasonal bottle, so the product image is read from the summary block) and
jackdaniels.com (Next.js; schema.org Product with name, description and bottle image; proof in the
copy). Jack Daniel's current lineup is what its listing pages link to; the /whiskey/limited/ decanters
and replicas are history, not products. Flavored whiskeys and RTDs are skipped.

`tasting_notes` is each page's own tasting block, read the way its site lays it out: Old Forester's three icon cards
(aroma / taste / finish), Woodford's Nose / Taste / Finish after its Proof and Appearance lines, Coopers' Craft's "Flavor
Profile" (the nose, the taste, the finish), and Jack Daniel's aroma / taste / finish strip. Jack Daniel's pages without that
strip (the Distillery Series, the aged and single-barrel releases) keep only the intro sentences that name notes, nose or palate.
The "you might also like" cards, cocktail recipes and sibling lists on every page are never read."""
from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof, titlecase

PRODUCER = "Brown-Forman"
DELAY = 5
SITEMAP = "https://www.oldforester.com/products-sitemap.xml"
IMAGE_PREFIX = "https://"
CATALOG_FAMILIES = ["Old Forester", "Woodford Reserve", "Jack Daniel's", "Coopers' Craft", "Early Times"]

SKIP = re.compile(r"bitters|syrup|tincture|mint-julep|decanter|kentucky-derby|coca-cola|country-cocktails|/flavors$|apple|fire$|honey|lemonade|"
                  r"ginger|winter-jack|blackberry|mclaren|historical|on-the-go|/premium$|bonded-series$|single-barrel-collection$|limited-edition$|"
                  r"saloon|master-distiller-series|sinatra-century|no-27-gold|eric-church|limited-edition-gentleman|holiday|/whiskey/limited/|"
                  r"personal-selection|our-products|whiskey/distillery-series/?$|old-forester-\d{4}-(fall-|spring-)?birthday", re.I)  # old Birthday vintages: the bare-year slug is the current one

HOSTS = {
    "www.oldforester.com": ("Old Forester", r"^/products/[^/]+/?$", []),
    "www.woodfordreserve.com": ("Woodford Reserve", r"^/whiskey/[^/]+/?$", []),
    "www.cooperscraft.com": ("Coopers' Craft", r"^/bourbon/[^/]+/?$", []),
    "www.jackdaniels.com": ("Jack Daniel's", r"^/whiskey/[^/]+$", ["/our-products", "/whiskey/premium", "/whiskey/bonded-series", "/whiskey/single-barrel-collection", "/whiskey/limited-edition"]),
}
SITEMAPS = {"www.oldforester.com": "/products-sitemap.xml", "www.woodfordreserve.com": "/product-sitemap.xml", "www.cooperscraft.com": "/bourbon-sitemap.xml"}

# slug → (family, expression, aliases the catalog may know it by). None = the flagship.
REFILE = {
    "old-forester-86-proof": ("Old Forester", "86 Proof", ["Old Forester Classic Bourbon", "Old Forester 86"]),
    "old-forester-100-proof": ("Old Forester", "100 Proof", ["Old Forester Signature Bourbon", "Old Forester Signature", "Old Forester 100"]),
    "old-forester-100-proof-rye-whisky": ("Old Forester", "Rye", ["Old Forester Rye", "Old Forester 100 Proof Rye"]),
    "old-forester-single-barrel-100-proof": ("Old Forester", "Single Barrel", ["Old Forester Single Barrel 100 Proof"]),
    "old-forester-single-barrel-barrel-proof": ("Old Forester", "Single Barrel Barrel Proof", ["Old Forester Single Barrel, Barrel Strength", "Old Forester Single Barrel Barrel Strength"]),
    "old-forester-single-barrel-rye": ("Old Forester", "Single Barrel Rye", []),
    "old-forester-1920-style-prohibition-whisky": ("Old Forester", "1920 Prohibition Style", []),
    "old-forester-1924-10-year-old-whisky": ("Old Forester", "1924, 10 Year", ["Old Forester 1924 — 10 Year", "Old Forester 1924"]),
    "old-forester-presidents-choice-bourbon": ("Old Forester", "President's Choice", []),
    "old-forester-king-ranch-edition": ("Old Forester", "King Ranch", ["Old Forester King Ranch Edition"]),
    "old-forester-statesman-bourbon": ("Old Forester", "Statesman Bourbon", ["Old Forester Statesman"]),
    "old-forester-1910-old-fine-whisky": ("Old Forester", "1910 Old Fine Whisky", ["Old Forester 1910"]),
    "117-series-1910-extra-extra-old": ("Old Forester", "117 Series: 1910 Extra Extra Old", ["Old Forester The 117 Series: Extra Extra Old"]),
    "117-series-1910-extra-old": ("Old Forester", "117 Series: 1910 Extra Old", ["Old Forester The 117 Series: 1910 Extra Old"]),
    "straight-bourbon-whiskey": ("Woodford Reserve", "Distiller's Select", ["Woodford Reserve", "Woodford Reserve Bourbon"]),
    "double-oaked": ("Woodford Reserve", "Double Oaked", []),
    "double-double-oaked": ("Woodford Reserve", "Double Double Oaked", []),
    "rye-whiskey": ("Woodford Reserve", "Distiller's Select Rye", ["Woodford Reserve Rye"]),
    "malt-whiskey": ("Woodford Reserve", "Straight Malt", ["Woodford Reserve Malt Whiskey"]),
    "wheat-whiskey": ("Woodford Reserve", "Wheat Whiskey", []),
    "wheat-whiskey-bottled-in-bond": ("Woodford Reserve", "Wheat Whiskey Bottled in Bond", []),
    "batch-proof": ("Woodford Reserve", "Master's Collection: Batch Proof", ["Woodford Reserve Batch Proof"]),
    "masters-collection": ("Woodford Reserve", "Master's Collection", []),
    "masters-collection-sonoma-triple-finish": ("Woodford Reserve", "Master's Collection: Sonoma Triple Finish", []),
    "distillery-series": ("Woodford Reserve", "Distillery Series", []),
    "distillery-series-toasted-oak-four-grain": ("Woodford Reserve", "Distillery Series: Toasted Oak Four Grain", []),
    "toasted-oak-oat-grain": ("Woodford Reserve", "Toasted Oak Oat Grain", []),
    "honey-barrel-finish": ("Woodford Reserve", "Distillery Series: Honey Barrel Finish", []),
    "historic-barrel-entry": ("Woodford Reserve", "Master's Collection: Historic Barrel Entry", []),
    "baccarat-edition": ("Woodford Reserve", "Baccarat Edition", []),
    "original": ("Coopers' Craft", None, ["Coopers Craft", "Coopers' Craft Original"]),
    "barrel-reserve": ("Coopers' Craft", "Barrel Reserve", ["Coopers' Craft Barrel Reserve 100 Proof"]),
    "old-no-7": ("Jack Daniel's", "Old No. 7", ["Jack Daniel's", "Old No 7", "Jack Daniel's Tennessee Whiskey"]),
    "gentleman-jack": ("Jack Daniel's", "Gentleman Jack", []),
    "gentleman-jack-double-mellowed-tennessee-whiskey": ("Jack Daniel's", "Gentleman Jack", []),
    "jack-daniels-single-barrel-select-tennessee-whiskey": ("Jack Daniel's", "Single Barrel Select", ["Jack Daniel's Single Barrel"]),
    "jack-daniels-single-barrel-tennessee-rye-whiskey": ("Jack Daniel's", "Single Barrel Rye", []),
    "jack-daniels-bonded-tennessee-whiskey": ("Jack Daniel's", "Bonded", ["Jack Daniel's Bonded Tennessee Whiskey"]),
    "jack-daniels-bonded-tennessee-rye-whiskey": ("Jack Daniel's", "Bonded Rye", []),
    "jack-daniels-bonded-triple-mash": ("Jack Daniel's", "Triple Mash", ["Jack Daniel's Triple Mash Blended", "Jack Daniel's Bonded Triple Mash"]),
    "jack-daniels-sinatra-select-tennessee-whiskey": ("Jack Daniel's", "Sinatra Select", ["Sinatra"]),
    "jack-daniels-10-year-old-tennessee-whiskey": ("Jack Daniel's", "10 Year", ["Jack Daniel's 10 Yr"]),
    "jack-daniels-12-year-old-tennessee-whiskey": ("Jack Daniel's", "12 Year", ["Jack Daniel's 12 Yr"]),
    "14-year-old-tennessee-whiskey": ("Jack Daniel's", "14 Year", []),
    "jack-daniels-single-barrel-100-proof-tennessee-whiskey": ("Jack Daniel's", "Single Barrel 100 Proof", []),
    "jack-daniels-single-barrel-barrel-proof-tennessee-whiskey": ("Jack Daniel's", "Single Barrel Barrel Proof", []),
    "jack-daniels-single-barrel-barrel-strength-tennessee-whiskey": ("Jack Daniel's", "Single Barrel Barrel Strength", []),
    "jack-daniels-single-barrel-heritage-barrel-tennessee-whiskey": ("Jack Daniel's", "Single Barrel Heritage Barrel", []),
    "single-barrel-special-release-barrel-proof-rye": ("Jack Daniel's", "Single Barrel Special Release Barrel Proof Rye", []),
    "single-barrel-tennessee-rye-special-release-tanyard-hill": ("Jack Daniel's", "Single Barrel Special Release Tanyard Hill Rye", []),
    "jack-daniel-distillery-150th-anniversary-whiskey": ("Jack Daniel's", "150th Anniversary", []),
}
BIRTHDAY = re.compile(r"(?:^|-)\d{4}-(?:fall-|spring-)?birthday-bourbon$")  # every vintage is the one Birthday Bourbon
NOT_CORE = re.compile(r"birthday|117 series|president|king ranch|1924|master's collection|distillery series|batch proof|baccarat|double double|"
                      r"toasted oak|honey barrel|historic barrel|sonoma|special release|150th|14 year|12 year|10 year|heritage barrel|barrel strength|"
                      r"single barrel barrel proof|sinatra|wheat whiskey bottled", re.I)
RARITY = [
    (r"birthday|president's choice|150th|14 year|sonoma|master's collection: batch proof$", "lottery"),
    (r"117 series|king ranch|1924|master's collection|distillery series|batch proof|baccarat|double double|special release|12 year|10 year|heritage barrel|barrel strength|single barrel barrel proof|historic barrel|toasted oak|honey barrel", "allocated"),
    (r"sinatra|wheat whiskey bottled|single barrel rye|statesman", "limited"),
    (r".", "shelf"),
]
MASH_BILLS = {}
PRODUCER_BY_FAMILY = {"Jack Daniel's": ("Jack Daniel's", "cc780290-0e4c-413e-a92d-4893327810f5")}  # the Lynchburg distillery has its own maker record


def _links(page: str, host: str, pattern: str) -> set[str]:
    out = set()
    for href in re.findall(r'href="([^"#?]+)"', page):
        path = urlparse(href).path if href.startswith("http") else href
        if href.startswith("http") and urlparse(href).netloc != host:
            continue
        if re.search(pattern, path):
            out.add(f"https://{host}{path.rstrip('/')}" + ("/" if host != "www.jackdaniels.com" else ""))
    return out


def list_urls(fetcher) -> list[str]:
    urls: set[str] = set()
    for host, (_, pattern, indexes) in HOSTS.items():
        if host in SITEMAPS:
            xml = fetcher.get(f"https://{host}{SITEMAPS[host]}")
            urls |= {u for u in re.findall(r"<loc>(https://" + re.escape(host) + r"[^<]*)</loc>", xml) if re.search(pattern, urlparse(u).path)}
        for idx in indexes:
            urls |= _links(fetcher.get(f"https://{host}{idx}"), host, pattern)
    return sorted(u for u in urls if not SKIP.search(urlparse(u).path))


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'").replace("®", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _product(page: str) -> dict | None:
    for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            j = json.loads(m)
        except ValueError:
            continue
        for g in (j.get("@graph") or [j]):
            if isinstance(g, dict) and g.get("@type") == "Product":
                return g
    return None


def _flat(page: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript|nav|header|footer)[^>]*>.*?</\1>", "", page, flags=re.S)))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _pairs(pairs: list[tuple[str, str]]) -> str | None:
    out = [f"{'Aroma' if k.strip().lower() == 'arome' else k.strip().capitalize()}: {_sentence(v)}" for k, v in pairs if k and v and v.strip()]
    return " ".join(out)[:900] or None


JD_LABELS = ("aroma", "arome", "nose", "taste", "flavor", "finish")
JD_SENSORY = re.compile(r"\bnotes? of\b|\bnose\b|\bpalate\b|\baromas?\b|\bflavors? of\b|\btaste (?:rich|begins)\b", re.I)
JD_NOT_TASTE = re.compile(r"recipe|cocktail|proof will|available (?:only|in)|selected by|trademark|\bcookies?\b", re.I)


def _notes(host: str, page: str, flat: str) -> str | None:
    if host == "www.oldforester.com":
        icons = {"nose": "Aroma", "lips": "Taste", "glass": "Finish"}
        pairs = []
        for cls, head, body in re.findall(r'<h2 class="[^"]*tasting-note-title([^"]*)">(.*?)</h2>\s*<p>(.*?)</p>', page, re.S):
            icon = re.search(r"uses-icon-(\w+)", cls)
            label = _text(re.sub(r"<svg.*?</svg>", "", head, flags=re.S)) or icons.get(icon.group(1) if icon else "", "")
            pairs.append((label, _text(body) or ""))
        return _pairs(pairs)
    if host == "www.cooperscraft.com":
        m = re.search(r"FLAVOR PROFILE\|\s*THE NOSE:\|\s*(.*?)\|\s*THE TASTE:\|\s*(.*?)\|\s*THE FINISH:\|\s*(.*?)\|", flat)
        return _pairs(list(zip(("Nose", "Taste", "Finish"), m.groups()))) if m else None
    toks = [t.strip() for t in flat.split("|")]
    if host == "www.woodfordreserve.com":
        got: dict[str, str] = {}
        for i, t in enumerate(toks):
            m = re.match(r"(Aroma|Flavor|Nose|Taste|Finish):\s*(.+)$", t)
            if m:
                got.setdefault(m.group(1), m.group(2))
            elif t in ("Nose", "Taste", "Finish") and i + 1 < len(toks):
                got.setdefault(t, toks[i + 1])
        return _pairs(list(got.items()))
    # jackdaniels.com: an aroma / taste / finish strip, else the intro sentences that name notes, nose or palate
    low = [t.lower() for t in toks]
    for i, t in enumerate(low):
        if t in ("aroma", "arome", "nose") and i + 6 < len(toks) and low[i + 2] in ("taste", "flavor") and low[i + 4] == "finish":
            return _pairs([(toks[i], toks[i + 1]), (toks[i + 2], toks[i + 3]), (toks[i + 4], toks[i + 5])])
    intro = re.split(r"(?i)\|\s*you might also like|\|\s*targeting cookies|\|\s*explore ", flat)[0]
    sents = []
    for seg in intro.split("|"):
        for sent in re.split(r"(?<=[.!?])\s+", seg.strip()):
            sent = re.sub(r"^Offered at [^)]*\),\s*", "", sent.strip())  # the proof clause is not taste
            sent = _sentence(sent) if sent else ""
            core = re.sub(r"^notes? of ", "", sent.lower().rstrip("."))
            if sent and JD_SENSORY.search(sent) and not JD_NOT_TASTE.search(sent) and core not in " ".join(sents).lower():
                sents.append(sent)  # a bullet that repeats a sentence already kept is dropped
    return " ".join(sents)[:900] or None


def parse(url: str, page: str) -> BottlingRecord | None:
    host, path = urlparse(url).netloc, urlparse(url).path
    slug = path.rstrip("/").split("/")[-1]
    family = HOSTS[host][0]
    prod = _product(page)
    h1s = [_text(x) for x in re.findall(r"<h1[^>]*>(.*?)</h1>", page, re.S)]
    title = _text((re.search(r"<title>(.*?)</title>", page, re.S) or [None, ""])[1]) or ""
    name_raw = _text((prod or {}).get("name")) or (h1s[0] if h1s else None) or title.split("|")[0].split(" - ")[0].strip()
    if not name_raw:
        return None
    flat = _flat(page)
    description = _text((prod or {}).get("description")) or _text((re.search(r'name="description" content="([^"]+)"', page) or [None, ""])[1])

    # Proof: a "Proof | 90.4 °" note (Woodford), else the copy ("At 86 proof", "bottled at 104 proof"), else the name.
    pf = None
    m = re.search(r"\bProof\|\s*(\d{2,3}(?:\.\d+)?)\s*°?", flat)
    if m:
        pf = float(m.group(1))
    if pf is None:
        # Only the product's own copy: every JD page carries a "delivered at 100 proof" Bonded promo, and every
        # Old Forester page lists its "86 Proof" / "100 Proof" siblings by name.
        if host == "www.jackdaniels.com":
            own = ""
        elif host == "www.oldforester.com":
            i = page.find("<h1")
            own = re.split(r"You won.t find|finer family|Lorem ipsum|Learn more", _flat(page[i:i + 20000]))[0]
        else:
            own = flat[:20000]
        copy = " ".join(x for x in (name_raw, description, own) if x)
        copy = re.sub(r"enter(?:ing|ed|s)?\s+(?:the\s+)?(?:second(?:ary)?\s+)?barrel\s+at\s+(?:a\s+low\s+)?\d{2,3}(?:\.\d+)?\s*proof", " ", copy, flags=re.I)  # entry proof is not bottling proof
        if not re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}(?:\.\d+)?[- ]proof", copy, re.I):
            m = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b|\bproof (?:of |is )?(\d{2,3}(?:\.\d+)?)\b|bottled at (\d{2,3}(?:\.\d+)?)", copy, re.I)
            pf = float(next(g for g in m.groups() if g)) if m else None
    years, label = age(" ".join(x for x in (name_raw, description) if x))

    if slug == "masters-collection":  # the page is whichever edition is current; its h1 names it
        edition = next((h for h in h1s if h and "Responsibly" not in h), None)
        family, expression, aliases = "Woodford Reserve", f"Master's Collection: {edition}" if edition else "Master's Collection", []
    elif slug in REFILE:
        family, expression, aliases = REFILE[slug]
    elif BIRTHDAY.search(slug):
        family, expression, aliases = "Old Forester", "Birthday Bourbon", [name_raw]
        m = re.search(r"(\d{4})", slug)
        years, label = age(description or "")
    else:
        rest = name_raw.upper()
        for pre in (family.upper(), family.upper().replace("'", "'")):
            if rest.startswith(pre):
                rest = rest[len(pre):]
        rest = rest.strip(" -–—:,")
        rest = re.sub(r"^THE\s+", "", rest)
        rest = re.sub(r"\b(\d+)[- ]YEARS?[- ]OLD\b", r"\1 YEAR", rest)
        for _ in range(3):
            rest = re.sub(r"\s*\b(TENNESSEE WHISKEY|KENTUCKY STRAIGHT (BOURBON|RYE)( WHISK(E)?Y)?|BOURBON WHISK(E)?Y|STRAIGHT BOURBON|BOURBON|WHISKEY|WHISKY)$", "", rest).strip()
        expression = titlecase(rest) if rest else None
        aliases = [name_raw]
    name = family if expression is None else f"{family} {expression}"

    # Class from the label's own words, by family when the name doesn't say.
    if re.search(r"\brye\b", name, re.I) and "Bourbon x" not in name:
        class_raw = "Straight Rye Whiskey"
    elif re.search(r"malt", name, re.I):
        class_raw = "Kentucky Straight Malt Whiskey"
    elif re.search(r"wheat whiskey", name, re.I):
        class_raw = "Kentucky Straight Wheat Whiskey"
    elif family == "Jack Daniel's":
        class_raw = "Blended Straight Whiskey" if "Triple Mash" in name else "Tennessee Whiskey"
    else:
        class_raw = "Kentucky Straight Bourbon Whisky"
    if re.search(r"bottled[- ]in[- ]bond|\bbonded\b", name_raw + " " + (description or ""), re.I):
        class_raw += " Bottled-in-Bond"

    # Image: JSON-LD (JD), else the summary block's full-size upload (Woodford), else og:image.
    img = (prod or {}).get("image")
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, dict):
        img = img.get("url")
    if not img and host == "www.woodfordreserve.com":
        i = page.find("c-product-summary")
        for src in re.findall(r'<img[^>]+src="([^"]+wp-content/uploads/[^"]+)"', page[max(0, i - 6000):i + 2000]):
            if not re.search(r"-\d+x\d+\.(png|jpg|webp)", src):
                img = src
                break
    if not img and host == "www.cooperscraft.com":
        img = next((src for src in re.findall(r'<img[^>]+src="([^"]+wp-content/uploads/[^"]+)"', page) if "bottle" in src.lower()), None)
    if not img:
        m = re.search(r'property="og:image" content="([^"]+)"', page)
        img = m.group(1) if m else None
    if img and re.search(r"logo|holiday|derby", img, re.I):
        img = None  # an og:image fallback that is the distillery's mark, not a bottle
    mash = "rye" if class_raw.startswith("Straight Rye") else None  # none of these pages states a recipe
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=description, tasting_notes=_notes(host, page, flat), image_url=img,
        aliases=sorted({*aliases} - {name}), is_core_range=not NOT_CORE.search(name),
    )
