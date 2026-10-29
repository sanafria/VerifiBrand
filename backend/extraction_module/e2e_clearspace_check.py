"""Run from repo root: PYTHONPATH=.:backend/extraction_module python backend/extraction_module/e2e_clearspace_check.py"""
from pathlib import Path
import cv2, numpy as np
from brandledger_extraction.file_processing import extract_content
from brandledger_extraction.logo_matcher import load_library
from brandledger_extraction.visual_checks import run_visual_checks
from backend.app.api.uploads import _confident_logo_box

OUT = Path(__file__).parent / "demo_creatives"
refs, problems = load_library(None)
print("library:", [(r.name, r.status, r.placeholder) for r in refs], problems or "")
ref = refs[0]
logo = ref.bgr
scale = 120 / logo.shape[0]
logo = cv2.resize(logo, None, fx=scale, fy=scale)
canvas = np.full((500, 900, 3), 255, np.uint8)
y0, x0 = 190, 300
canvas[y0:y0 + logo.shape[0], x0:x0 + logo.shape[1]] = logo
cv2.putText(canvas, "SPRING SALE 20% OFF", (40, 450), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
path = OUT / "logo_on_canvas.png"
cv2.imwrite(str(path), canvas)
print("logo placed at", (x0, y0, logo.shape[1], logo.shape[0]))

result = extract_content(str(path), "image/png")
for m in result.get("logo_matches", []):
    print("logo match:", m.get("status"), m.get("similarity_score"), m.get("region_full"), m.get("image_size"))
box, size = _confident_logo_box(result)
print("box passed to visual check:", box, size)
r = run_visual_checks(path.read_bytes(), path.name, box, size, box is not None)
print("checks_run:", r.checks_run)
print("skipped:", r.skipped)
print("errors:", r.errors)
print("clearspace findings:", [(f.status, f.matched_text) for f in r.findings if f.category == "visual_clearspace"])
