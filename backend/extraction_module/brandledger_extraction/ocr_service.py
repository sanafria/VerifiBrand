"""OCR with Tesseract (via pytesseract).

Returns text plus per-word confidence and bounding boxes so other checks
(e.g. contrast) can reuse the word locations without running OCR twice.
"""
from __future__ import annotations
from dataclasses import dataclass, field

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

from . import config

try:  # pytesseract is a thin wrapper; the Tesseract *program* is the real dependency
    import pytesseract
    from pytesseract import Output
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
except ImportError:  # pragma: no cover
    pytesseract = None


def opencv_available() -> bool:
    """Check if OpenCV (cv2) is installed and available."""
    return cv2 is not None


class OcrUnavailableError(RuntimeError):
    """Tesseract (or pytesseract) is not installed / not reachable."""


class OcrFailedError(RuntimeError):
    """Tesseract ran but failed (timeout, bad image...)."""


@dataclass
class OcrResult:
    text: str = ""
    mean_confidence: float = 0.0          # 0-100, over accepted words
    words: list = field(default_factory=list)   # {text, conf, x, y, w, h}
    variant: str = "original"             # original | enhanced
    scale: float = 1.0                    # words' boxes are in ORIGINAL image coordinates


def tesseract_available() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _run(gray: np.ndarray, lang: str) -> tuple[str, float, list]:
    try:
        data = pytesseract.image_to_data(
            gray, lang=lang, output_type=Output.DICT,
            timeout=config.OCR_TIMEOUT_SECONDS, config="--psm 3")
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "Tesseract is not installed or not on PATH. macOS: `brew install tesseract`.") from exc
    except RuntimeError as exc:           # pytesseract raises RuntimeError on timeout
        raise OcrFailedError(f"Tesseract timed out or failed: {exc}") from exc
    except Exception as exc:
        raise OcrFailedError(f"Tesseract failed: {exc}") from exc

    words, lines = [], {}
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if not text or conf < config.OCR_WORD_MIN_CONF:
            continue
        word = {"text": text, "conf": conf, "x": int(data["left"][i]), "y": int(data["top"][i]),
                "w": int(data["width"][i]), "h": int(data["height"][i])}
        words.append(word)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(text)
    text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
    mean_conf = float(np.mean([w["conf"] for w in words])) if words else 0.0
    return text, mean_conf, words


def _enhance(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Upscale small images, boost local contrast, binarise. Returns (image, scale)."""
    if cv2 is None:
        return gray, 1.0
    h, w = gray.shape[:2]
    scale = 1.0
    if max(h, w) < 1600:
        scale = 1600 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary, scale


def _quality(words: list) -> float:
    """Higher = better: total confident words (favours variants that read more)."""
    return sum(w["conf"] for w in words) / 100.0


def ocr_image(bgr: np.ndarray, lang: str | None = None) -> OcrResult:
    """OCR a BGR image. Tries a second, enhanced pass only when the first looks weak."""
    if cv2 is None:
        raise OcrUnavailableError("OpenCV (cv2) is not installed. Run `pip install opencv-python-headless`.")
    if pytesseract is None:
        raise OcrUnavailableError("pytesseract is not installed. Run `pip install pytesseract`.")
    lang = lang or config.OCR_LANG
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr

    text, conf, words = _run(gray, lang)
    best = OcrResult(text, conf, words, "original", 1.0)

    if conf < config.OCR_RETRY_BELOW or len(words) < 3:
        enhanced, scale = _enhance(gray)
        try:
            t2, c2, w2 = _run(enhanced, lang)
        except OcrFailedError:
            return best
        if _quality(w2) > _quality(words):
            for w in w2:                  # map boxes back to original coordinates
                for k in ("x", "y", "w", "h"):
                    w[k] = int(round(w[k] / scale))
            best = OcrResult(t2, c2, w2, "enhanced", scale)
    return best
