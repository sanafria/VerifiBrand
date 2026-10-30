"""Central settings and thresholds for the extraction module.

Every number that affects a warning lives here so the team can tune it in one
place.  Thresholds were calibrated ONLY on the synthetic sample dataset - re-tune
them with real Inkloom assets (see docs/INTEGRATION.md).
"""
import os
from pathlib import Path

SCHEMA_VERSION = "1.0"

# ---- file validation -------------------------------------------------------
MAX_FILE_BYTES = int(os.getenv("BL_MAX_FILE_MB", "20")) * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("BL_MAX_PDF_PAGES", "15"))
MAX_IMAGE_PIXELS = 50_000_000          # guard against decompression bombs

SUPPORTED_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}
IMAGE_MIME_TYPES = {m for m in SUPPORTED_TYPES.values() if m.startswith("image/")}

# ---- OCR -------------------------------------------------------------------
OCR_LANG = os.getenv("BL_OCR_LANG", "eng")
OCR_TIMEOUT_SECONDS = 60
OCR_WORD_MIN_CONF = 30                 # ignore words Tesseract is very unsure about
OCR_LOW_CONFIDENCE = 60                # mean confidence below this -> warning
OCR_RETRY_BELOW = 75                   # try the enhanced variant below this
PDF_RENDER_DPI = 200
PDF_MIN_TEXT_CHARS = 30                # fewer chars than this -> treat page as scanned
TESSERACT_CMD = os.getenv("TESSERACT_CMD")   # optional explicit path

# ---- visual checks ---------------------------------------------------------
MIN_IMAGE_SHORT_SIDE = 400             # px; below -> LOW_RESOLUTION
MIN_IMAGE_LONG_SIDE = 800
BLUR_LAPLACIAN_VAR = 60.0              # below -> possible blur (on <=1000px copy)
BLUR_NORMALISE_SIDE = 1000
CONTRAST_AA_NORMAL = 4.5               # WCAG AA for normal text (reference only)
CONTRAST_AA_LARGE = 3.0
CONTRAST_MIN_WORDS = 3                 # need this many measurable words
CONTRAST_FLAG_SHARE = 0.30             # share of words below 4.5 that triggers a warning

# ---- logo matching ---------------------------------------------------------
LOGO_LIBRARY_DIR = Path(os.getenv(
    "BL_LOGO_LIBRARY", Path(__file__).resolve().parent.parent / "logo_library"))
LOGO_MATCH_THRESHOLD = 0.70            # shape score >= this -> candidate match
LOGO_UNCERTAIN_THRESHOLD = 0.55        # between this and match threshold -> uncertain
LOGO_COLOR_DELTA_E = 25.0              # CIE76 distance; above -> colour differs
LOGO_STANDALONE_MAX_SIDE = 900         # images this small are treated as "a logo file"
LOGO_MAX_PDF_PAGES = 3
