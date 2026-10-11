"""klukewhiskeycompany.com (K.LUKE Whiskey Company, Mississippi; the founders Jonathan and Jennifer Maisano blend
barrels sourced from Kentucky and Indiana distilleries). A Wix site; robots.txt allows everything for `*` and sets a
Crawl-delay only for dotbot/AhrefsBot, so DELAY is the project's usual 6. kluke.com is a parked domain (it resolves to
a parking host and resets the connection); the real site is the one Breaking Bourbon's "Official Website" link names.
The pages are server-rendered, so the facts are in the static HTML. The honest fetcher gets 200s; nothing is worked
around.

Pages: /releases (the batch ledger — the only page with proofs), /trade (sell-sheet names), / (award headings), /blending
(how the blends are made; no per-bottle fact). The sitemap lists releases, trade, blending, shop and press only.

The releases page is one table per line, each preceded by a bottle-art image whose HTML alt text is its file name
(`100proof.png`, `barrelStrength.png`, `rye.png`, `toastedBarrel.png`, `singleBarrel.png`), then "BATCH n | Bottled d/m/yy |
Total Batch Yield ... | Proof x". The alt text is page markup, not a reading of the picture. The trade page's sell-sheet list
names what each line is ("K.LUKE Toasted Barrel, Barrel Strength Bourbon Batch 4", "K.LUKE Toasted Barrel, Barrel Strength
Rye Batch 5", "K.LUKE Barrel Strength Bourbon Batch 12/14/15/16", "Batch 5/6 - Small Batch 100 Proof Bourbon"), and the home
page's award headings repeat those five names (Barrel Strength Bourbon, Toasted Barrel Bourbon, Toasted Barrel Rye,
Small Batch 100 Proof, Keenan Cab Reserve). Matching the two: toastedBarrel.png ends at Batch 4 = the sell sheet's Toasted
Barrel Bourbon Batch 4; rye.png reaches Batch 5 = the sell sheet's Toasted Barrel Rye Batch 5 (so the rye line is the toasted
one, not a plain barrel-strength rye as the review site titled it).

Judgment (all of it lives here so a re-run reproduces it):
  - A batch is not a row. Each line is one bottling; the *latest* batch on the ledger (highest number, the newest
    "Bottled" date) supplies the proof, the way Booker's is handled. Barrel Strength Bourbon is therefore 114.4 (Batch 16),
    not the seed's 118.0 (Batch 15). Every batch's proof varies by a few points; the trade page says so ("will vary in proof
    and flavor from batch to batch"). The proof will drift on the next refresh and that is expected.
  - Small Batch 100 Proof states its proof in its own name (home page, trade page, image file name) and prints none in
    the ledger, so 100 is read from the name (PROOF_FROM_NAME, the Cedar Ridge precedent).
  - No age, mash bill or finish is read anywhere: the blending page says "a variety of ages" and "mash bills up to 36% rye"
    (a ceiling across components, not a recipe). The bottle-art image also carries label text; label photos are not read, so
    no age is taken from it. Toasted Barrel's finish is its name ("Toasted Barrel", read by `finish()`). Keenan's finish is the
    page's own sentence (secondary aged in fresh-dumped Keenan Reserve Cabernet Sauvignon French and American oak barrels).
  - Keenan Reserve Cabernet Sauvignon Finished Bourbon: the table after the single-barrel list has no image alt; its
    paragraph (the only remaining product on the page, directly below it) names it. Two batches; the latest supplies the proof.
  - The Single Barrel table (barrels #4913, #4919, #56971 ...), the trade page's "Barrel Program" casks (Madeira, Armagnac,
    Pineau des Charentes, Sauternes, Cognac, Tawny Port finished single barrels and 8-month extended-age Kelvin Toasted
    Barrel) and the Maisano Hand Select picks are store/club selections, each barrel its own proof: a program, not a
    bottling. Not imported. The seed 'K.Luke Cask Finished Single Barrel, Cognac Cask' (117.4) therefore stays a seed row;
    the Cognac cask is listed on the trade page only as a retailer's barrel, with no proof.
  - The seed 'K.Luke Blended Bourbon' (Breaking Bourbon's "Blended Straight Bourbon (Batch 5)", 100 proof) and 'K.Luke Small
    Batch' ("Small Batch Straight Bourbon (Batch 2)", 100 proof) are the same Small Batch 100 Proof line at two batches; the
    importer claims 'Small Batch' (alias below) and the sibling is merged into it by hand (`cellar.merge_product`).
Class is the maker's word for the line (Bourbon / Rye); "straight" is not printed in the page text so it is not asserted.
Rarity: the 100 Proof line is regularly restocked in eight states; the barrel-strength and toasted lines are allocated at
roughly 700-1,900 bottles a batch; Keenan is "very limited availability" in its own words."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "K.Luke"
DELAY = 6
BASE = "https://www.klukewhiskeycompany.com/"
RELEASES = BASE + "releases"
SITEMAP = BASE + "sitemap.xml"  # not crawled (list_urls is fixed); scripts/bourbon_write.py reads its host
IMAGE_PREFIX = "https://static.wixstatic.com/media/"
CATALOG_FAMILIES = ["K.Luke"]
PRODUCER_BY_FAMILY = {}
FAMILY = "K.Luke"

# Evidence pages cached with the crawl; only /releases yields records.
PAGES = [BASE, RELEASES, BASE + "trade", BASE + "blending"]

# image alt (file name) on /releases -> (expression, aliases, class, finish)
SERIES = {
    "100proof.png": ("Small Batch 100 Proof", ["K.Luke Small Batch", "K.Luke Small Batch 100 Proof Bourbon"], "Bourbon Whiskey", None),
    "barrelStrength.png": ("Barrel Strength Bourbon", ["K.Luke Small Batch Barrel Strength", "K.Luke Barrel Strength"], "Bourbon Whiskey", None),
    "rye.png": ("Toasted Barrel Barrel Strength Rye", ["K.Luke Small Batch Barrel Strength Rye", "K.Luke Toasted Barrel Rye"], "Rye Whiskey", None),
    "toastedBarrel.png": ("Toasted Barrel Barrel Strength Bourbon", ["K.Luke Toasted Barrel Barrel Strength", "K.Luke Toasted Barrel Bourbon"], "Bourbon Whiskey", None),
}
KEENAN = ("Keenan Reserve Cabernet Sauvignon Finished Bourbon", ["K.Luke Keenan Reserve", "K.Luke Keenan Cab Reserve"], "Bourbon Whiskey",
          "Cabernet Sauvignon French and American Oak Barrels")
# The maker's own product name carries the proof where the ledger prints none.
PROOF_FROM_NAME = {"100proof.png": 100.0}

# The two lines with a standing, repeated release; the toasted pair and Keenan are batch releases.
CORE = {"Small Batch 100 Proof", "Barrel Strength Bourbon"}
RARITY = [(r"keenan", "limited"), (r"100 proof", "shelf"), (r".", "allocated")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return list(PAGES)


def _main(page: str) -> str:
    i = page.find('<main id="PAGES_CONTAINER"')
    t = page[i:] if i > 0 else page
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S)
    t = re.sub(r'<img[^>]*?src="([^"]*)"[^>]*?alt="([^"]*)"[^>]*>', r"|IMG[\2]{\1}|", t)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\s*\|\s*)+", " | ", t)


def _batches(section: str) -> list[tuple[int, float | None]]:
    """[(batch number, proof or None)] for every 'BATCH n | Bottled ... | Proof x' block of one table."""
    out = []
    for m in re.finditer(r"BATCH (\d+) \|(.*?)(?=BATCH \d+ \||$)", section):
        p = re.search(r"Proof (\d{2,3}(?:\.\d+)?)", m.group(2))
        out.append((int(m.group(1)), float(p.group(1)) if p else None))
    return out


def _wix_original(src: str) -> str | None:
    m = re.match(r"(https://static\.wixstatic\.com/media/[^/]+)", src)
    return m.group(1) if m else None


def parse(url: str, page: str) -> list[BottlingRecord] | None:
    if url.rstrip("/") != RELEASES:
        return None
    text = _main(page)
    parts = re.split(r"(\|\s*IMG\[[^\]]*\]\{[^}]*\}\s*)", text)
    # parts alternates: text, marker, text, marker ... ; each table is the text after its marker
    sections: list[tuple[str, str, str]] = []  # (alt, src, table text)
    for i in range(1, len(parts), 2):
        m = re.match(r"\|\s*IMG\[([^\]]*)\]\{([^}]*)\}", parts[i])
        sections.append((m.group(1), m.group(2), parts[i + 1] if i + 1 < len(parts) else ""))
    recs: list[BottlingRecord] = []
    for alt, src, body in sections:
        if alt in SERIES:
            expression, aliases, class_raw, finish = SERIES[alt]
            image = _wix_original(src)
        elif alt == "" and "Keenan Reserve Cabernet Sauvignon Finished Bourbon" in body and "BATCH" in body:
            expression, aliases, class_raw, finish = KEENAN
            image = None  # its picture is an unlabeled thumbnail
        else:
            continue
        batches = _batches(body)
        if not batches:
            continue
        number, proof = max(batches)  # the latest batch is the current release
        if proof is None:
            proof = PROOF_FROM_NAME.get(alt)
        name = f"{FAMILY} {expression}"
        recs.append(BottlingRecord(
            brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=proof,
            class_raw=class_raw, finish=finish, image_url=image,
            aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
        ))
    return recs or None
