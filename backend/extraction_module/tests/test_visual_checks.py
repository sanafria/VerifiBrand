import io
import pytest
from PIL import Image, ImageDraw
from brandledger_extraction.visual_checks import run_visual_checks, check_clearspace, load_rules


def _png(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def test_on_palette_image_has_no_colour_finding():
    r = run_visual_checks(_png(Image.new("RGB", (200, 200), "#1E3A8A")), "a.png")
    assert r.processed and "visual_colour" in r.checks_run
    assert [f for f in r.findings if f.category == "visual_colour"] == []


def test_off_palette_image_fails_colour():
    r = run_visual_checks(_png(Image.new("RGB", (200, 200), "#FF0000")), "a.png")
    f = [f for f in r.findings if f.category == "visual_colour"]
    assert f and f[0].status == "fail" and f[0].policy_card_id == "VIS-COLOUR-001"


def test_corrupt_file_not_processed():
    r = run_visual_checks(b"not an image", "a.png")
    assert r.processed is False and r.errors and r.findings == []


def test_images_skip_typography_and_layout():
    r = run_visual_checks(_png(Image.new("RGB", (50, 50), "white")), "a.png")
    assert any("typography" in s for s in r.skipped) and any("layout" in s for s in r.skipped)


def _logo_img(blob):
    img = Image.new("RGB", (300, 300), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([100, 100, 139, 139], fill="black")
    if blob:
        d.rectangle([145, 100, 154, 109], fill="black")
    return img


def test_clearspace_pass_and_fail():
    rules = load_rules()
    assert check_clearspace(_logo_img(False), (100, 100, 40, 40), rules) == []
    out = check_clearspace(_logo_img(True), (100, 100, 40, 40), rules)
    assert out and out[0].category == "visual_clearspace" and out[0].status == "fail"


def _pdf(fonts):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 100), "Big Headline", fontsize=30, fontname=fonts[0])
    p.insert_text((72, 140), "Body copy goes here for the test.", fontsize=11, fontname=fonts[1])
    return doc.tobytes()


def test_pdf_good_typography_and_layout():
    r = run_visual_checks(_pdf(("helv", "helv")), "a.pdf")
    assert "visual_typography" in r.checks_run and "visual_layout" in r.checks_run
    assert [f for f in r.findings if f.category in ("visual_typography", "visual_layout")] == []


def test_pdf_bad_font_flagged():
    r = run_visual_checks(_pdf(("helv", "cour")), "a.pdf")
    assert any(f.category == "visual_typography" for f in r.findings)