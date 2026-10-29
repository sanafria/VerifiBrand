"""Run: PYTHONPATH=backend/extraction_module python backend/extraction_module/make_clearspace_demo.py"""
from pathlib import Path
from PIL import Image, ImageDraw
from brandledger_extraction.visual_checks import run_visual_checks

OUT = Path(__file__).parent / "demo_creatives"
OUT.mkdir(exist_ok=True)
BLUE, AMBER = (30, 58, 138), (245, 158, 11)
LOGO = (60, 60, 120, 120)  # x, y, w, h


def make(name, gap):
    img = Image.new("RGB", (900, 500), (255, 255, 255))
    d = ImageDraw.Draw(img)
    x, y, w, h = LOGO
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=BLUE)              # stand-in logo
    d.rectangle([x + w + gap, y, x + w + gap + 200, y + 40], fill=AMBER)  # neighbouring element
    img.save(OUT / name)
    r = run_visual_checks((OUT / name).read_bytes(), name, logo_bbox=LOGO)
    cs = [(f.category, f.status) for f in r.findings if f.category == "visual_clearspace"]
    print(f"{name:36} clearspace ran: {'visual_clearspace' in r.checks_run}  {cs or 'no findings'}")


make("approved_clearspace.png", 300)
make("bad_clearspace_crowded_logo.png", 10)
