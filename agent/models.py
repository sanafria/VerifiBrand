"""Message Schemas for the VerifiBrand Fetch.ai Agent.

Defines the typed request and response protocols for:
1. Action A: Check Creative Compliance
2. Action B: Explain Publication Blocks
3. Action C: Verify Brand Passport
"""
from typing import Any, Dict, List, Optional
from uagents import Field, Model


# ==============================================================================
# Action A: Check Creative Compliance
# ==============================================================================

class ComplianceCheckRequest(Model):
    """Request payload to check creative text against approved brand policies."""
    title: str = Field(
        ...,
        min_length=1,
        description="Title of creative post, campaign, or marketing copy",
    )
    content_text: str = Field(
        ...,
        min_length=1,
        description="Creative copy text to scan for policy violations and evidence",
    )
    draft_id: Optional[str] = Field(
        None,
        description="Optional existing content draft UUID for rescanning",
    )
    scan_date: Optional[str] = Field(
        None,
        description="Optional reference date (YYYY-MM-DD) for time-sensitive policy validation",
    )


class ComplianceCheckResponse(Model):
    """Response returned after authoritative backend scan evaluation."""
    success: bool = Field(
        ...,
        description="True if compliance evaluation completed successfully",
    )
    decision: str = Field(
        ...,
        description="Compliance outcome: 'PASS', 'FLAG', or 'BLOCK'",
    )
    status: str = Field(
        default="completed",
        description="Scan execution status ('completed', 'failed', 'pending')",
    )
    scan_id: Optional[str] = Field(
        None,
        description="UUID of recorded scan in BrandLedger backend",
    )
    draft_id: Optional[str] = Field(
        None,
        description="UUID of associated content draft in BrandLedger backend",
    )
    has_blockers: bool = Field(
        default=False,
        description="True if high-severity blocking violations were detected",
    )
    total_findings: int = Field(
        default=0,
        description="Total number of policy findings detected",
    )
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Verbatim policy receipts and evidence citations from backend engine",
    )
    summary: str = Field(
        ...,
        description="Human-readable summary of compliance findings and recommendations",
    )
    error: Optional[str] = Field(
        None,
        description="Error details if scan or connection failed",
    )


# ==============================================================================
# Action B: Explain Publication Blocks
# ==============================================================================

class ExplainBlockRequest(Model):
    """Request payload to explain why a publication event or scan was blocked."""
    event_id: Optional[str] = Field(
        None,
        description="Unique CMS publication event identifier evaluated by the publication gate",
    )
    scan_id: Optional[str] = Field(
        None,
        description="Scan UUID fallback if evaluating directly against recorded scan findings",
    )


class ExplainBlockResponse(Model):
    """Response providing simple, evidence-backed explanations for publication blocks."""
    success: bool = Field(
        ...,
        description="True if block details were successfully retrieved and explained",
    )
    decision: str = Field(
        ...,
        description="Recorded gate or scan decision: 'BLOCK', 'PASS', or 'UNKNOWN'",
    )
    event_id: Optional[str] = Field(
        None,
        description="Publication event identifier",
    )
    scan_id: Optional[str] = Field(
        None,
        description="Associated compliance scan UUID",
    )
    reason: Optional[str] = Field(
        None,
        description="Authoritative machine-readable reason code from gate evaluation",
    )
    explanation: str = Field(
        ...,
        description="Clear, non-technical explanation of the decision",
    )
    detailed_breakdown: List[str] = Field(
        default_factory=list,
        description="Itemized list of blocking violations with policy IDs, versions, and fixes",
    )
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Original evidence and citations returned by the backend",
    )
    passport_id: Optional[str] = Field(
        None,
        description="Associated Content Passport certificate UUID if evaluated",
    )
    passport_hash_verified: Optional[bool] = Field(
        None,
        description="Cryptographic SHA-256 verification status if passport was checked",
    )
    error: Optional[str] = Field(
        None,
        description="Error details if event was not found or backend service failed",
    )


# ==============================================================================
# Action C: Verify Brand Passport
# ==============================================================================

class VerifyPassportRequest(Model):
    """Request payload to inspect and cryptographically verify a Content Passport."""
    passport_id: str = Field(
        ...,
        min_length=1,
        description="UUID of the Content Passport certificate to verify",
    )


class VerifyPassportResponse(Model):
    """Response confirming Content Passport status and cryptographic authenticity."""
    success: bool = Field(
        ...,
        description="True if passport lookup and verification check completed",
    )
    passport_id: str = Field(
        ...,
        description="Content Passport certificate UUID",
    )
    verification_status: str = Field(
        ...,
        description="Outcome: 'VERIFIED', 'TAMPERED', 'REVOKED', 'NOT_FOUND', or 'ERROR'",
    )
    hash_verified: Optional[bool] = Field(
        None,
        description="True if canonical SHA-256 hash strictly matches stored signature",
    )
    passport_hash: Optional[str] = Field(
        None,
        description="Authoritative SHA-256 hash computed over canonical metadata snapshot",
    )
    status: Optional[str] = Field(
        None,
        description="Passport lifecycle state ('valid' or 'revoked')",
    )
    draft_id: Optional[str] = Field(
        None,
        description="UUID of approved content draft",
    )
    scan_id: Optional[str] = Field(
        None,
        description="UUID of associated compliance scan attempt",
    )
    review_id: Optional[str] = Field(
        None,
        description="UUID of authorized human reviewer approval record",
    )
    created_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp of passport issuance",
    )
    metadata_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Safe high-level summary of frozen passport metadata snapshot",
    )
    message: str = Field(
        ...,
        description="Clear plain-language explanation of passport verification outcome",
    )
    error: Optional[str] = Field(
        None,
        description="Error details if passport is missing, invalid, or backend unreachable",
    )
