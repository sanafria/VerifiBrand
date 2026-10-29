"""OpenCV-based image-quality and contrast checks.

Honesty rules for this file:
* Blur and resolution checks are heuristics -> they report a confidence.
* The contrast check ESTIMATES colours from OCR word boxes.  It NEVER states
  that an image "passes WCAG".  ``wcag_verified`` is always False.
"""
from __future__ import annotations
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

from . import config
from .models import VisualWarning

CONTRAST_LIMITATIONS = (
    "Estimated from OCR word boxes by separating each box into a background colour and a "
    "text colour. It cannot see text that OCR missed, is unreliable over photos/gradients/"
    "anti-aliased small text, and does not know the real font size. This is NOT a WCAG "
    "conformance test; use a dedicated tool (e.g. WebAIM Contrast Checker) on the real "
    "design colours before claiming compliance."
)


# ---------------------------------------------------------------- basics ----
def _linear(c: np.ndarray) -> np.ndarray:
    c = c / 255.0
    return np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(bgr) -> float:
    b, g, r = _linear(np.asarray(bgr, dtype=float))
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def contrast_ratio(bgr1, bgr2) -> float:
    l1, l2 = relative_luminance(bgr1), relative_luminance(bgr2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def blur_score(bgr: np.ndarray) -> float:
    """Variance of the Laplacian on a copy no larger than BLUR_NORMALISE_SIDE."""
    if cv2 is None:
        return 0.0
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    longest = max(h, w)
    if longest > config.BLUR_NORMALISE_SIDE:
        s = config.BLUR_NORMALISE_SIDE / longest
        gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


# ---------------------------------------------------------------- checks ----
def check_resolution(bgr: np.ndarray, page=None) -> list[VisualWarning]:
    h, w = bgr.shape[:2]
    short, long_ = min(h, w), max(h, w)
    if short < config.MIN_IMAGE_SHORT_SIDE or long_ < config.MIN_IMAGE_LONG_SIDE:
        very_low = short < config.MIN_IMAGE_SHORT_SIDE * 0.6
        return [VisualWarning(
            "LOW_RESOLUTION", "high" if very_low else "medium", 0.9,
            f"Image is only {w}x{h}px. Small text may be unreadable and OCR may be unreliable. "
            f"Recommended at least {config.MIN_IMAGE_LONG_SIDE}x{config.MIN_IMAGE_SHORT_SIDE}px.",
            page, {"width": w, "height": h})]
    return []


def check_blur(bgr: np.ndarray, ocr_confidence: float | None, page=None) -> list[VisualWarning]:
    if cv2 is None:
        return []
    score = blur_score(bgr)
    if float(bgr.std()) < 3.0:      # essentially a flat/blank image: blur is meaningless
        return []
    if score >= config.BLUR_LAPLACIAN_VAR:
        return []
    # Flat designs also have low variance, so confidence is higher only when OCR agrees.
    ocr_agrees = ocr_confidence is not None and ocr_confidence < config.OCR_LOW_CONFIDENCE + 15
    return [VisualWarning(
        "POSSIBLE_BLUR", "high" if ocr_agrees else "medium", 0.85 if ocr_agrees else 0.55,
        "Image looks blurry or out of focus (low edge sharpness)."
        + (" OCR confidence is also low, which supports this." if ocr_agrees else
           " Note: very plain/flat artwork can also score low, so please confirm visually."),
        page, {"laplacian_variance": round(score, 1), "threshold": config.BLUR_LAPLACIAN_VAR})]


def check_ocr_quality(ocr, page=None) -> list[VisualWarning]:
    """Warn when OCR found no text, or read it with low confidence."""
    if ocr is None:
        return []
    if not ocr.words:
        return [VisualWarning(
            "NO_TEXT_DETECTED", "medium", 0.6,
            "OCR found no readable text. The image may contain no text, or the text may be "
            "too small, blurry or low-contrast to read.", page)]
    if ocr.mean_confidence < config.OCR_LOW_CONFIDENCE:
        return [VisualWarning(
            "LOW_OCR_CONFIDENCE", "high", 0.8,
            f"OCR confidence is low ({ocr.mean_confidence:.0f}/100). Extracted text may contain "
            "errors, so any findings based on it need human confirmation.",
            page, {"mean_confidence": round(ocr.mean_confidence, 1)})]
    return []


def estimate_contrast(bgr: np.ndarray, words: list) -> dict:
    """Estimate text/background contrast per OCR word box. See CONTRAST_LIMITATIONS."""
    ratios = []
    h_img, w_img = bgr.shape[:2]
    for w in words:
        if w["h"] < 8 or w["w"] < 8:
            continue
        pad = 2
        x0, y0 = max(0, w["x"] - pad), max(0, w["y"] - pad)
        x1, y1 = min(w_img, w["x"] + w["w"] + pad), min(h_img, w["y"] + w["h"] + pad)
        crop = bgr[y0:y1, x0:x1]
        if crop.size == 0 or crop.shape[0] < 6 or crop.shape[1] < 6:
            continue
        ring = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]]).astype(float)
        bg = np.median(ring, axis=0)
        dist = np.linalg.norm(crop.reshape(-1, 3).astype(float) - bg, axis=1)
        if dist.max() < 12:                      # nothing distinguishable from background
            ratios.append({"word": w["text"], "ratio": 1.0, "box": [w["x"], w["y"], w["w"], w["h"]],
                           "text_bgr": [int(v) for v in bg], "bg_bgr": [int(v) for v in bg]})
            continue
        k = max(3, int(0.15 * len(dist)))
        fg = crop.reshape(-1, 3)[np.argsort(dist)[-k:]].astype(float).mean(axis=0)
        ratios.append({"word": w["text"], "ratio": round(contrast_ratio(fg, bg), 2),
                       "box": [w["x"], w["y"], w["w"], w["h"]],
                       "text_bgr": [int(v) for v in fg], "bg_bgr": [int(v) for v in bg]})
    values = [r["ratio"] for r in ratios]
    summary = {
        "method": "estimated_from_ocr_word_boxes",
        "wcag_verified": False,
        "limitations": CONTRAST_LIMITATIONS,
        "words_measured": len(values),
    }
    if values:
        below = [v for v in values if v < config.CONTRAST_AA_NORMAL]
        summary.update({
            "median_ratio": round(float(np.median(values)), 2),
            "min_ratio": round(float(min(values)), 2),
            "share_below_4_5": round(len(below) / len(values), 2),
            "share_below_3": round(len([v for v in values if v < config.CONTRAST_AA_LARGE]) / len(values), 2),
            "lowest_samples": sorted(ratios, key=lambda r: r["ratio"])[:5],
        })
    return summary


def check_contrast(bgr: np.ndarray, ocr, page=None) -> tuple[list[VisualWarning], dict]:
    if ocr is None or len(ocr.words) < config.CONTRAST_MIN_WORDS:
        return [], {"method": "skipped", "wcag_verified": False,
                    "reason": "Not enough OCR-detected words to estimate contrast.",
                    "limitations": CONTRAST_LIMITATIONS}
    summary = estimate_contrast(bgr, ocr.words)
    if summary["words_measured"] < config.CONTRAST_MIN_WORDS:
        return [], summary
    median, share = summary["median_ratio"], summary["share_below_4_5"]
    if share >= config.CONTRAST_FLAG_SHARE:
        severe = median < config.CONTRAST_AA_LARGE
        return [VisualWarning(
            "POSSIBLE_LOW_CONTRAST", "high" if severe else "medium", 0.7 if severe else 0.5,
            f"Text may have low contrast (estimated median ratio {median}:1; WCAG AA normally asks "
            f"for 4.5:1 for normal text and 3:1 for large text). This is an estimate, not a "
            "compliance test - please verify with the real design colours.",
            page, {k: summary[k] for k in ("median_ratio", "min_ratio", "share_below_4_5")})], summary
    return [], summary


def run_image_checks(bgr: np.ndarray, ocr, page=None) -> tuple[list[VisualWarning], dict]:
    """Run all checks on one image. Returns (warnings, summary-metrics)."""
    warnings: list[VisualWarning] = []
    warnings += check_resolution(bgr, page)
    ocr_conf = ocr.mean_confidence if (ocr is not None and ocr.words) else None
    warnings += check_blur(bgr, ocr_conf, page)
    warnings += check_ocr_quality(ocr, page)
    contrast_warnings, contrast = check_contrast(bgr, ocr, page)
    warnings += contrast_warnings
    h, w = bgr.shape[:2]
    return warnings, {"width": w, "height": h, "blur_laplacian_variance": round(blur_score(bgr), 1),
                      "contrast": contrast}
