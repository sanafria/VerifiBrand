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
from backend.app.schemas.policy import PolicyCardResponse
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


# ---------------------------------------------------------------------------
# Member 2: Policy & Passport Agent Tools Schemas
# ---------------------------------------------------------------------------

class GetApprovedPoliciesResult(BaseModel):
    """Machine-readable output of get_approved_policies agent tool."""
    total_policies: int = Field(..., description="Count of approved active policies")
    policies: List[PolicyCardResponse] = Field(default_factory=list, description="List of active policy cards")


class PolicyDetailsResult(BaseModel):
    """Machine-readable output of get_policy_details agent tool."""
    found: bool = Field(..., description="True if policy card was found")
    policy_id: Optional[str] = Field(None, description="Queried policy ID or key")
    policy_key: Optional[str] = Field(None, description="Stable human-readable policy key")
    version: Optional[str] = Field(None, description="Current or requested version string")
    requested_version: Optional[str] = Field(None, description="Specific historical version requested, if any")
    is_historical: bool = Field(default=False, description="True if this is a historical version snapshot")
    policy: Optional[PolicyCardResponse] = Field(None, description="Full policy card details")
    error: Optional[str] = Field(None, description="Error message if policy was not found")


class ContentPassportResult(BaseModel):
    """Machine-readable output of get_passport agent tool."""
    found: bool = Field(..., description="True if Content Passport was found")
    id: Optional[str] = Field(None, description="Content Passport UUID")
    draft_id: Optional[str] = Field(None, description="Associated draft UUID")
    scan_id: Optional[str] = Field(None, description="Associated scan UUID")
    review_id: Optional[str] = Field(None, description="Associated human review UUID")
    passport_hash: Optional[str] = Field(None, description="Stored SHA-256 hash of canonical snapshot")
    status: Optional[str] = Field(None, description="Passport status (valid, revoked)")
    metadata_snapshot: Optional[Dict[str, Any]] = Field(None, description="Frozen canonical metadata snapshot")
    applied_policy_versions: List[Dict[str, Any]] = Field(default_factory=list, description="Policies and versions frozen in passport")
    hash_verified: bool = Field(default=False, description="True if stored hash matches recomputed canonical hash")
    created_at: Optional[str] = Field(None, description="ISO timestamp of passport issuance")
    error: Optional[str] = Field(None, description="Error message if passport was not found")


class VerifyPassportInput(BaseModel):
    """Input payload to verify Content Passport hash integrity."""
    passport_id: Optional[str] = Field(None, description="Target Content Passport UUID to retrieve and verify")
    passport_hash: Optional[str] = Field(None, description="Expected SHA-256 hash if verifying direct payload")
    metadata_snapshot: Optional[Dict[str, Any]] = Field(None, description="Raw metadata snapshot if verifying direct payload")


class VerifyPassportResult(BaseModel):
    """Machine-readable output of verify_passport agent tool."""
    passport_id: Optional[str] = Field(None, description="Target Content Passport UUID if applicable")
    status: str = Field(..., description="Verification verdict: VALID, TAMPERED, or NOT_FOUND")
    hash_verified: bool = Field(..., description="True if stored hash strictly equals computed hash")
    stored_hash: Optional[str] = Field(None, description="Stored SHA-256 hash")
    computed_hash: Optional[str] = Field(None, description="Cryptographically computed canonical SHA-256 hash")
    explanation: str = Field(..., description="Authoritative verification result explanation")


class ExplainFindingInput(BaseModel):
    """Input payload to explain a compliance finding."""
    finding_id: Optional[str] = Field(None, description="UUID of finding to explain")
    scan_id: Optional[str] = Field(None, description="Scan ID containing finding")
    finding_index: Optional[int] = Field(None, description="0-indexed position of finding in scan")
    finding: Optional[Finding] = Field(None, description="Direct finding object if scan not persisted")


class ExplainFindingResult(BaseModel):
    """Machine-readable output of explain_finding agent tool."""
    found: bool = Field(default=True, description="True if finding and cited policy card exist")
    finding_id: Optional[str] = Field(None, description="Target finding ID")
    scan_id: Optional[str] = Field(None, description="Associated scan ID")
    category: Optional[str] = Field(None, description="Finding category")
    severity: Optional[str] = Field(None, description="Finding severity level")
    matched_text: Optional[str] = Field(None, description="The non-compliant text flagged in the draft")
    policy_card_id: Optional[str] = Field(None, description="Cited policy card UUID or key")
    policy_version: Optional[str] = Field(None, description="Cited policy version")
    verbatim_source_quote: Optional[str] = Field(None, description="Authoritative source quote from policy")
    evidence_provenance: str = Field(..., description="Provenance state: VERIFIED, UNVERIFIED, or HUMAN_REVIEW_REQUIRED")
    is_verified: bool = Field(..., description="True if quote was confirmed verbatim against policy text")
    remediation_guidance: str = Field(..., description="Actionable remediation guidance for compliance")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context or rule breakdown")
    error: Optional[str] = Field(None, description="Error message if finding or policy could not be found")

