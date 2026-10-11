"""pursuitspirits.com (Pursuit Spirits, Louisville — pursuitunited.com 301s here). WordPress + Elementor; robots.txt is
Yoast's allow-all with no Crawl-delay, so DELAY is the project's usual 6. One static page per bottling; the page-sitemap
also holds history the nav no longer links (Oak Collection Rye = "Sherry Revere Rye", Old Anvil, the Mellwood pages,
Pursuit Series, /series/ is a JS table), so the list is the maker's own nav: the Pursuit United brand page
(/pursuit-united/) plus its Collaborations page. Every page also prints a stray SEO-plugin line ("REPLACE THE ENTIRE
EXISTING BLOCK WITH THIS FILE") in its static HTML: page noise, ignored.

Facts live in the product block: "88 Proof (44% Alc./Vol)", "Proof Varies", a "Spec Sheet" with the component mash
bills ("Bardstown Bourbon Co. 78% Corn; 10% Rye / 12% Malted Barley", "Finger Lakes Distilling 70% Local Corn / 20% Red
Winter Wheat / 10% Malted Barley"), and a "Finished with ..." line. Proof is read only from that block's first "N Proof";
"Proof Varies" (both Barrel Proof pages) states none, so those rows are listed, not confirmed, and keep the seeded batch
proof. No page states an age: age is never read (the seeded 5 on 'Blended Straight' is an owner NAS decision).

Names: the maker renamed the line "Triple Mash" -> "Triple Batch" (pursuitspirits.com/triple-mash-bourbon and
/triple-mash-bourbon-barrel-proof still 301 to the new pages), so the seeds' "Triple Mash ..." names are aliases and the
maker's titles are adopted. The 108-proof plain blends are the same blend as the 88s at a higher proof ("Gift Shop
Only"); the seeded 'Blended Straight' (108, bourbon) and 'Blended Rye' (108, rye) are taken to be those two pages: same
class statement ("A blend of straight bourbon/rye whiskeys"), same proof, and nothing else on the site is a plain 108
blend. That is a judgment, stated here, not something the maker says.

Class and mash: "A blend of straight bourbon whiskeys" is a straight bourbon (High West lesson), so class_raw carries the
straight whiskey, never the word 'blend'. The only cross-type blend is Found Footage (not imported, see below). Each blend
is three component recipes from three distilleries, so mash_raw is left null (no single mash bill); mash_style is read from
the stated recipes: a wheat recipe next to a rye recipe is four grain (Triple Batch Bourbon's page says "four grain" in
words), corn/rye/malt only is traditional. Rye pages are spirit_type rye, which normalize reads as the rye style.

Not imported, and why:
- Joint Operations Bourbon (108), Found Footage (Shortbarrel collab, 112.4), XS Double Oak Rye: the page shows "Coming
  Soon", not a bottle yet. XS Double Oak Bourbon is on the sitemap but not in the nav and states "Proof Varies".
- Pursuit Series (single-barrel episodes, a JS table), Private Select Program (program: 108 proof at account request),
  Old Anvil (Legacy Collection, 375 mL, 11 Summers, 119.4) and Mellwood Bottled in Bond (100): other families (Mellwood
  already has one seed row) — a follow-up, not Pursuit United's family.
- Oak Collection Rye (Sherry Revere Rye, 108): live but unlinked, so history. The seeded bourbon 'The Oak Collection'
  has no page that names it and stays a seed."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Pursuit United"
DELAY = 6
SITEMAP = "https://pursuitspirits.com/sitemap_index.xml"  # reference only; list_urls() is the nav
IMAGE_PREFIX = "https://pursuitspirits.com/"
CATALOG_FAMILIES = ["Pursuit United"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Straight Bourbon Whiskey"
RYE = "Straight Rye Whiskey"
BASE = "https://pursuitspirits.com/"

# slug → (expression, [catalog names it answers to], class statement, finish as the page words it)
PAGES = {
    "united-bourbon": ("Triple Batch Bourbon", ["Pursuit United Triple Mash", "Pursuit United Triple Mash Bourbon"], BOURBON, None),
    "united-rye": ("Triple Batch Rye", ["Pursuit United Triple Mash Rye"], RYE, None),
    "united-bourbon-108": ("Triple Batch Bourbon 108", ["Pursuit United Blended Straight", "Pursuit United Blended Straight Bourbon"], BOURBON, None),
    "united-rye-108": ("Triple Batch Rye 108", ["Pursuit United Blended Rye", "Pursuit United Blended Straight Rye"], RYE, None),
    "united-bourbon-barrel-proof": ("Triple Batch Bourbon Barrel Proof", ["Pursuit United Triple Mash Barrel Proof", "Pursuit United Triple Mash Barrel Proof Bourbon"], BOURBON, None),
    "united-rye-barrel-proof": ("Triple Batch Rye Barrel Proof", ["Pursuit United Triple Mash Barrel Proof Rye"], RYE, None),
    "double-oak-bourbon": ("Double Oak Bourbon", ["Pursuit United Double Oaked Bourbon"], BOURBON, "Double Oaked"),
    "double-oak-rye": ("Double Oak Rye", ["Pursuit United Double Oaked Rye"], RYE, "Double Oaked"),
    "twice-toasted-bourbon": ("Twice Toasted Bourbon", [], BOURBON, "Toasted American and French Oak"),
    "cognac-cask-rye": ("Cognac Cask Rye", [], RYE, "XO Cognac Barrels"),
    "kodama-mizunara-bourbon": ("Kodama Mizunara Bourbon", ["Pursuit United Kodam Mizunara", "Pursuit United Kodam Mizunara Bourbon", "Pursuit United Kodama Mizunara"], BOURBON, "Mizunara and Infrared Toasted Oak"),
    "sakura-bloom-bourbon": ("Sakura Bloom Bourbon", [], BOURBON, "Japanese Cherry Blossom Barrels"),
    # the Meat Church collaboration is filed under this family on the shelf; the seed's own name is kept
    "honey-hog": ("x Meat Church Honey Hog", ["Pursuit x Meat Church Honey Hog Bourbon", "Pursuit United Honey Hog"], BOURBON, "Burleson's Texas Wildflower Honey Barrels"),
}
# Hand-set names where the bar-order name is not "Pursuit United <expression>".
NAME = {"honey-hog": "Pursuit x Meat Church Honey Hog"}
CORE = {"Triple Batch Bourbon", "Triple Batch Rye", "Double Oak Bourbon", "Double Oak Rye"}
RARITY = [(r"triple batch (bourbon|rye)$", "shelf"), (r".", "limited")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + slug + "/" for slug in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _own(text: str) -> str:
    """The product block: after the nav's last 'TOURS + TASTINGS', before the footer."""
    i = text.find("TOURS + TASTINGS|")
    j = text.find("Facebook| Twitter")
    return text[i + len("TOURS + TASTINGS|"):j if j > i else None] if i >= 0 else text


def _mash_style(own: str, spirit_rye: bool) -> str | None:
    if spirit_rye:
        return None  # normalize reads a rye as the rye style
    if re.search(r"four grain", own, re.I):
        return "four_grain"
    wheat = re.search(r"\d+%\s+(?:Local\s+)?(?:Red Winter\s+)?Wheat", own)
    rye = re.search(r"\d+%\s+Rye", own)
    if wheat and rye:
        return "four_grain"  # a wheat recipe and a rye recipe in one blend
    if re.search(r"\d+%\s+(?:Local\s+)?Corn", own) and rye:
        return "traditional" if float(re.search(r"(\d+)%\s+Rye", own).group(1)) < 20 else "high_rye"
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    expression, aliases, class_raw, finish = PAGES[slug]
    name = NAME.get(slug, f"Pursuit United {expression}")
    own = _own(_flat(page))
    if "STRAIGHT" in own and ("STRAIGHT RYE" in own) != (class_raw == RYE):
        return None  # the page's own class statement disagrees with the table: leave it for a human

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*Proof\s*\(", own)  # "Proof Varies" has no number and states none
    proof = float(pm.group(1)) if pm else None

    og = re.search(r'property="og:image" content="([^"]+)"', page)
    img = html.unescape(og.group(1)) if og else None

    return BottlingRecord(
        brand_family="Pursuit United", expression=expression, name=name, source_url=url, proof=proof,
        class_raw=class_raw, mash_raw=None, mash_style=_mash_style(own, class_raw == RYE), finish=finish, image_url=img,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )
