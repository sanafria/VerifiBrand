"""Pydantic Contract Schemas for BrandLedger.

Shared contracts across rules engine, database, and API layers.
"""
from backend.app.schemas.finding import (
    Finding,
    FindingCategory,
    FindingSeverity,
)
from backend.app.schemas.passport import (
    PassportResponse,
    PassportStatus,
)
from backend.app.schemas.policy import (
    CardType,
    PolicyCard,
    PolicyCardBase,
    PolicyCardCreate,
    PolicyCardResponse,
    PolicyCardUpdate,
    PolicyListResponse,
    PolicyStatus,
    SeverityLevel,
    normalize_policy_card,
)
from backend.app.schemas.review import (
    ReviewCreate,
    ReviewDecision,
    ReviewResponse,
)
from backend.app.schemas.scan import (
    DraftCreate,
    DraftResponse,
    DraftStatus,
    ScanCreate,
    ScanResponse,
    ScanStatus,
)
from backend.app.schemas.system import HealthResponse, UserRole
from backend.app.schemas.gate import (
    GateDecision,
    GateFindingEvidence,
    PublishGateRequest,
    PublishGateResponse,
)
from backend.app.schemas.merkle import (
    ProofDirection,
    MerkleProofStep,
    MerkleProof,
    MerkleProofVerificationResult,
    MerkleTreeResponse,
)
from backend.app.schemas.agent_tools import (
    ComplianceDecision,
    ScanCreativeInput,
    ScanCreativeResult,
    EvidenceCitation,
    GetFindingsResult,
)

__all__ = [
    # Finding & Evidence
    "Finding",
    "FindingCategory",
    "FindingSeverity",
    # Policy Cards
    "CardType",
    "PolicyCard",
    "PolicyCardBase",
    "PolicyCardCreate",
    "PolicyCardResponse",
    "PolicyCardUpdate",
    "PolicyListResponse",
    "PolicyStatus",
    "SeverityLevel",
    "normalize_policy_card",
    # Drafts & Scans
    "DraftCreate",
    "DraftResponse",
    "DraftStatus",
    "ScanCreate",
    "ScanResponse",
    "ScanStatus",
    # Reviews & Passports
    "ReviewCreate",
    "ReviewDecision",
    "ReviewResponse",
    "PassportResponse",
    "PassportStatus",
    # System
    "HealthResponse",
    "UserRole",
    # Publication Gate (Member 6)
    "GateDecision",
    "GateFindingEvidence",
    "PublishGateRequest",
    "PublishGateResponse",
    # Merkle Ledger
    "ProofDirection",
    "MerkleProofStep",
    "MerkleProof",
    "MerkleProofVerificationResult",
    "MerkleTreeResponse",
    # Agent Tools
    "ComplianceDecision",
    "ScanCreativeInput",
    "ScanCreativeResult",
    "EvidenceCitation",
    "GetFindingsResult",
]
