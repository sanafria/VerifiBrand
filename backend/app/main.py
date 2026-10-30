"""FastAPI Main Entrypoint for BrandLedger.

Connects PostgreSQL database, configures CORS, and registers API routers.
"""
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.api.gate import router as gate_router
from backend.app.api.passports import router as passports_router
from backend.app.api.policies import router as policies_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.scans import router as scans_router
from backend.app.api.uploads import OcrResponse, extract_ocr_endpoint
from backend.app.api.uploads import router as uploads_router
from backend.app.api.merkle import router as merkle_router
from backend.app.api.agent_tools import router as agent_tools_router
from backend.app.config import settings
from backend.app.db import db_manager
from backend.app.schemas.finding import Finding
from backend.app.services.gate_service import ensure_gate_schema
from backend.app.services.policy_engine import scan_draft


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: connect to database on startup, disconnect on shutdown."""
    try:
        await db_manager.connect()
        await ensure_gate_schema()
    except Exception:
        # If DB is temporarily unavailable, allow API to start for health check
        pass
    yield
    await db_manager.disconnect()


app = FastAPI(
    title="BrandLedger API",
    description="Compliance, Rules Engine, and Policy Verification API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for Next.js frontend (Sana and Nimra)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(policies_router, prefix="/api")
app.include_router(scans_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(passports_router, prefix="/api")
app.include_router(gate_router, prefix="/api")
app.include_router(merkle_router, prefix="/api")
app.include_router(agent_tools_router, prefix="/api")


class ScanDraftRequest(BaseModel):
    content_text: str = Field(..., description="Draft text to scan")
    policy_cards: list[dict] = Field(..., description="Policy cards to validate against")
    scan_date: str = Field(..., description="Reference date YYYY-MM-DD")


class ScanDraftResponse(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    total_findings: int = Field(default=0)


@app.post("/scan-draft", response_model=ScanDraftResponse)
@app.post("/api/scan", response_model=ScanDraftResponse)
async def scan_draft_endpoint(payload: ScanDraftRequest):
    """Scan draft text against policy cards and return verified findings."""
    try:
        datetime.strptime(payload.scan_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan_date format. Expected YYYY-MM-DD.")

    try:
        raw_findings = scan_draft(
            content_text=payload.content_text,
            policy_cards=payload.policy_cards,
            scan_date=payload.scan_date,
        )
        validated = [Finding(**f) for f in raw_findings]
        return ScanDraftResponse(findings=validated, total_findings=len(validated))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/ocr", response_model=OcrResponse)
@app.post("/ocr", response_model=OcrResponse)
async def direct_ocr_endpoint(file: UploadFile = File(...)):
    """Direct OCR endpoint for image copy extraction."""
    return await extract_ocr_endpoint(file)


@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "brandledger-api"}
