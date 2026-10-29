"""BrandLedger Services Package."""

from backend.app.services.rule_checks import (
    check_terminology,
    check_expired_offers,
    check_factual_accuracy,
    check_unsupported_claims,
)
from backend.app.services.evidence_verifier import (
    verify_finding,
    verify_source_quotation,
    verify_policy_card_and_version,
    filter_and_verify_findings,
    verify_findings_with_report,
    VerificationDetail,
    EvidenceVerificationReport,
)

from backend.app.services.ai_checks import (
    is_ai_enabled,
    run_optional_ai_checks,
)
from backend.app.services.policy_engine import scan_draft
from backend.app.services.gate_service import (
    compute_payload_hash,
    ensure_gate_schema,
    evaluate_publication_eligibility,
    get_duplicate_publication_event,
    get_recorded_gate_event,
    record_publication_event,
    verify_hmac_signature,
)
from backend.app.services.merkle_ledger import (
    MerkleTree,
    hash_leaf,
    hash_internal_nodes,
    verify_merkle_proof,
    build_merkle_tree_from_passports,
    get_database_passport_ledger,
)
from backend.app.services.agent_tools import (
    scan_creative,
    get_findings,
    evaluate_compliance_decision,
)

__all__ = [
    "check_terminology",
    "check_expired_offers",
    "check_factual_accuracy",
    "check_unsupported_claims",
    "verify_finding",
    "verify_source_quotation",
    "verify_policy_card_and_version",
    "filter_and_verify_findings",
    "verify_findings_with_report",
    "VerificationDetail",
    "EvidenceVerificationReport",
    "is_ai_enabled",
    "run_optional_ai_checks",
    "scan_draft",
    # Gate Service (Member 6)
    "compute_payload_hash",
    "ensure_gate_schema",
    "evaluate_publication_eligibility",
    "get_duplicate_publication_event",
    "get_recorded_gate_event",
    "record_publication_event",
    "verify_hmac_signature",
    # Merkle Ledger (Member 4)
    "MerkleTree",
    "hash_leaf",
    "hash_internal_nodes",
    "verify_merkle_proof",
    "build_merkle_tree_from_passports",
    "get_database_passport_ledger",
    # Agent Tools (Member 4)
    "scan_creative",
    "get_findings",
    "evaluate_compliance_decision",
]
