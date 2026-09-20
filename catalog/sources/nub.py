"""nubcigar.com — Wix, one page per line (Cain now lives here too, in Nub sizes; caincigar.com is
parked). The page text gives WRAPPER ~ / BINDER ~ / FILLER ~ by origin and a description; the
sizes are published only as a PNG line-up with the dimensions printed under each cigar, so they
are transcribed here from those images, each cited by its media id. Page titles, not slugs, name
the lines: the slugs are Wix "copy-of-" leftovers that don't match."""
from __future__ import annotations

import html
import re

from ..model import LineRecord, Vitola

BRAND = "Nub"
COUNTRY = None  # the site never says where they are rolled
DELAY = 5
SITEMAP = "https://www.nubcigar.com/pages-sitemap.xml"
IMAGE_PREFIX = "https://static.wixstatic.com/"
MEDIA = "https://static.wixstatic.com/media/"

LEAF_WORDS = r"san andr[eé]s|broadleaf|connecticut|cameroon|sumatra|habano|corojo|criollo|candela|maduro|sun[- ]?grown"

# Transcribed from the size line-up image on each page (media id → sizes as Nub prints them).
# Nub names a size by its dimensions: 3.75 x 58 is the "358", 4 x 64 torpedo the "464T".
SIZES = {
    "Habano":              ("da1e21_5dcb5a3f9b1f4658b716236fcf7bc844~mv2.png", ["3.75 x 58", "4 x 60", "4 x 64 T", "4 x 66"]),
    "México":              ("da1e21_9b3216cec6714d6392fd3f184fe4826c~mv2.png", ["4 x 60", "4 x 64 T"]),
    "Maduro":              ("da1e21_cdd2fdd1e80345d7aa752110c6baf749~mv2.png", ["4 x 60", "4 x 64 T"]),
    "Connecticut":         ("da1e21_d45b4090321449ce8c1790a91fb035de~mv2.png", ["3.75 x 54", "3.75 x 58", "4 x 60", "4 x 64 T"]),
    "Cameroon":            ("da1e21_959476b8d9974aabb65c09817bbbf844~mv2.png", ["3.75 x 58", "4 x 60", "4 x 64 T", "4 x 66 BPT"]),
    "Cain Habano":         ("da1e21_edcbc15c24c44227bbd53fa2e4385b64~mv2.png", ["4 x 60"]),
    "Cain Maduro":         ("da1e21_807945a92768496a80127e3f3778041d~mv2.png", ["4 x 60"]),
    "Cain F":              ("da1e21_269ad960d7f344ffb8a2e4b4d4a69a6b~mv2.png", ["4 x 60"]),
    "Nuance Single Roast": ("da1e21_b3fdbd21de6c460688fd94968d51626d~mv2.png", ["4 x 38", "4 x 60", "3.75 x 54"]),
    "Nuance Double Roast": ("da1e21_3834793f7ce840869d8c5c642702eccb~mv2.png", ["4 x 38", "4 x 60", "3.75 x 54"]),
    "Nuance Triple Roast": ("da1e21_6e6c97a291304fae824070211af66b43~mv2.png", ["4 x 38", "4 x 60", "3.75 x 54"]),
}


# Nub Cafe was renamed Nub Nuance: Cappuccino became Single Roast, Espresso became Double Roast.
OVERRIDES = {
    "19589fc8-133f-4bd2-a0e3-94415c36d66d": {"line": "Nuance Single Roast"},
    "31777587-661b-43c1-9e14-27634a91c90b": {"line": "Nuance Double Roast"},
}


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    return sorted(u for u in set(re.findall(r"<loc>(https://www\.nubcigar\.com/[^<]*nub-[^<]+)</loc>", xml)))


def _size(printed: str) -> Vitola:
    m = re.match(r"(\d+(?:\.\d+)?) x (\d+)\s*([A-Z]*)", printed)
    length, ring, suffix = float(m.group(1)), int(m.group(2)), m.group(3)
    # "3.75 x 58" → "358", "4 x 64 T" → "464T": Nub's own shorthand
    return Vitola(name=f"{int(length) if length.is_integer() else str(length).replace('.', '')[:1]}{ring}{suffix}", length_in=length, ring_gauge=ring)


def parse(url: str, page: str) -> LineRecord | None:
    title = re.search(r"<title>Nub (.*?) \|", page)
    if not title:
        return None
    line = html.unescape(title.group(1)).strip()
    if line not in SIZES:
        return None
    text = html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S))
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "\n", text)).replace("​", "")
    stats = re.search(r"WRAPPER ~ ([A-Za-z ]+?) BINDER ~ ([A-Za-z ]+?) FILLER ~ ([A-Za-z ]+?) Buy", text)
    origin = binder = filler = None
    if stats:
        origin, binder, filler = (s.strip() for s in stats.groups())
    desc = re.search(r"Careers (.*?) WRAPPER ~", text)
    desc = desc.group(1) if desc else ""
    words = [w for w in re.findall(LEAF_WORDS, desc, re.I) if re.search(rf"\b{re.escape(w)}\b[^.]{{0,40}}wrapp|wrapp[^.]{{0,60}}\b{re.escape(w)}\b", desc, re.I)]
    words += re.findall(LEAF_WORDS, line, re.I)
    hint = " ".join(dict.fromkeys(w.lower() for w in words))
    strength = re.search(r"\b(mild to medium|medium to full|mild|medium|full)[- ]bod", desc, re.I)
    media, printed = SIZES[line]
    return LineRecord(
        brand=BRAND, line=line, source_url=url,
        wrapper_raw=" ".join(x for x in (origin, hint) if x) or None, binder=binder, filler=filler,
        body=strength.group(1).title() if strength else None,
        band_image_url=MEDIA + media, vitolas=[_size(p) for p in printed],
    )
