"""PDF access with two interchangeable backends.

* PyMuPDF (``import fitz``) - the team's chosen library; used when installed.
* pypdfium2 - automatic fallback so the module still works without PyMuPDF.

Both expose the same tiny interface: ``page_count``, ``page_text(i)``,
``render_page(i, dpi)`` (returns a BGR numpy array) and ``close()``.
"""
from __future__ import annotations

try:
    import numpy as np
except ImportError:
    np = None


class PdfEncryptedError(Exception):
    pass


class PdfCorruptError(Exception):
    pass


class PdfBackendMissingError(Exception):
    pass


def _pil_to_bgr(pil_image) -> np.ndarray:
    rgb = np.array(pil_image.convert("RGB"))
    return rgb[:, :, ::-1].copy()


class _FitzDoc:
    name = "pymupdf"

    def __init__(self, path: str):
        import fitz
        self._fitz = fitz
        try:
            self._doc = fitz.open(path)
        except Exception as exc:
            raise PdfCorruptError(str(exc)) from exc
        if self._doc.needs_pass:
            self._doc.close()
            raise PdfEncryptedError("PDF is password protected.")
        self.page_count = self._doc.page_count

    def page_text(self, i: int) -> str:
        return self._doc[i].get_text("text") or ""

    def render_page(self, i: int, dpi: int) -> np.ndarray:
        pix = self._doc[i].get_pixmap(matrix=self._fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        return arr[:, :, ::-1].copy() if pix.n >= 3 else cv2_gray_to_bgr(arr)

    def close(self):
        self._doc.close()


def cv2_gray_to_bgr(arr: np.ndarray) -> np.ndarray:
    try:
        import cv2
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    except ImportError:
        if np is not None:
            return np.repeat(arr[:, :, :1], 3, axis=2)
        return arr


class _PdfiumDoc:
    name = "pypdfium2"

    def __init__(self, path: str):
        import pypdfium2 as pdfium
        try:
            self._doc = pdfium.PdfDocument(path)
        except Exception as exc:
            msg = str(exc)
            if "password" in msg.lower():
                raise PdfEncryptedError("PDF is password protected.") from exc
            raise PdfCorruptError(msg) from exc
        self.page_count = len(self._doc)

    def page_text(self, i: int) -> str:
        page = self._doc[i]
        try:
            textpage = page.get_textpage()
            try:
                return textpage.get_text_range() or ""
            finally:
                textpage.close()
        finally:
            page.close()

    def render_page(self, i: int, dpi: int) -> np.ndarray:
        page = self._doc[i]
        try:
            return _pil_to_bgr(page.render(scale=dpi / 72).to_pil())
        finally:
            page.close()

    def close(self):
        self._doc.close()


def open_pdf(path: str):
    """Open a PDF with the best available backend."""
    try:
        import fitz  # noqa: F401
        return _FitzDoc(path)
    except ImportError:
        pass
    try:
        import pypdfium2  # noqa: F401
    except ImportError as exc:
        raise PdfBackendMissingError(
            "No PDF backend installed. Run `pip install pymupdf`.") from exc
    return _PdfiumDoc(path)
