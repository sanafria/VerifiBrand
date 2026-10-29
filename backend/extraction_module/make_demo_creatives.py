"""Builds a small demo set: one approved creative and one noncompliant creative per check.
Run: PYTHONPATH=backend/extraction_module python backend/extraction_module/make_demo_creatives.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pymupdf
from brandledger_extraction.visual_checks import run_visual_checks

OUT = Path(__file__).parent / "demo_creatives"
OUT.mkdir(exist_ok=True)

BLUE, AMBER, WHITE = (30, 58, 138), (245, 158, 11), (255, 255, 255)
RED, LIME = (220, 20, 60), (50, 205, 50)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def make_png(name, bg, accent, text_colour, headline, body):
    img = Image.new("RGB", (900, 500), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 380, 900, 500], fill=accent)
    d.text((50, 60), headline, fill=text_colour, font=_font(64))
    d.text((50, 190), body, fill=text_colour, font=_font(34))
    img.save(OUT / name)


def make_pdf(name, head_size, body_size, head_font="helv", body_font="helv"):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 110), "Spring Sale 20% Off", fontsize=head_size, fontname=head_font)
    p.insert_text((72, 160), "Valid on selected items until 30 November 2026.", fontsize=body_size, fontname=body_font)
    (OUT / name).write_bytes(doc.tobytes())


# Approved creatives
make_png("approved_poster_on_palette.png", BLUE, AMBER, WHITE, "SPRING SALE 20% OFF", "Valid on selected items only")
make_pdf("approved_flyer_good_type_and_layout.pdf", 30, 11)

# Noncompliant creatives
make_png("bad_colour_off_palette.png", RED, LIME, WHITE, "SPRING SALE 20% OFF", "Valid on selected items only")
make_pdf("bad_typography_wrong_font.pdf", 30, 11, "helv", "cour")
make_pdf("bad_typography_tiny_text.pdf", 30, 7)
make_pdf("bad_layout_weak_headline.pdf", 12, 11)

print(f"{'file':44} processed  findings")
for f in sorted(OUT.iterdir()):
    r = run_visual_checks(f.read_bytes(), f.name)
    found = [(x.category, x.status) for x in r.findings]
    print(f"{f.name:44} {str(r.processed):9}  {found if found else 'no findings'}")
