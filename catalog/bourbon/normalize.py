"""Label text → the catalog's typed bourbon columns. Deterministic; unknown stays unknown."""
from __future__ import annotations

import re

from ..normalize import key  # the same comparison key the cigar side uses


def proof(text: str | None) -> float | None:
    """'90 (45%)' → 90; '45% ABV' → 90; '134.4 proof' → 134.4."""
    if not text:
        return None
    t = text.replace(",", ".")
    if re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}(?:\.\d+)?", t):
        return None  # "107–114": a range is not a statement
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:proof|°|\(|$)", t, re.I)
    if m and 40 <= float(m.group(1)) <= 200:
        return float(m.group(1))
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*%", t)
    if m:
        return round(float(m.group(1)) * 2, 1)
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?)\b", t)
    return float(m.group(1)) if m and 40 <= float(m.group(1)) <= 200 else None


_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "fifteen": 15, "eighteen": 18, "twenty": 20, "decade": 10,
          "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "twelfth": 12}


def age(text: str | None) -> tuple[float | None, str | None]:
    """'Aged 10 Years' / '12-year-old' / 'at least 4 years' / 'a full decade' → (years, '10 yr').
    Returns (None, None) when the text states no age; 'NAS' is the caller's word, never inferred."""
    if not text:
        return None, None
    t = text.lower()
    rng = re.search(r"(?:aged|matured)\s+(?:for\s+)?(?:between\s+)?(\d{1,2})\s*(?:-|–|to|and)\s*(\d{1,2})[- ]years?", t) \
        or re.search(r"\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*years?\b", t)
    if rng:  # "Aged between 10 and 12 years" / a bare "4 - 6 Years Old" is a display label, not a number
        return None, f"{rng.group(1)}–{rng.group(2)} yr"
    m = re.search(r"(?:(?:aged|matured|rests?|rested)\s+(?:for\s+)?(?:at least\s+|a minimum of\s+|over\s+)?|minimum\s+(?:of\s+)?)(\d{1,2}(?:\.\d)?|[a-z]+)\s*[- ]?years?", t) \
        or re.search(r"\b(\d{1,2}(?:\.\d)?|[a-z]+)[- ]year[- ]old\b", t) \
        or re.search(r"\b(\d{1,2})\s*yrs?\b", t) \
        or re.search(r"\b(\d{1,2}(?:\.\d)?)\s+years?\s+(?:old|of age|in (?:the )?barrel)", t) \
        or re.search(r"\ba full (decade)\b", t) \
        or re.search(r"\bits (fourth|fifth|sixth|seventh|eighth|ninth|tenth|twelfth) year\b", t) \
        or re.search(r"\b(\d{1,2})[- ]years?\b(?![- ]old bottle)", t)
    if not m:
        return None, None
    raw = m.group(1)
    years = float(raw) if raw[0].isdigit() else _WORDS.get(raw)
    if not years or years > 50:
        return None, None
    label = f"{int(years) if years == int(years) else years} yr"
    return years, label


def spirit_type(class_raw: str | None, name: str = "") -> str | None:
    """The label's class statement → cellar.spirit_type. None when it is not whiskey at all."""
    t = f"{class_raw or ''} {name}".lower()
    # "bourbon" in the *label class* rules out rye/blend; a maker's own name containing "Bourbon"
    # (The Bardstown Bourbon Company) must not (a Bardstown Bourbon Company rye is still a rye).
    class_says_bourbon = "bourbon" in (class_raw or "").lower()
    # The label's own class says what's in the bottle; a cask that once held rum, tequila or brandy
    # is a finish mentioned in the marketing name, not what's in this bottle (Widow Jane's "Tequila
    # Ocho Cask Finish" bourbon, a hypothetical "Rum Cask Finish" rye).
    if re.search(r"vodka|\bgin\b|liqueur|\bcream\b|soda|tequila|\brum\b|brandy|\bbeer\b", (class_raw or "").lower()):
        return None
    if re.search(r"\bblend", class_raw or "", re.I) and not re.search(r"blended (?:straight )?bourbon", class_raw or "", re.I):
        return "blend"  # the label calls it a blend, whatever it was blended from
    if re.search(r"single malt", t):
        return "american_single_malt"
    if re.search(r"tennessee whisk", t):
        return "tennessee"
    if re.search(r"\bwheat whisk", t):
        return "wheat_whiskey"
    if re.search(r"\brye whisk|\brye\b(?! recipe| mash| bourbon)", t) and not class_says_bourbon:
        return "rye"
    if re.search(r"blend|blended", t) and not class_says_bourbon:
        return "blend"
    if class_says_bourbon or "bourbon" in t:
        return "bourbon"
    if re.search(r"whisk|sour mash|corn", t):
        return "other"
    return None


def mash_bill(text: str | None) -> str | None:
    """A recipe stated as percentages, cleaned; anything else is not a mash bill."""
    if not text or not re.search(r"\d{1,3}\s*%", text):
        return None
    return re.sub(r"\s+", " ", text).strip()


def mash_style(mash_raw: str | None, spirit: str | None, name: str = "") -> str | None:
    """Recipe → family. Only from what the maker states: percentages, or the words wheat / four grain / rye."""
    t = f"{mash_raw or ''} {name}".lower()
    if spirit == "rye":
        return "rye"
    if re.search(r"four[- ]grain", t):
        return "four_grain"
    # "21% rye" and "rye: 21%" both state the same figure; a maker's own label reads either way.
    rye = re.search(r"(\d{1,2})\s*%\s*(?:winter\s+)?rye", t) or re.search(r"rye:?\s*(\d{1,2})\s*%", t)
    if re.search(r"wheat", t) and not rye:
        return "wheated"
    if rye:
        return "high_rye" if int(rye.group(1)) >= 20 else "traditional"
    if re.search(r"high[- ]rye", t):
        return "high_rye"
    if re.search(r"\d{1,2}\s*%\s*corn", t) or re.search(r"corn:?\s*(\d{1,2})\s*%", t):
        return "traditional"
    return None


def expression_type(name: str, single_barrel_default: bool = False) -> str:
    n = name.lower()
    if re.search(r"single[- ]barrel|single[- ]cask", n) or single_barrel_default:
        return "single_barrel"
    if re.search(r"small[- ]batch", n):
        return "small_batch"
    if re.search(r"store pick|private (?:select|barrel)|hand[- ]select", n):
        return "store_pick"
    if re.search(r"limited|anniversary|antique collection|special release|commemorative", n):
        return "limited"
    return "standard"


def flags(name: str, class_raw: str | None, proof_value: float | None) -> tuple[bool, bool]:
    """→ (bottled_in_bond, barrel_proof), from the label and the 115-proof floor the app uses."""
    t = f"{name} {class_raw or ''}".lower()
    bib = bool(re.search(r"bottled[- ]in[- ]bond|\bbonded\b|\bbib\b", t))
    bp = bool(re.search(r"barrel[- ]proof|cask[- ]strength|full[- ]proof|uncut|straight from the barrel|barrel[- ]strength", t)) or (proof_value or 0) >= 115
    return bib, bp


def finish(name: str, description: str | None = None) -> str | None:
    """'Finished in Port Casks' / 'Toasted Barrel Finish' / 'Double Oaked' as marketed; None when not a finished whiskey."""
    for t in (name, description or ""):
        # "Cask Finish Series" as a product LINE's own name is not "finished in a cask" (Barrell's landing
        # page for six different one-off casks); a real single bottling never calls its finish a "series".
        m = re.search(r"finished in ([\w' ]+?(?:cask|barrel)s?)", t, re.I) \
            or re.search(r"([\w' ]+?(?:cask|barrel|oak)) finish(?:ed)?\b(?!\s*series)", t, re.I)
        if m:
            return m.group(1).strip().title()
        if re.search(r"double oaked", t, re.I):
            return "Double Oaked"
        if re.search(r"toasted barrel", t, re.I):
            return "Toasted Barrel"
    return None


SMALL = {"of", "the", "and", "in", "a", "de", "du", "for", "at", "by", "x"}
KEEP = {"OFC": "O.F.C.", "CYPB": "C.Y.P.B.", "EH": "E.H.", "JR": "Jr.", "WL": "W.L.", "US": "US", "XO": "XO", "II": "II", "III": "III", "IV": "IV", "XA": "XA"}


def titlecase(text: str) -> str:
    """Label capitals → the bar-order name: 'E.H. TAYLOR, JR. SMALL BATCH' → 'E.H. Taylor, Jr. Small Batch'."""
    out = []
    for i, w in enumerate(text.split()):
        core = re.sub(r"[^A-Za-z]", "", w)
        if core.upper() in KEEP and (core.upper() == core or "." in w):
            out.append(re.sub(re.escape(core), KEEP[core.upper()], w, flags=re.I) if "." not in KEEP[core.upper()] or "." not in w else w.upper().replace("JR", "Jr"))
            continue
        lw = w.lower()
        if i and lw in SMALL:
            out.append(lw)
            continue
        # Keep dotted initials ("E.H.") and mixed tokens ("No.", "#1") sane; capitalise after an apostrophe only for O'.
        if re.fullmatch(r"(?:[A-Za-z]\.)+,?", w):  # "E.H." / "W.L." — initials
            out.append(w.upper())
        else:
            out.append(lw[:1].upper() + lw[1:])
    s = " ".join(out)
    s = re.sub(r"(\w)'S\b", r"\1's", s)
    s = re.sub(r"\bMc(\w)", lambda m: "Mc" + m.group(1).upper(), s)
    return s


def expression_tokens(text: str | None) -> set[str]:
    """The words of an expression, boilerplate dropped, each as a comparison key."""
    t = (text or "").lower()
    t = re.sub(r"\baged\s+(?:for\s+)?(?:at least\s+)?(\d+)\s*[- ]?years?(?:\s+old)?", r"\1 year", t)
    t = re.sub(r"\b(\d+)[- ]?(?:years?|yrs?|yo)(?:[- ]old)?\b", r"\1 year", t)
    t = re.sub(r"\b(kentucky|straight|bourbon|whiskey|whisky|tennessee|the|brand|edition|old)\b", " ", t)
    return {key(w) for w in t.split() if key(w)}


def expression_key(text: str | None) -> str:
    """Comparison key for an expression: the age said the same way, label boilerplate dropped."""
    t = (text or "").lower()
    t = re.sub(r"\baged\s+(?:for\s+)?(?:at least\s+)?(\d+)\s*[- ]?years?(?:\s+old)?", r"\1 year", t)
    t = re.sub(r"\b(\d+)[- ]?(?:years?|yrs?|yo)(?:[- ]old)?\b", r"\1 year", t)
    t = re.sub(r"\b(kentucky|straight|bourbon|whiskey|whisky|tennessee|the|brand|edition|old)\b", " ", t)
    return "".join(sorted(key(w) for w in t.split() if key(w)))  # "18 Year Rye" ~ "Rye 18 Year"
