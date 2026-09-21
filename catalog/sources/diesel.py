"""Diesel on cigarworld.com (General Cigar). AJ Fernandez's brand, rolled at Tabacalera AJ Fernandez
in Estelí; a few pages say so outright, the rest get the curated map below."""
import re

from . import cigarworld as base

BRANDS = ["diesel"]
COUNTRY = None
DELAY, SITEMAP, IMAGE_PREFIX = base.DELAY, base.SITEMAP, base.IMAGE_PREFIX

# The site files some releases as their own lines; the catalog files them as sizes of the line the
# band says: page line → (line, size name). Fool's Errand is a trilogy of one-size blends,
# Founder's Collection an annual one-size release named for a horse.
RELEASES = {
    "Fool's Errand - Simple Fool": ("Fool's Errand", "Simple Fool"),
    "Fool's Errand - Stubborn Fool": ("Fool's Errand", "Stubborn Fool"),
    "Fool's Errand - Worthy Fool": ("Fool's Errand", "Worthy Fool"),
    "Backyard Barbecue Series - Pulled Pork": ("Backyard BBQ Series", "Pulled Pork"),
    "Backyard BBQ Series Burnt Ends": ("Backyard BBQ Series", "Burnt Ends"),
    "Sunday Gravy Porcellino": ("Sunday Gravy", "Porcellino"),
    "Sunday Gravy Rosamarino": ("Sunday Gravy", "Rosamarino"),
    "Whiskey Row Founder's Collection Mizunara": ("Whiskey Row Founder's Collection", "Mizunara"),
    "Whiskey Row Founder's Collection Nevallier": ("Whiskey Row Founder's Collection", "Nevallier"),
    "Whiskey Row Founder's Collection Raceking": ("Whiskey Row Founder's Collection", "Raceking"),
}
LINE_NAMES = {"GRIND": "Grind", "Diesel": None, "d. 10th": "d.10th"}  # the site shouts; the flagship page is just "Diesel"


def list_urls(fetcher):
    return base.list_urls(fetcher, BRANDS)


def parse(url, page):
    rec = base.parse(url, page, COUNTRY_BY_LINE)
    if rec is None:
        return None
    if rec.line in RELEASES:
        rec.line, name = RELEASES[rec.line]
        if len(rec.vitolas) == 1:
            rec.vitolas[0].name = name
    elif rec.line in LINE_NAMES:
        rec.line = LINE_NAMES[rec.line]
    # Unlimited lists "Robusto" twice (5.5 x 54 and 4.7 x 52); the site calls the 4.5 x 52 d.10th a
    # Short Robusto, so the shorter of a same-named pair takes that name here too
    for v in rec.vitolas:
        twins = [w for w in rec.vitolas if w.name == v.name and w is not v]
        if twins and v.length_in and all(v.length_in < w.length_in for w in twins if w.length_in):
            v.name = "Short " + v.name
    if rec.country is None:
        rec.country = COUNTRY_BY_LINE.get(rec.line)
    return rec


# CURATED, not maker text: every Diesel is rolled at Tabacalera AJ Fernandez in Estelí (the Sunday
# Gravy pages say so; the others name AJ Fernandez as the blender and nothing else).
COUNTRY_BY_LINE = {l: "Nicaragua" for l in (
    None, "Backyard BBQ Series", "Crucible", "d.10th", "Delirium", "Disciple", "Estelí Puro", "Fool's Errand", "Grind",
    "Hair of the Dog", "Rage", "Sunday Gravy", "Uncaged", "Unlimited", "Unlimited Maduro", "Vintage Series",
    "Vintage Series Natural", "Whiskey Row", "Whiskey Row Founder's Collection", "Whiskey Row Sherry Cask", "Wicked")}

# Catalog rows re-filed by hand.
OVERRIDES = {
    "35cab358-ed38-4919-bfd3-565d44b7c260": {"expression": "Toro Box Pressed"},   # Hair of the Dog's one size
    "1ed9cb5a-fe8d-4d8f-8bf9-5ba615cefdd3": {"expression": "Torpedo"},            # Wicked 6.2 x 56 is the Torpedo, not a Robusto
    # left alone: Estelita, Uncut d.CT, Unholy Cocktail, Rage Robusto — not on the site
}
