"""Visual finding schema (Member 5). Field names mirror backend/app/schemas/finding.py."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

VisualCategory = Literal[
    "visual_colour", "visual_typography", "visual_layout", "visual_clearspace"
]
Status = Literal["fail", "needs_review"]   # passing checks produce NO finding
Severity = Literal["high", "medium", "low", "info"]

REVIEW_THRESHOLD = 0.7                     # below this, never claim a fail


class VisualFinding(BaseModel):
    policy_card_id: str = Field(..., min_length=1)
    policy_version: str = Field(..., min_length=1)
    category: VisualCategory
    status: Status
    severity: Severity
    matched_text: str
    source_quote: str = Field(..., min_length=1)
    explanation: str
    suggested_fix: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    is_verified: bool = True

    @model_validator(mode="after")
    def low_confidence_means_review(self):
        if self.confidence < REVIEW_THRESHOLD:
            self.status = "needs_review"
        return self


class VisualResult(BaseModel):
    processed: bool
    image_hash: Optional[str] = None
    checks_run: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)   # checks that could not apply, with reason
    findings: List[VisualFinding] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)