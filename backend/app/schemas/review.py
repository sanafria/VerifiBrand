"""Review Workflow Schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    """Human review decision."""
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewCreate(BaseModel):
    """Human reviewer decision payload."""
    draft_id: UUID = Field(..., description="UUID of draft being reviewed")
    scan_id: UUID = Field(..., description="UUID of completed scan evaluated")
    decision: ReviewDecision = Field(..., description="'approved' or 'rejected'")
    comment: Optional[str] = Field(default="", description="Reviewer explanation or verification note")
    approval_type: Optional[str] = Field(default="standard", description="'standard' or 'visual_only'")
    visual_override_reason: Optional[str] = Field(default=None, description="Mandatory reason for visual-only review")


class ReviewResponse(BaseModel):
    """Review decision record."""
    id: UUID
    draft_id: UUID
    scan_id: UUID
    reviewer_id: str
    reviewer_name: str
    decision: ReviewDecision
    comment: str
    passport_id: Optional[UUID] = None
    sha256: Optional[str] = None
    approval_type: Optional[str] = None
    decision_limitations: Optional[str] = None
    created_at: datetime
