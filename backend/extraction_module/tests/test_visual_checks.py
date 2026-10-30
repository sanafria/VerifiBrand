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

def _pdf_sizes(head_size, body_size, font="helv"):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 100), "Big Headline", fontsize=head_size, fontname=font)
    p.insert_text((72, 140), "Body copy goes here for the test.", fontsize=body_size, fontname=font)
    return doc.tobytes()


def test_pdf_weak_headline_flagged_layout():
    r = run_visual_checks(_pdf_sizes(12, 11), "a.pdf")
    assert any(f.category == "visual_layout" for f in r.findings)


def test_pdf_small_text_flagged_typography():
    r = run_visual_checks(_pdf_sizes(30, 7), "a.pdf")
    assert any(f.category == "visual_typography" for f in r.findings)


def test_clearspace_box_is_rescaled_from_reference_size():
    bad, good = _logo_img(True), _logo_img(False)
    w, h = bad.size
    # box and size are given at 2x, as if measured on a larger render
    for img, expect_fail in ((bad, True), (good, False)):
        r = run_visual_checks(_png(img), "a.png", logo_bbox=(200, 200, 80, 80), logo_ref_size=(w * 2, h * 2))
        assert "visual_clearspace" in r.checks_run
        fails = [f for f in r.findings if f.category == "visual_clearspace"]
        assert bool(fails) == expect_fail


def test_clearspace_skipped_when_reference_shape_differs():
    img = _logo_img(False)
    w, h = img.size
    r = run_visual_checks(_png(img), "a.png", logo_bbox=(10, 10, 20, 20), logo_ref_size=(w, h * 2))
    assert "visual_clearspace" not in r.checks_run
    assert any(s.startswith("visual_clearspace") for s in r.skipped)


def test_estimated_logo_box_downgrades_clearspace_fail_to_needs_review():
    img = _png(_logo_img(True))
    hard = run_visual_checks(img, "a.png", logo_bbox=(100, 100, 40, 40))
    soft = run_visual_checks(img, "a.png", logo_bbox=(100, 100, 40, 40), logo_estimated=True)
    assert [f.status for f in hard.findings if f.category == "visual_clearspace"] == ["fail"]
    assert [f.status for f in soft.findings if f.category == "visual_clearspace"] == ["needs_review"]
    assert "visual_clearspace" in soft.checks_run


def test_explainer_rules():
    from brandledger_extraction.visual_explainer import explain_visual
    assert "not a pass" in explain_visual({"processed": False, "errors": ["could not open file: x"]})
    assert "No visual check result" in explain_visual(None)
    clean = explain_visual({"processed": True, "checks_run": ["visual_colour"], "findings": [],
                            "skipped": ["visual_typography: fonts can only be read from PDFs"], "errors": []})
    assert "not mean the creative is fully compliant" in clean and "Not checked" in clean
    review = explain_visual({"processed": True, "checks_run": ["visual_clearspace"], "skipped": [], "errors": [],
                             "findings": [{"category": "visual_clearspace", "status": "needs_review",
                                           "matched_text": "Logo close to edge", "explanation": "x"}]})
    assert "A person must confirm" in review
    real = run_visual_checks(_pdf(("helv", "cour")), "a.pdf")
    assert "Problem (typography)" in explain_visual({"processed": real.processed, "checks_run": real.checks_run,
        "findings": real.findings, "skipped": real.skipped, "errors": real.errors})
