"""Free text → the catalog's enums. Deterministic; anything unrecognised stays `unknown`, never a guess."""
from __future__ import annotations

import re
import unicodedata

# Leaf variety first, growing region last: "Connecticut River Valley Habano" is a Habano grown in Connecticut.
LEAF_PATTERNS = [
    ("connecticut_broadleaf", r"broadleaf"),
    ("san_andres", r"san andr[eé]s|mexic"),
    ("brazilian", r"mata fina|arapiraca|brazil"),
    ("cameroon", r"cameroon"),
    ("sumatra", r"sumatra"),
    ("corojo", r"corojo"),
    ("criollo", r"criollo"),
    ("candela", r"candela"),
    ("habano", r"habano|havana"),
    ("connecticut_shade", r"connecticut|shade"),
]

ORIGIN_PATTERNS = [
    ("Mexico", r"mexic|san andr"),
    ("Ecuador", r"ecuador"),
    ("Nicaragua", r"nicarag|estel[ií]|jalapa"),
    ("Honduras", r"hondur"),
    ("Dominican Republic", r"dominican"),
    ("Brazil", r"brazil|mata fina"),
    ("Cameroon", r"cameroon"),
    ("Indonesia", r"indonesia|sumatra"),
    ("United States", r"connecticut river valley|pennsylvania|united states|u\.s\.a|american|usa\b"),
]

SHADE_PATTERNS = [
    ("oscuro", r"oscuro|negro"),
    ("maduro", r"maduro"),
    ("claro", r"shade|claro|candela"),
    ("colorado", r"colorado|rosado|sun[- ]?grown|habano|corojo|sumatra|cameroon"),
]


def _first(patterns, text):
    t = text.lower()
    for value, pat in patterns:
        if re.search(pat, t):
            return value
    return None


def wrapper(raw: str | None) -> tuple[str, str | None, str | None]:
    """→ (wrapper_leaf, wrapper_origin, wrapper_shade)."""
    if not raw:
        return "unknown", None, None
    leaf = _first(LEAF_PATTERNS, raw) or "unknown"  # an origin or a shade alone does not name a leaf
    origin = _first(ORIGIN_PATTERNS, raw)  # "Connecticut" alone names the seed, not where it grew
    shade = _first(SHADE_PATTERNS, raw)
    return leaf, origin, shade


STRENGTH = {
    "mild": "mild", "mild-medium": "mild_medium", "mild to medium": "mild_medium", "medium": "medium",
    "medium-full": "medium_full", "medium to full": "medium_full", "medium-plus": "medium_full", "full": "full",
}


def strength(raw: str | None) -> str | None:
    if not raw:
        return None
    return STRENGTH.get(re.sub(r"\s*[-–]\s*", "-", raw.strip().lower()))


def shape(size_name: str) -> tuple[str, bool]:
    """→ (shape, box_pressed) from a marketed size name."""
    n = size_name.lower()
    box = bool(re.search(r"box[- ]?press|\bbp\b|\d{3}\s?bpt\b", n))
    if re.search(r"torpedo|pyramid|pir[aá]mide|\d{3}\s?(?:bp)?t\b", n):  # Nub's "464T" / "466BPT"
        return "torpedo", box
    if "belicoso" in n:
        return "belicoso", box
    if re.search(r"perfecto|pig|salom[oó]n|diadema", n):
        return "perfecto", box
    if re.search(r"figurado|culebra", n):
        return "figurado", box
    return "parejo", box


def dimensions(text: str) -> tuple[float | None, int | None]:
    """'5 x 43', '5 1/2 x 52', '6.125 x 52', '4 ¼ x 60' → (length, ring)."""
    t = text.replace("¼", " 1/4").replace("½", " 1/2").replace("¾", " 3/4").replace("⅛", " 1/8").replace("⅝", " 5/8").replace("⅜", " 3/8").replace("⅞", " 7/8")
    m = re.search(r"(\d+(?:\.\d+)?)(?:\s+(\d{1,2})/(\d{1,2}))?\s*(?:\"|”|in\.?|inch(?:es)?)?\s*[x×]\s*(\d{2,3})", t, re.I)
    if not m:
        return None, None
    length = float(m.group(1))
    if m.group(2):
        length += int(m.group(2)) / int(m.group(3))
    return round(length, 3), int(m.group(4))


def clean_value(text: str | None) -> str | None:
    """Placeholders a maker prints instead of a fact."""
    if not text or re.search(r"varies|undisclosed|n/a|see individual", text, re.I):
        return None
    return text


def size_name(text: str) -> str:
    """Marketed size name without a quoted aside: Flying Pig "Seasonal Release" → Flying Pig."""
    return re.sub(r"\s*[\"“”(].*$", "", text).strip()


def key(text: str | None) -> str:
    """Comparison key: lowercase alphanumerics only, minus any quoted or bracketed aside ("Seasonal Release")."""
    t = re.sub(r"[\"“”(].*$", "", text or "")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()  # Pilón → Pilon
    return re.sub(r"[^a-z0-9]", "", t.lower().replace("&", "and"))
