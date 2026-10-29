"""Main entry point: ``extract_content(file_path, content_type)``.

Zoya's scan workflow calls this, takes ``extracted_text`` and feeds it to
Zynab's ``scan_draft(...)``.  The function never raises for bad input; problems
come back in ``errors`` with ``success = False``.
"""
from __future__ import annotations
import time
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

from . import config
from .entity_extractor import extract_entities
from .image_checks import run_image_checks
from .logo_matcher import load_library, match_logos, summarise_logo_results
from .models import ExtractionResult, PageResult, ProcessingError, VisualWarning
from .ocr_service import OcrFailedError, OcrUnavailableError, ocr_image, tesseract_available
from .pdf_utils import PdfBackendMissingError, PdfCorruptError, PdfEncryptedError, open_pdf

if Image is not None:
    Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS


def _sniff(head: bytes) -> str | None:
    """Detect the real type from magic bytes (extension can lie)."""
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"BM"):
        return "image/bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    return None


def _decode_image(path: Path) -> np.ndarray:
    if Image is None or np is None:
        raise RuntimeError("Image processing dependencies (Pillow, numpy) are not installed.")
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        rgb = np.array(img.convert("RGB"))
    return rgb[:, :, ::-1].copy()


def extract_content(file_path: str, content_type: str | None = None, *,
                    run_visual_checks: bool = True, run_logo_matching: bool = True,
                    logo_library_dir: str | None = None) -> dict:
    """Extract text + metadata from an image, PDF or .txt file.

    Returns a JSON-compatible dict (see docs/OUTPUT_SCHEMA.md). Key fields:
    ``success``, ``extracted_text``, ``content_type``, ``warnings``, ``errors``.
    """
    started = time.perf_counter()
    path = Path(file_path)
    result = ExtractionResult(file_name=path.name)
    try:
        _process(path, content_type, result, run_visual_checks, run_logo_matching, logo_library_dir)
    except Exception as exc:           # last-resort guard: never crash the API
        result.success = False
        result.errors.append(ProcessingError("INTERNAL_ERROR", f"Unexpected error: {exc}"))
    _finalise(result, started)
    return result.to_dict()


def _fail(result: ExtractionResult, code: str, message: str, page=None):
    result.success = False
    result.errors.append(ProcessingError(code, message, page))


def _process(path, declared_type, result, run_visual, run_logos, logo_dir):
    # ---- 1. validate the file ------------------------------------------------
    if not path.is_file():
        return _fail(result, "FILE_NOT_FOUND", f"File not found: {path.name}")
    size = path.stat().st_size
    result.size_bytes = size
    ext = path.suffix.lower()
    result.file_type = ext.lstrip(".")
    if size == 0:
        return _fail(result, "EMPTY_FILE", "The file is empty (0 bytes).")
    if size > config.MAX_FILE_BYTES:
        return _fail(result, "FILE_TOO_LARGE",
                     f"File is {size / 1e6:.1f} MB; the limit is {config.MAX_FILE_BYTES / 1e6:.0f} MB.")
    if ext not in config.SUPPORTED_TYPES:
        return _fail(result, "UNSUPPORTED_FORMAT",
                     f"'{ext or 'no extension'}' is not supported. Supported: "
                     + ", ".join(sorted(config.SUPPORTED_TYPES)))
    expected = config.SUPPORTED_TYPES[ext]
    result.content_type = expected

    with open(path, "rb") as fh:
        head = fh.read(16)
    sniffed = _sniff(head)
    if expected != "text/plain":
        if sniffed is None:
            return _fail(result, "CORRUPT_FILE",
                         "File contents do not look like a valid image/PDF (wrong or damaged file).")
        if sniffed != expected:
            result.warnings.append(
                f"Extension says {expected} but contents look like {sniffed}; using the contents.")
            result.content_type = sniffed
    if declared_type and declared_type.split(";")[0].strip().lower() != result.content_type:
        result.warnings.append(
            f"Declared content type '{declared_type}' differs from detected '{result.content_type}'.")

    # ---- 2. dispatch ---------------------------------------------------------
    if result.content_type == "text/plain":
        _process_text(path, result)
    elif result.content_type == "application/pdf":
        _process_pdf(path, result, run_visual, run_logos, logo_dir)
    else:
        _process_image(path, result, run_visual, run_logos, logo_dir)

    # ---- 3. entities (extraction only - NOT policy findings) -----------------
    if result.extracted_text.strip():
        result.entities = extract_entities(result.extracted_text)


def _process_text(path, result):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        result.warnings.append("File was not valid UTF-8; decoded as Latin-1 (accents may be wrong).")
    result.extraction_method = "plain_text"
    result.extracted_text = text.strip()
    result.pages.append(PageResult(1, result.extracted_text, "plain_text", None, len(result.extracted_text)))
    if not result.extracted_text:
        return _fail(result, "EMPTY_EXTRACTION", "The text file contains only whitespace.")
    result.success = True


def _ocr_or_error(bgr, result, page=None):
    """Run OCR; on failure record an error and return None."""
    try:
        return ocr_image(bgr)
    except OcrUnavailableError as exc:
        _fail(result, "OCR_UNAVAILABLE", str(exc), page)
    except OcrFailedError as exc:
        _fail(result, "OCR_FAILED", str(exc), page)
    return None


def _library(result, logo_dir):
    refs, problems = load_library(logo_dir)
    for p in problems:
        result.warnings.append(f"Logo matching: {p}")
    return refs


def _process_image(path, result, run_visual, run_logos, logo_dir):
    if cv2 is None:
        return _fail(result, "OPENCV_UNAVAILABLE",
                     "OpenCV (cv2) is not installed. Image extraction and visual checks require opencv-python-headless.")
    try:
        bgr = _decode_image(path)
    except Exception as exc:
        return _fail(result, "CORRUPT_FILE", f"Could not open the image: {exc}")
    ocr = _ocr_or_error(bgr, result)
    if ocr is None:
        return
    result.extraction_method = "ocr"
    result.extracted_text = ocr.text.strip()
    result.ocr = {"used": True, "engine": "tesseract", "language": config.OCR_LANG,
                  "mean_confidence": round(ocr.mean_confidence, 1), "word_count": len(ocr.words),
                  "variant": ocr.variant}
    result.pages.append(PageResult(1, result.extracted_text, "image_ocr",
                                   round(ocr.mean_confidence, 1), len(result.extracted_text)))
    if run_visual:
        warnings, summary = run_image_checks(bgr, ocr)
        result.visual_warnings += warnings
        result.visual_summary = summary
    if run_logos:
        refs = _library(result, logo_dir)
        _add_logo_results(result, match_logos(bgr, refs, has_text=len(ocr.words) > 5))
    if not result.extracted_text:
        result.warnings.append("No text could be extracted from this image.")
        # still a valid, successful run: the image may legitimately contain no text,
        # but downstream must NOT treat 'no text' as 'no violations'.
    result.success = True


def _process_pdf(path, result, run_visual, run_logos, logo_dir):
    try:
        doc = open_pdf(str(path))
    except PdfEncryptedError as exc:
        return _fail(result, "PDF_ENCRYPTED", str(exc))
    except PdfCorruptError as exc:
        return _fail(result, "CORRUPT_FILE", f"Could not open the PDF: {exc}")
    except PdfBackendMissingError as exc:
        return _fail(result, "PDF_BACKEND_MISSING", str(exc))

    try:
        n = doc.page_count
        if n == 0:
            return _fail(result, "EMPTY_FILE", "The PDF has no pages.")
        if n > config.MAX_PDF_PAGES:
            result.warnings.append(
                f"PDF has {n} pages; only the first {config.MAX_PDF_PAGES} were processed.")
        limit = min(n, config.MAX_PDF_PAGES)
        methods, confidences, texts = set(), [], []
        refs = _library(result, logo_dir) if run_logos else []
        ocr_ok = True
        for i in range(limit):
            page_no = i + 1
            try:
                layer = doc.page_text(i).strip()
            except Exception as exc:
                layer = ""
                result.warnings.append(f"Page {page_no}: could not read text layer ({exc}).")
            rendered = None
            if len(layer) >= config.PDF_MIN_TEXT_CHARS:
                page = PageResult(page_no, layer, "text_layer", None, len(layer))
                methods.add("text_layer")
            else:
                page = PageResult(page_no, layer, "none", None, len(layer))
                if ocr_ok:
                    try:
                        rendered = doc.render_page(i, config.PDF_RENDER_DPI)
                    except Exception as exc:
                        _fail(result, "PAGE_RENDER_FAILED", f"Could not render page: {exc}", page_no)
                        rendered = None
                    if rendered is not None:
                        ocr = _ocr_or_error(rendered, result, page_no)
                        if ocr is None:
                            ocr_ok = False
                        else:
                            page = PageResult(page_no, ocr.text.strip(), "ocr",
                                              round(ocr.mean_confidence, 1), len(ocr.text.strip()))
                            methods.add("ocr")
                            confidences.append(ocr.mean_confidence)
                            if run_visual:
                                w, summary = run_image_checks(rendered, ocr, page_no)
                                result.visual_warnings += w
                                result.visual_summary[f"page_{page_no}"] = summary
                if not page.text:
                    result.warnings.append(f"Page {page_no}: no text found.")
            result.pages.append(page)
            texts.append(page.text)
            if refs and page_no <= config.LOGO_MAX_PDF_PAGES:
                try:
                    img = rendered if rendered is not None else doc.render_page(i, 150)
                    _add_logo_results(result, match_logos(img, refs, page_no, has_text=True))
                except Exception as exc:
                    result.warnings.append(f"Page {page_no}: logo matching skipped ({exc}).")
        result.extracted_text = "\n\n".join(t for t in texts if t).strip()
        result.extraction_method = ("mixed" if len(methods) > 1 else next(iter(methods), "none"))
        if "ocr" in methods:
            result.ocr = {"used": True, "engine": "tesseract", "language": config.OCR_LANG,
                          "mean_confidence": round(sum(confidences) / len(confidences), 1),
                          "pages_ocr": [p.page for p in result.pages if p.method == "ocr"]}
        else:
            result.ocr = {"used": False}
        result.ocr["pdf_backend"] = doc.name
        if result.errors:
            result.success = False
        elif not result.extracted_text:
            _fail(result, "EMPTY_EXTRACTION",
                  "No text could be extracted from any page (blank, image-only without readable text).")
        else:
            result.success = True
    finally:
        doc.close()


def _add_logo_results(result, per_reference):
    """Store only the single most informative result for each image/page."""
    best = summarise_logo_results(per_reference)
    if best:
        result.logo_matches.append(best)


def _finalise(result: ExtractionResult, started: float):
    reasons = []
    if result.errors:
        reasons.append("Processing errors occurred; content could not be fully read.")
    if result.visual_warnings:
        reasons.append("Visual warnings were raised.")
    if result.ocr.get("used") and result.ocr.get("mean_confidence", 100) < 85:
        reasons.append("Text came from OCR with less than high confidence; it may contain errors.")
    if result.logo_matches:
        reasons.append("Logo results are similarity estimates and need human confirmation.")
    if any(d.get("ambiguous") for d in result.entities.get("dates", [])):
        reasons.append("Ambiguous date format found.")
    if result.success and not result.extracted_text.strip():
        reasons.append("No text extracted - cannot be treated as 'no violations'.")
    result.review_reasons = reasons
    result.human_review_required = bool(reasons) or not result.success
    result.processing_ms = int((time.perf_counter() - started) * 1000)
