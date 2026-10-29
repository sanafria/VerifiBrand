"""Publication Gate and CMS Webhook Schemas (Owned by Member 6).

Defines the Pydantic schemas for:
- CMS webhook incoming payload
- Gate evaluation decision outcome ('PASS' | 'BLOCK')
- Evidence receipts for compliance blockers
- Gate decision response with duplicate/idempotency tracking
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class GateDecision(str, Enum):
    """Publication decision outcome."""
    PASS = "PASS"
    BLOCK = "BLOCK"


class GateFindingEvidence(BaseModel):
    """Exact policy evidence citation for any compliance blocker."""
    policy_card_id: str = Field(..., description="Referenced policy card ID")
    policy_version: str = Field(..., description="Exact policy version snapshot")
    category: str = Field(..., description="Finding category (e.g., terminology, expired_offer)")
    severity: str = Field(..., description="Finding severity (e.g., blocker, high)")
    matched_text: str = Field(..., description="Exact offending text matched in draft")
    source_quote: str = Field(..., description="Verbatim quote from approved policy card")
    explanation: str = Field(..., description="Detailed violation explanation")
    suggested_fix: str = Field(default="", description="Actionable suggested fix")


class PublishGateRequest(BaseModel):
    """CMS publication gate webhook request payload."""
    event_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique CMS event or delivery identifier for idempotency",
    )
    draft_id: Optional[UUID] = Field(
        None,
        description="UUID of content draft being evaluated",
    )
    passport_id: Optional[UUID] = Field(
        None,
        description="UUID of issued Content Passport certificate (if available)",
    )
    scan_id: Optional[UUID] = Field(
        None,
        description="UUID of scan attempt (if available)",
    )
    content_text: Optional[str] = Field(
        None,
        description="Optional creative copy to verify against approved snapshot",
    )


class PublishGateResponse(BaseModel):
    """Predictable JSON response returned by the publication gate."""
    event_id: str = Field(..., description="CMS event or delivery ID matching the request")
    decision: GateDecision = Field(..., description="'PASS' or 'BLOCK'")
    status_code: int = Field(default=200, description="HTTP status code representation")
    reason: str = Field(..., description="Machine-readable code explaining the decision")
    explanation: str = Field(..., description="Clear human-readable explanation of gate decision")
    draft_id: Optional[UUID] = Field(None, description="UUID of associated content draft")
    scan_id: Optional[UUID] = Field(None, description="UUID of associated compliance scan")
    passport_id: Optional[UUID] = Field(None, description="UUID of Content Passport evaluated")
    passport_hash_verified: Optional[bool] = Field(
        None,
        description="True if canonical SHA-256 cryptographic hash verified",
    )
    findings: List[GateFindingEvidence] = Field(
        default_factory=list,
        description="Policy receipts for any blocking violations",
    )
    total_blockers: int = Field(default=0, description="Count of blocking violations detected")
    duplicate: bool = Field(default=False, description="True if returned from duplicate event store")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of evaluation",
    )
