"""BrandLedger FastAPI Application Entry Point.

Maintained as part of the shared API layer owned by Zoya, integrating
CORS, configuration, shared schemas, database pooling, Policy Card APIs,
and Zynab's scan_draft service.
"""

from contextlib import asynccontextmanager
from typing import Any
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.api.passports import router as passports_router
from backend.app.api.policies import router as policies_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.scans import router as scans_router
from backend.app.api.uploads import router as uploads_router
from backend.app.api.merkle import router as merkle_router
from backend.app.api.agent_tools import router as agent_tools_router
from backend.app.config import settings
from backend.app.db import db_manager
from backend.app.schemas.finding import Finding
from backend.app.services.policy_engine import scan_draft


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: connect to database on startup, disconnect on shutdown."""
    try:
        await db_manager.connect()
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
app.include_router(merkle_router, prefix="/api")
app.include_router(agent_tools_router, prefix="/api")



class ScanDraftRequest(BaseModel):
    """Scan request model matching the scan workflow contract."""
    content_text: str = Field(..., description="Draft marketing content to be scanned")
    policy_cards: list[dict[str, Any]] = Field(..., description="Approved policy cards")
    scan_date: str = Field(..., description="Reference scan date string (YYYY-MM-DD)")


class ScanDraftResponse(BaseModel):
    """Scan response model returning structured, validated findings."""
    total_findings: int
    findings: list[Finding]


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "brandledger-api"}


@app.post("/api/scan", response_model=ScanDraftResponse)
def api_scan_draft(request: ScanDraftRequest) -> ScanDraftResponse:
    """Scan draft endpoint integrating the deterministic policy engine service."""
    try:
        findings = scan_draft(
            content_text=request.content_text,
            policy_cards=request.policy_cards,
            scan_date=request.scan_date,
        )
        return ScanDraftResponse(
            total_findings=len(findings),
            findings=[Finding(**f) for f in findings],
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scan error: {str(exc)}")
