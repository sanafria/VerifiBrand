"""Tests for POST /api/scans/upload (Mahadevi).

Uses the REAL extraction module on the sample dataset, but replaces Zoya's
``execute_scan`` with a fake so no PostgreSQL database is required.
Run:  python -m pytest backend/tests/test_api_uploads.py -v
"""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import uploads
from backend.app.schemas.scan import ScanResponse, ScanStatus
from backend.extraction_module.brandledger_extraction.ocr_service import tesseract_available

DATA = Path(__file__).resolve().parent.parent / "extraction_module" / "dataset"


@pytest.fixture()
def client_and_calls(monkeypatch):
    calls = []

    async def fake_execute_scan(title, content_text, draft_id=None, scan_date_str=None):
        calls.append({"title": title, "content_text": content_text})
        return ScanResponse(
            scan_id=uuid4(), draft_id=uuid4(), status=ScanStatus.COMPLETED,
            findings=[], total_findings=0, has_blockers=False, created_at=datetime.now(),
        )

    monkeypatch.setattr(uploads, "execute_scan", fake_execute_scan)
    app = FastAPI()
    app.include_router(uploads.router, prefix="/api")
    return TestClient(app), calls


def _post(client, rel_path, content_type):
    path = DATA / rel_path
    with open(path, "rb") as fh:
        return client.post("/api/scans/upload", files={"file": (path.name, fh, content_type)})


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract OCR binary not installed on host system")
def test_image_is_extracted_then_scanned(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "images/img_clear_offer.png", "image/png")
    assert r.status_code == 201, r.text
    assert len(calls) == 1 and "SPRING SALE" in calls[0]["content_text"]
    body = r.json()
    assert body["extraction"]["extraction_method"] == "ocr"
    assert body["extraction"]["file_name"] == "img_clear_offer.png"
    assert body["scan"]["status"] == "completed"


def test_text_layer_pdf_is_scanned(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "pdfs/pdf_selectable_text.pdf", "application/pdf")
    assert r.status_code == 201, r.text
    assert "SUMMER OFFER" in calls[0]["content_text"]


@pytest.mark.parametrize("rel_path,code", [
    ("edge_cases/corrupt.png", "CORRUPT_FILE"),
    ("edge_cases/empty.png", "EMPTY_FILE"),
    ("edge_cases/unsupported.docx", "UNSUPPORTED_FORMAT"),
    ("edge_cases/corrupt.pdf", "CORRUPT_FILE"),
])
def test_bad_files_are_rejected_and_never_scanned(client_and_calls, rel_path, code):
    client, calls = client_and_calls
    r = _post(client, rel_path, "application/octet-stream")
    assert r.status_code == 422
    assert code in {e["code"] for e in r.json()["detail"]["errors"]}
    assert calls == []          # a failed read must never reach the scanner


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract OCR binary not installed on host system")
def test_blank_image_is_not_treated_as_clean(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "images/img_blank.png", "image/png")
    assert r.status_code == 422
    assert "NO_TEXT_EXTRACTED" in {e["code"] for e in r.json()["detail"]["errors"]}
    assert calls == []


VISUAL_KEYS = {"processed", "checks_run", "skipped", "findings", "errors"}


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract OCR binary not installed on host system")
def test_image_upload_returns_visual_block(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "images/img_clear_offer.png", "image/png")
    assert r.status_code == 201, r.text
    visual = r.json()["extraction"]["visual"]
    assert visual is not None
    assert VISUAL_KEYS <= set(visual)
    assert visual["processed"] is True


def test_pdf_upload_returns_visual_block(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "pdfs/pdf_selectable_text.pdf", "application/pdf")
    assert r.status_code == 201, r.text
    visual = r.json()["extraction"]["visual"]
    assert visual is not None and VISUAL_KEYS <= set(visual)


def test_txt_upload_skips_visual_checks(client_and_calls):
    client, calls = client_and_calls
    r = client.post(
        "/api/scans/upload",
        files={"file": ("note.txt", b"Join our members today", "text/plain")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["extraction"]["visual"] is None


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract OCR binary not installed on host system")
def test_no_text_422_still_carries_visual_results(client_and_calls):
    client, calls = client_and_calls
    r = _post(client, "images/img_blank.png", "image/png")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "NO_TEXT_EXTRACTED" in {e["code"] for e in detail["errors"]}
    assert detail["visual"] is not None
    assert VISUAL_KEYS <= set(detail["visual"])
    assert calls == []          # still never scanned
