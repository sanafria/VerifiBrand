"""Agent Tools Schemas and Compliance Decision Enums for BrandLedger.

Defines the contract for agent tools:
- scan_creative
- get_findings
- verify_merkle_proof
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.app.schemas.finding import Finding
from backend.app.schemas.scan import ScanStatus


class ComplianceDecision(str, Enum):
    """Authoritative compliance decision enum matching Phase 6 specifications.

    - PASS: The scan completed and no blocking compliance violations were identified.
    - BLOCK: One or more blocking violations were identified.
    - HUMAN_REVIEW: A decision cannot safely be made automatically because evidence
      is missing, ambiguous, inconsistent, or requires human judgment.
    """
    PASS = "PASS"
    BLOCK = "BLOCK"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ScanCreativeInput(BaseModel):
    """Input payload for scan_creative agent tool."""
    title: Optional[str] = Field(default="Creative Submission", description="Title or campaign name")
    content_text: str = Field(..., min_length=1, description="Marketing copy or creative text to scan")
    draft_id: Optional[UUID] = Field(None, description="Optional existing content draft ID")
    scan_date: Optional[str] = Field(None, description="Optional explicit scan reference date (YYYY-MM-DD)")
    policy_cards: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional list of policy cards. If omitted, loads active policies from database or defaults.",
    )


class EvidenceCitation(BaseModel):
    """Machine-readable policy citation linking finding to authoritative evidence."""
    policy_card_id: str
    policy_version: str
    source_quote: str
    category: str
    severity: str
    matched_text: str


class ScanCreativeResult(BaseModel):
    """Machine-readable output of scan_creative agent tool."""
    status: ScanStatus = Field(..., description="Scan status (completed or failed)")
    decision: ComplianceDecision = Field(..., description="Authoritative compliance decision (PASS, BLOCK, HUMAN_REVIEW)")
    decision_reason: str = Field(..., description="Explanation for the compliance decision")
    total_findings: int = Field(default=0, description="Total count of findings detected")
    blockers_count: int = Field(default=0, description="Count of blocking or high severity findings")
    has_blockers: bool = Field(default=False, description="True if any blocker or high severity finding exists")
    findings: List[Finding] = Field(default_factory=list, description="Validated, evidence-backed findings")
    evidence_citations: List[EvidenceCitation] = Field(default_factory=list, description="Traceable evidence receipts")
    draft_id: Optional[UUID] = Field(None, description="Associated draft ID if persisted")
    scan_id: Optional[UUID] = Field(None, description="Associated scan ID if persisted")


class GetFindingsResult(BaseModel):
    """Machine-readable output of get_findings agent tool."""
    found: bool = Field(..., description="True if findings for the target scan/draft were found")
    scan_id: Optional[str] = Field(None, description="The queried scan ID")
    draft_id: Optional[str] = Field(None, description="The queried draft ID")
    status: Optional[str] = Field(None, description="Scan execution status if known")
    total_findings: int = Field(default=0, description="Count of findings")
    findings: List[Finding] = Field(default_factory=list, description="List of structured findings")
    error: Optional[str] = Field(None, description="Error message if not found or lookup failed")
