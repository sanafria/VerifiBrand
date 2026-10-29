"""Upload & Scan API Router for BrandLedger (Owned by Mahadevi).

POST /api/scans/upload
    1. Receives an image / PDF / .txt file.
    2. Runs the extraction module (OCR, PDF text, entity candidates, visual checks, logo similarity).
    3. Hands the extracted text to Zoya's existing ``execute_scan`` - the SAME scan workflow
       used for typed text. No separate scan logic or database schema is created here.

Safety rule: if extraction fails or finds no text, NO scan is created and an error is
returned. "Could not read the file" must never look like "no violations found".

Extraction details (visual warnings, logo results, entities) are returned in the response
but are NOT persisted in the database (no schema change was made).
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.schemas.scan import ScanResponse
from backend.app.services.scan_service import execute_scan
from backend.extraction_module.brandledger_extraction import config as extraction_config
from backend.extraction_module.brandledger_extraction import extract_content
from backend.extraction_module.brandledger_extraction.visual_checks import run_visual_checks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Scan uploads"])

# Extraction error codes that mean "server is missing a dependency", not "bad file".
_SERVER_SIDE_CODES = {"OCR_UNAVAILABLE", "PDF_BACKEND_MISSING", "INTERNAL_ERROR", "OPENCV_UNAVAILABLE"}
_VISUAL_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}

try:
    import multipart
    _MULTIPART_AVAILABLE = True
except ImportError:
    _MULTIPART_AVAILABLE = False


class ExtractionSummary(BaseModel):
    file_name: str
    file_type: str
    content_type: str
    extraction_method: str
    ocr: Dict[str, Any] = {}
    pages: List[Dict[str, Any]] = []
    entities: Dict[str, Any] = {}
    visual_warnings: List[Dict[str, Any]] = []
    logo_matches: List[Dict[str, Any]] = []
    warnings: List[str] = []
    human_review_required: bool
    review_reasons: List[str] = []
    visual: Optional[Dict[str, Any]] = None


class UploadScanResponse(BaseModel):
    scan: ScanResponse
    extraction: ExtractionSummary


async def _save_upload(upload: UploadFile) -> Path:
    """Stream the upload to a temp file, enforcing the size limit. Returns the temp path."""
    suffix = Path(upload.filename or "").suffix.lower()
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="bl_upload_")
    os.close(fd)
    tmp_path = Path(tmp_name)
    size = 0
    try:
        with open(tmp_path, "wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > extraction_config.MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "message": "File is too large.",
                            "errors": [{
                                "code": "FILE_TOO_LARGE",
                                "message": f"Limit is {extraction_config.MAX_FILE_BYTES // (1024 * 1024)} MB.",
                            }],
                        },
                    )
                out.write(chunk)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path


_CONFIDENT_LOGO_STATUSES = {"possible_match", "possible_variant_mismatch", "possible_outdated_logo"}


def _confident_logo_box(result):
    """Logo box from page 1 of a confident logo match, else (None, None).
    Weak matches still carry a box, so they must never be used for clear space."""
    for m in result.get("logo_matches") or []:
        region, size = m.get("region_full"), m.get("image_size")
        if (m.get("status") in _CONFIDENT_LOGO_STATUSES and m.get("page") in (None, 1)
                and region and size and region["w"] > 0 and region["h"] > 0):
            return [region["x"], region["y"], region["w"], region["h"]], [size["w"], size["h"]]
    return None, None


if _MULTIPART_AVAILABLE:
    @router.post(
        "/upload",
        response_model=UploadScanResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Upload a file, extract its text, and scan it",
        description=(
            "Accepts an image, PDF or .txt file. Extracts text (OCR when needed), then runs the "
            "same scan workflow as POST /api/scans. If no text can be extracted, nothing is "
            "scanned and an error is returned."
        ),
    )
    async def upload_and_scan(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        draft_id: Optional[UUID] = Form(None),
        scan_date: Optional[str] = Form(None),
    ) -> UploadScanResponse:
        original_name = Path(file.filename or "upload").name  # basename only, never a path
        tmp_path = await _save_upload(file)
        visual = None
        try:
            # OCR / PDF rendering is CPU-heavy and blocking: keep it off the event loop.
            result = await asyncio.to_thread(extract_content, str(tmp_path), file.content_type)
            if Path(original_name).suffix.lower() in _VISUAL_EXTS:
                # visual checks must run before the temp file is deleted below
                file_bytes = await asyncio.to_thread(tmp_path.read_bytes)
                box, ref_size = _confident_logo_box(result)
                visual = await asyncio.to_thread(
                    run_visual_checks, file_bytes, original_name, box, ref_size, box is not None)
        finally:
            tmp_path.unlink(missing_ok=True)
        result["file_name"] = original_name

        errors = result.get("errors", [])
        if not result.get("success"):
            codes = {e.get("code") for e in errors}
            http_status = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if codes & _SERVER_SIDE_CODES
                else 422
            )
            raise HTTPException(
                status_code=http_status,
                detail={
                    "message": "The file could not be processed. No scan was created.",
                    "errors": errors,
                    "warnings": result.get("warnings", []),
                },
            )

        text = (result.get("extracted_text") or "").strip()
        if not text:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": (
                        "No readable text was found in this file. No scan was created. "
                        "This is NOT a clean result - the file needs human review."
                    ),
                    "errors": [{"code": "NO_TEXT_EXTRACTED", "message": "Extraction produced no text."}],
                    "warnings": result.get("warnings", []),
                    "visual_warnings": result.get("visual_warnings", []),
                    "visual": visual.model_dump() if visual else None,
                },
            )

        scan = await execute_scan(
            title=(title or Path(original_name).stem or "Uploaded file")[:200],
            content_text=text,
            draft_id=draft_id,
            scan_date_str=scan_date,
        )

        return UploadScanResponse(
            scan=scan,
            extraction=ExtractionSummary(
                file_name=result["file_name"],
                file_type=result.get("file_type", ""),
                content_type=result.get("content_type", ""),
                extraction_method=result.get("extraction_method", ""),
                ocr=result.get("ocr", {}),
                pages=result.get("pages", []),
                entities=result.get("entities", {}),
                visual_warnings=result.get("visual_warnings", []),
                logo_matches=result.get("logo_matches", []),
                warnings=result.get("warnings", []),
                human_review_required=bool(result.get("human_review_required", True)),
                review_reasons=result.get("review_reasons", []),
                visual=visual.model_dump() if visual else None,
            ),
        )
else:
    @router.post(
        "/upload",
        response_model=UploadScanResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Upload a file, extract its text, and scan it",
        description="Upload route (unavailable: python-multipart not installed).",
    )
    async def upload_and_scan_fallback() -> UploadScanResponse:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "File upload endpoint is unavailable. python-multipart is not installed.",
                "errors": [{"code": "MULTIPART_UNAVAILABLE", "message": "python-multipart is required for multipart/form-data"}],
                "warnings": [],
            },
        )
