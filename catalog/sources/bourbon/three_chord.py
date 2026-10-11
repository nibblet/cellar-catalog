"""threechordbourbon.com (Three Chord Bourbon, Inc., Clarence NY; Neil Giraldo's brand, blended by Ari Sussman and
"Co-Packed at the Ugly Dog Distillery", Chelsea MI — the catalog's producer stays "Three Chord"). WordPress (Yoast
sitemap, BeTheme) with WooCommerce; robots.txt is Yoast's allow-all with no Crawl-delay, so DELAY is the project's usual
6. Every page carries a "Are You Of Drinking Age?" overlay in its static HTML; the page copy is served regardless and
nothing here clicks through it (Journeyman / Hard Truth precedent). The bottle shop, store.threechordbourbon.com, 307s
every page to /age-verification: it is NOT read (its sitemap.xml was read for slugs only, to learn that Backstage Series
pages exist for Underoath, Allman Brothers, Casualties, Dayseeker, JM, Anthrax and Conway Machine; none of those pages
can be read, so those bottlings state no proof here and stay seeds or are not added).

What is imported:
- /our-whiskey/ — the five standing bottles. Each is a carousel slide: a bottle photo whose file name is the bottle
  ("strangecolab.webp", "riot.webp", "flipside.webp", "hardpressed.webp", "Un-edited.jpg": page markup, not OCR), and a
  "More Info" toggle reading "alc/vol 43% | 750ML | 86 PROOF" + a one-line class ("Kentucky straight bourbon whiskey
  finished in Pinot Noir barrels."). The name is confirmed by the cocktail pages (flipside-flipside-old-fashioned,
  hard-pressed-hard-pressed-memphis-julep, riot-basement-sazerac, un-edited-un-edited-boulevardier,
  strange-collab-strange-sour-pinot-float) and by the Cordell Jackson copy on Hard Pressed.
- /our-whiskey/amplify-rye-whiskey/ — Amplify Rye ("95 proof", "MASH BILL: 95% Rye / 5% Malted Barley", "$56.92 MSRP"). The
  page's post category says "Blended Bourbon Whiskey" but the whiskey is a blend of Kentucky and Indiana rye (95% rye
  mash bill): class_raw says Rye Whiskey (a blend of the same whiskey is that whiskey). It is not on the /our-whiskey/
  carousel any more; it is kept core because the seed is core and the page is live with a Buy Now.
- /backstage-series/ — the Backstage Series (limited artist collaborations, 2023). Each tile is a flip-box: front bottle
  photo, back blurb ("Blend of 8 Year Old Kentucky Corn Whiskey and 2 Year Old Kentucky Bourbon finished in Toasted
  Barrels"), then `<h6>Name</h6><h6>PROOF 98</h6>`. Seven tiles are listed: The Cadillac Three 90, Goodbye June 120,
  Halestorm 90, Lucero 98, Black Stone Cherry 98, Dinosaur Jr. 96.6, Theory of a Deadman 93.4. The per-artist pages
  (/our-whiskey/halestorm/ etc.) are empty templates ("mL | % ABV | proof") except Dinosaur Jr., whose 96.6 agrees with the
  index; they are cached as evidence and not parsed. The blurbs state component ages (6 / 2.5 / 8 year), which are not the
  bottle's age: no age is read for any of them.

Judgments carried here so a re-run reproduces them:
- Class. Halestorm, Black Stone Cherry and Dinosaur Jr. blend straight bourbons WITH corn whiskey, a cross-type blend: class
  is "Blend of Bourbon and Corn Whiskey", so spirit_type reads 'blend' (the seeds say bourbon; owner may reverse). Goodbye
  June and Theory of a Deadman blend only bourbons (class Bourbon Whiskey); Lucero blends Tennessee whiskeys (Tennessee
  Whiskey); The Cadillac Three's blurb says only "whiskey" (class Whiskey -> 'other'). Un-Edited is "Blend of straight
  bourbon whiskeys", which is a bourbon (High West lesson); RIOT is a double-bonded blend of straight ryes, a rye.
- Strange Collab. The maker's only Strange Collab is the 86-proof Pinot Noir finished Kentucky bourbon, so it claims the seed
  'Strange Collab Pinot Noir Finished' (99 proof, which the page contradicts) by that seed's name. The catalog also holds a
  second 99-proof seed, 'Strange Collaboration' (visible, core, age 5.5 labelled NAS): nothing on the page ties it to this
  bottle, so it is NOT claimed or merged; it is an owner item.
- Flipside and Hard Pressed answer to the seeds 'Flipside Triplewood' and 'Hard Pressed Tennessee' (proofs agree); the
  maker's names are the short ones, the seeds' stay as aliases.
- A page that states no proof cannot create or confirm a row: Atreyu, Fu Manchu, Michael Ray, Taking Back Sunday, Allman
  Brothers Band and Underoath (no readable page), Twelve Bar Reserve Barrel Proof, Whiskey Drummer, Honey Toasted and the
  Amburana / Cherry Bounce rye are not on the site. They stay seeds."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Three Chord"
DELAY = 6
SITEMAP = "https://threechordbourbon.com/sitemap_index.xml"
IMAGE_PREFIX = "https://threechordbourbon.com/"
CATALOG_FAMILIES = ["Three Chord"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Three Chord"
BASE = "https://threechordbourbon.com"
OUR = BASE + "/our-whiskey/"
BACKSTAGE = BASE + "/backstage-series/"
AMPLIFY = BASE + "/our-whiskey/amplify-rye-whiskey/"
# Evidence pages (cached, never parsed): the per-artist pages are empty templates but Dinosaur Jr.
EVIDENCE = [BASE + "/our-whiskey/dinosaur-jr/", BASE + "/our-whiskey/halestorm/"]

# bottle-photo file stem on /our-whiskey/ -> (expression, [catalog names it answers to], class statement, finish)
LINEUP = {
    "strangecolab": ("Strange Collab", ["Three Chord Strange Collab Pinot Noir Finished"], "Kentucky Straight Bourbon Whiskey", "Pinot Noir Barrels"),
    "riot": ("RIOT Double Bonded Rye", [], "Straight Rye Whiskey", None),
    "flipside": ("Flipside", ["Three Chord Flipside Triplewood"], "Kentucky Straight Bourbon Whiskey", "Toasted French & American Oak"),
    "hardpressed": ("Hard Pressed", ["Three Chord Hard Pressed Tennessee"], "Tennessee Straight Bourbon Whiskey", None),
    "un-edited": ("Un-Edited", [], "Straight Bourbon Whiskey", None),
}
# Backstage tile name -> (class statement, finish)
BACKSTAGE_CLASS = {
    "The Cadillac Three": ("Whiskey", None),
    "Goodbye June": ("Bourbon Whiskey", "Cherry Bounce Barrels"),
    "Halestorm": ("Blend of Bourbon and Corn Whiskey", "Toasted Barrels"),
    "Lucero": ("Tennessee Whiskey", None),
    "Black Stone Cherry": ("Blend of Bourbon and Corn Whiskey", "Toasted Barrels"),
    "Dinosaur Jr.": ("Blend of Bourbon and Corn Whiskey", "Toasted Barrels"),
    "Theory of a Deadman": ("Bourbon Whiskey", None),
}
CORE = {"Strange Collab", "RIOT Double Bonded Rye", "Flipside", "Hard Pressed", "Un-Edited", "Amplify Rye"}
RARITY = [(r"backstage", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [OUR, AMPLIFY, BACKSTAGE, *EVIDENCE]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("’", "'").replace("\xa0", " ")).strip()


def _abs(src: str) -> str:
    src = html.unescape(src).split("#")[0]
    return src if src.startswith("http") else BASE + src


def _our_whiskey(url: str, page: str) -> list[BottlingRecord]:
    out = []
    for m in re.finditer(r'<div class="swiper-slide">(.*?)(?=<div class="swiper-slide">|$)', page, re.S):
        slide = m.group(1)
        img = re.search(r'data-src="([^"]*/wp-content/uploads/([^"/#]+?)\.(?:webp|jpg|png))(?:#\d+)?"', slide)
        pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*PROOF", slide)
        if not img or not pm:
            continue
        stem = img.group(2).lower()
        if stem not in LINEUP:
            continue
        expression, aliases, class_raw, finish = LINEUP[stem]
        name = f"{FAMILY} {expression}"
        out.append(BottlingRecord(
            brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=float(pm.group(1)),
            class_raw=class_raw, finish=finish, image_url=_abs(img.group(1)),
            aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE))
    return out


def _backstage(url: str, page: str) -> list[BottlingRecord]:
    out = []
    for m in re.finditer(r'<div class="flip-box-front">(.*?)</div>\s*<div class="flip-box-back">(.*?)</div></div></div>\s*<h6[^>]*>([^<]+)</h6>\s*<h6[^>]*>\s*PROOF\s*(\d{2,3}(?:\.\d+)?)\s*</h6>', page, re.S):
        front, back, artist, proof = m.groups()
        artist = _clean(artist)
        if artist not in BACKSTAGE_CLASS:
            continue
        class_raw, finish = BACKSTAGE_CLASS[artist]
        img = re.search(r'src="([^"]+)"', front)
        expression = f"Backstage Series: {artist}"
        out.append(BottlingRecord(
            brand_family=FAMILY, expression=expression, name=f"{FAMILY} {expression}", source_url=url, proof=float(proof),
            class_raw=class_raw, finish=finish, image_url=_abs(img.group(1)) if img else None,
            description=_clean(back), is_core_range=False))
    return out


def _amplify(url: str, page: str) -> BottlingRecord | None:
    text = _clean(re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", "", page, flags=re.S))
    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof\b", text, re.I)
    mm = re.search(r"MASH BILL:\s*([^|]*?)\s*(?:APPEARANCE|AROMA)", text)
    sm = re.search(r"\$\s*(\d+(?:\.\d{2})?)\s*MSRP", text)
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    mash = re.sub(r"\s*/\s*", ", ", mm.group(1)).strip(" ,") if mm else None
    return BottlingRecord(
        brand_family=FAMILY, expression="Amplify Rye", name=f"{FAMILY} Amplify Rye", source_url=url,
        proof=float(pm.group(1)) if pm else None, class_raw="Rye Whiskey", mash_raw=mash,
        msrp_usd=float(sm.group(1)) if sm else None, image_url=html.unescape(og.group(1)) if og else None,
        is_core_range=True)


def parse(url: str, page: str):
    if url == OUR:
        return _our_whiskey(url, page)
    if url == BACKSTAGE:
        return _backstage(url, page)
    if url == AMPLIFY:
        return _amplify(url, page)
    return None
