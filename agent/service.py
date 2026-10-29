"""Core Service Logic for VerifiBrand Fetch.ai Agent Actions.

Orchestrates the three authoritative agent capabilities:
1. Action A: Check Creative Compliance against backend policies
2. Action B: Explain Publication Blocks using gate evidence and scan findings
3. Action C: Verify Content Passport cryptographic authenticity and status
"""
import logging
from typing import Any, Dict, List, Optional
import uuid

from agent.client import (
    BackendClient,
    BackendConnectionError,
    BackendError,
    BackendNotFoundError,
    BackendResponseError,
    BackendTimeoutError,
)
from agent.config import AgentConfig, get_agent_config
from agent.models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ExplainBlockRequest,
    ExplainBlockResponse,
    VerifyPassportRequest,
    VerifyPassportResponse,
)

logger = logging.getLogger(__name__)


class VerifiBrandAgentService:
    """Service layer executing business logic for VerifiBrand agent actions."""

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        client: Optional[BackendClient] = None,
    ):
        self.config = config or get_agent_config()
        self.client = client or BackendClient(self.config)

    # ==========================================================================
    # Action A: Check Creative Compliance
    # ==========================================================================

    async def check_creative_compliance(
        self,
        request: ComplianceCheckRequest,
    ) -> ComplianceCheckResponse:
        """Scan creative text against approved brand policies via FastAPI backend.

        Never implements a second, conflicting set of compliance rules. Delegates
        strictly to the backend rules & evidence engine.
        """
        # 1. Input Validation
        if not request.title or not request.title.strip():
            return ComplianceCheckResponse(
                success=False,
                decision="BLOCK",
                has_blockers=True,
                total_findings=0,
                summary="Validation failure: 'title' must not be empty.",
                error="Input validation error: Title is required.",
            )

        if not request.content_text or not request.content_text.strip():
            return ComplianceCheckResponse(
                success=False,
                decision="BLOCK",
                has_blockers=True,
                total_findings=0,
                summary="Validation failure: 'content_text' must not be empty.",
                error="Input validation error: Creative text is required.",
            )

        # 2. Invoke Backend Scan Service
        try:
            backend_data = await self.client.submit_scan(
                title=request.title.strip(),
                content_text=request.content_text.strip(),
                draft_id=request.draft_id,
                scan_date=request.scan_date,
            )
        except BackendConnectionError as exc:
            logger.error("Connection error during compliance check: %s", exc)
            return ComplianceCheckResponse(
                success=False,
                decision="BLOCK",
                has_blockers=True,
                total_findings=0,
                summary="Compliance check failed: BrandLedger backend service is unreachable.",
                error=str(exc),
            )
        except BackendTimeoutError as exc:
            logger.error("Timeout during compliance check: %s", exc)
            return ComplianceCheckResponse(
                success=False,
                decision="BLOCK",
                has_blockers=True,
                total_findings=0,
                summary="Compliance check timed out while waiting for backend evaluation.",
                error=str(exc),
            )
        except (BackendResponseError, BackendError) as exc:
            logger.error("Backend error during compliance check: %s", exc)
            return ComplianceCheckResponse(
                success=False,
                decision="BLOCK",
                has_blockers=True,
                total_findings=0,
                summary="Compliance check rejected: Backend reported an evaluation error.",
                error=str(exc),
            )

        # 3. Parse Backend Scan Response
        scan_id = str(backend_data.get("scan_id", ""))
        draft_id = str(backend_data.get("draft_id", ""))
        raw_status = backend_data.get("status", "completed")
        has_blockers = bool(backend_data.get("has_blockers", False))
        total_findings = int(backend_data.get("total_findings", 0))
        raw_findings = backend_data.get("findings", [])

        # 4. Determine Authoritative Compliance Decision
        if has_blockers:
            decision = "BLOCK"
            summary = (
                f"Creative compliance check detected {total_findings} finding(s), "
                f"including blocking policy violations. Content cannot be published without revisions."
            )
        elif total_findings > 0:
            decision = "FLAG"
            summary = (
                f"Creative compliance check detected {total_findings} advisory finding(s). "
                f"No blockers were found, but review is recommended."
            )
        else:
            decision = "PASS"
            summary = (
                "Creative compliance check passed with zero violations. "
                "Content conforms to all approved brand policies."
            )

        # 5. Format Verbatim Policy Receipts
        formatted_findings: List[Dict[str, Any]] = []
        for finding in raw_findings:
            if isinstance(finding, dict):
                formatted_findings.append({
                    "policy_card_id": finding.get("policy_card_id", "UNKNOWN"),
                    "policy_version": finding.get("policy_version", "unknown"),
                    "category": finding.get("category", "general"),
                    "severity": finding.get("severity", "info"),
                    "matched_text": finding.get("matched_text", ""),
                    "source_quote": finding.get("source_quote", ""),
                    "explanation": finding.get("explanation", ""),
                    "suggested_fix": finding.get("suggested_fix", ""),
                    "confidence": float(finding.get("confidence", 1.0)),
                    "is_verified": bool(finding.get("is_verified", True)),
                })

        return ComplianceCheckResponse(
            success=True,
            decision=decision,
            status=raw_status,
            scan_id=scan_id if scan_id else None,
            draft_id=draft_id if draft_id else None,
            has_blockers=has_blockers,
            total_findings=total_findings,
            findings=formatted_findings,
            summary=summary,
        )

    # ==========================================================================
    # Action B: Explain Publication Blocks
    # ==========================================================================

    async def explain_publication_blocks(
        self,
        request: ExplainBlockRequest,
    ) -> ExplainBlockResponse:
        """Retrieve recorded gate decision or scan findings and explain in simple language.

        Never fabricates findings or claims that a block occurred if it did not.
        """
        # 1. Input Validation
        event_id = request.event_id.strip() if request.event_id else None
        scan_id = request.scan_id.strip() if request.scan_id else None

        if not event_id and not scan_id:
            return ExplainBlockResponse(
                success=False,
                decision="UNKNOWN",
                explanation="Validation error: Please provide either a publication 'event_id' or a 'scan_id'.",
                error="Missing required identifier: event_id or scan_id required.",
            )

        # 2. Path A: Evaluate Against Recorded Publication Gate Event
        if event_id:
            try:
                gate_data = await self.client.get_gate_event(event_id)
            except BackendNotFoundError:
                return ExplainBlockResponse(
                    success=False,
                    decision="UNKNOWN",
                    event_id=event_id,
                    explanation=f"Publication event '{event_id}' was not found in the gate event registry.",
                    error=f"Publication event '{event_id}' not found.",
                )
            except (BackendConnectionError, BackendTimeoutError, BackendError) as exc:
                logger.error("Failed to fetch publication event %s: %s", event_id, exc)
                return ExplainBlockResponse(
                    success=False,
                    decision="UNKNOWN",
                    event_id=event_id,
                    explanation="Could not retrieve publication event details due to backend communication error.",
                    error=str(exc),
                )

            return self._build_gate_explanation(event_id, gate_data)

        # 3. Path B: Fallback to Scan Findings
        try:
            scan_data = await self.client.get_scan(scan_id)  # type: ignore[arg-type]
        except BackendNotFoundError:
            return ExplainBlockResponse(
                success=False,
                decision="UNKNOWN",
                scan_id=scan_id,
                explanation=f"Scan record '{scan_id}' was not found in the compliance database.",
                error=f"Scan '{scan_id}' not found.",
            )
        except (BackendConnectionError, BackendTimeoutError, BackendError) as exc:
            return ExplainBlockResponse(
                success=False,
                decision="UNKNOWN",
                scan_id=scan_id,
                explanation="Could not retrieve scan details due to backend communication error.",
                error=str(exc),
            )

        return self._build_scan_explanation(scan_id, scan_data)  # type: ignore[arg-type]

    def _build_gate_explanation(
        self,
        event_id: str,
        gate_data: Dict[str, Any],
    ) -> ExplainBlockResponse:
        """Translate gate response into clear, non-technical explanation with policy citations."""
        decision = str(gate_data.get("decision", "BLOCK")).upper()
        reason = str(gate_data.get("reason", "UNKNOWN"))
        backend_explanation = str(gate_data.get("explanation", ""))
        raw_findings = gate_data.get("findings", [])
        passport_id = gate_data.get("passport_id")
        passport_hash_verified = gate_data.get("passport_hash_verified")
        scan_id = gate_data.get("scan_id")

        # Case 1: Event Actually Passed (Never claim a block occurred!)
        if decision == "PASS":
            breakdown = [
                f"Gate Evaluation: APPROVED (PASS)",
                f"Decision Code: {reason}",
                f"Backend Details: {backend_explanation}",
            ]
            if passport_hash_verified is True:
                breakdown.append("Cryptographic Passport Verification: SHA-256 hash valid and verified.")

            return ExplainBlockResponse(
                success=True,
                decision="PASS",
                event_id=event_id,
                scan_id=str(scan_id) if scan_id else None,
                passport_id=str(passport_id) if passport_id else None,
                passport_hash_verified=passport_hash_verified,
                reason=reason,
                explanation=(
                    f"No publication block occurred for event '{event_id}'. "
                    f"The publication gate approved this event for release."
                ),
                detailed_breakdown=breakdown,
                findings=[],
            )

        # Case 2: Event Was Blocked
        friendly_reasons = {
            "BLOCK_COMPLIANCE_FINDINGS": "Publication blocked due to active compliance policy violations in the creative copy.",
            "BLOCK_NO_PASSPORT": "Publication blocked because no Content Passport was provided or found for this asset.",
            "BLOCK_PASSPORT_TAMPERED": "Publication blocked due to cryptographic integrity alert: Content Passport SHA-256 hash mismatch.",
            "BLOCK_DRAFT_NOT_APPROVED": "Publication blocked because the draft has not received required human reviewer sign-off.",
            "BLOCK_DRAFT_REJECTED": "Publication blocked because this draft was explicitly rejected by a brand reviewer.",
            "BLOCK_CONTENT_MISMATCH": "Publication blocked because published copy does not match the approved draft snapshot.",
            "BLOCK_DRAFT_NOT_FOUND": "Publication blocked because the referenced content draft does not exist.",
            "BLOCK_PASSPORT_NOT_FOUND": "Publication blocked because the referenced Content Passport certificate does not exist.",
        }

        main_explanation = friendly_reasons.get(
            reason,
            backend_explanation or f"Publication blocked under reason code '{reason}'."
        )

        breakdown: List[str] = [
            f"Primary Block Reason: {main_explanation}",
            f"Machine Reason Code: {reason}",
        ]

        if passport_hash_verified is False:
            breakdown.append(
                "Cryptographic Integrity Alert: Content Passport failed SHA-256 signature verification. "
                "The certificate snapshot may have been tampered with or modified."
            )

        formatted_findings: List[Dict[str, Any]] = []
        for idx, f in enumerate(raw_findings, start=1):
            if isinstance(f, dict):
                p_id = f.get("policy_card_id", "Unknown Policy")
                p_ver = f.get("policy_version", "1.0.0")
                cat = f.get("category", "violation")
                matched = f.get("matched_text", "")
                quote = f.get("source_quote", "")
                expl = f.get("explanation", "")
                fix = f.get("suggested_fix", "")

                formatted_findings.append({
                    "policy_card_id": p_id,
                    "policy_version": p_ver,
                    "category": cat,
                    "severity": f.get("severity", "blocker"),
                    "matched_text": matched,
                    "source_quote": quote,
                    "explanation": expl,
                    "suggested_fix": fix,
                })

                item_text = (
                    f"Violation #{idx} [Policy {p_id} v{p_ver}] ({cat}): "
                    f"Offending text: \"{matched}\". "
                    f"Approved policy requirement: \"{quote}\". "
                    f"Explanation: {expl}. "
                    f"Actionable fix: {fix or 'Update draft copy to adhere to policy.'}"
                )
                breakdown.append(item_text)

        return ExplainBlockResponse(
            success=True,
            decision="BLOCK",
            event_id=event_id,
            scan_id=str(scan_id) if scan_id else None,
            passport_id=str(passport_id) if passport_id else None,
            passport_hash_verified=passport_hash_verified,
            reason=reason,
            explanation=main_explanation,
            detailed_breakdown=breakdown,
            findings=formatted_findings,
        )

    def _build_scan_explanation(
        self,
        scan_id: str,
        scan_data: Dict[str, Any],
    ) -> ExplainBlockResponse:
        """Translate scan attempt data into an explanation response."""
        has_blockers = bool(scan_data.get("has_blockers", False))
        raw_findings = scan_data.get("findings", [])
        total = int(scan_data.get("total_findings", 0))

        if not has_blockers and total == 0:
            return ExplainBlockResponse(
                success=True,
                decision="PASS",
                scan_id=scan_id,
                reason="SCAN_COMPLIANT_ZERO_FINDINGS",
                explanation=f"Scan '{scan_id}' contains zero policy findings and is eligible for approval.",
                detailed_breakdown=[f"Scan ID: {scan_id}", "Status: COMPLIANT (zero violations detected)."],
                findings=[],
            )

        decision = "BLOCK" if has_blockers else "FLAG"
        explanation = (
            f"Scan '{scan_id}' has {total} policy finding(s), "
            f"{'including active blockers preventing publication' if has_blockers else 'advisory warnings'}."
        )

        breakdown: List[str] = [
            f"Scan Evaluation: {'BLOCK' if has_blockers else 'FLAG'}",
            f"Total Findings: {total}",
        ]

        formatted_findings: List[Dict[str, Any]] = []
        for idx, f in enumerate(raw_findings, start=1):
            if isinstance(f, dict):
                p_id = f.get("policy_card_id", "Unknown Policy")
                p_ver = f.get("policy_version", "1.0.0")
                matched = f.get("matched_text", "")
                quote = f.get("source_quote", "")
                expl = f.get("explanation", "")
                fix = f.get("suggested_fix", "")

                formatted_findings.append({
                    "policy_card_id": p_id,
                    "policy_version": p_ver,
                    "category": f.get("category", "general"),
                    "severity": f.get("severity", "info"),
                    "matched_text": matched,
                    "source_quote": quote,
                    "explanation": expl,
                    "suggested_fix": fix,
                })

                breakdown.append(
                    f"Finding #{idx} [Policy {p_id} v{p_ver}]: "
                    f"Text: \"{matched}\" | Rule: \"{quote}\" | Fix: {fix or expl}"
                )

        return ExplainBlockResponse(
            success=True,
            decision=decision,
            scan_id=scan_id,
            reason="BLOCK_COMPLIANCE_FINDINGS" if has_blockers else "FLAG_COMPLIANCE_WARNINGS",
            explanation=explanation,
            detailed_breakdown=breakdown,
            findings=formatted_findings,
        )

    # ==========================================================================
    # Action C: Verify Brand Passport
    # ==========================================================================

    async def verify_brand_passport(
        self,
        request: VerifyPassportRequest,
    ) -> VerifyPassportResponse:
        """Inspect and cryptographically verify a Content Passport digital certificate.

        Clearly distinguishes:
        - VERIFIED (Valid status and canonical SHA-256 hash match)
        - TAMPERED (Hash mismatch indicating corrupted or modified record)
        - REVOKED (Revoked by governance)
        - NOT_FOUND (Nonexistent passport ID)
        - ERROR (Malformed UUID or backend communication failure)
        """
        raw_id = request.passport_id.strip()

        # 1. Input Validation: Validate UUID format
        try:
            uuid_obj = uuid.UUID(raw_id)
            canonical_id = str(uuid_obj)
        except (ValueError, AttributeError):
            return VerifyPassportResponse(
                success=False,
                passport_id=raw_id,
                verification_status="ERROR",
                message=f"Invalid passport ID: '{raw_id}' is not a valid UUID.",
                error="Invalid UUID format.",
            )

        # 2. Invoke Backend Passport Verification API
        try:
            data = await self.client.get_passport(canonical_id)
        except BackendNotFoundError:
            return VerifyPassportResponse(
                success=False,
                passport_id=canonical_id,
                verification_status="NOT_FOUND",
                message=f"Content Passport '{canonical_id}' was not found in the BrandLedger registry.",
                error="Passport not found.",
            )
        except BackendConnectionError as exc:
            return VerifyPassportResponse(
                success=False,
                passport_id=canonical_id,
                verification_status="ERROR",
                message="Cannot verify passport: BrandLedger backend service is unreachable.",
                error=str(exc),
            )
        except BackendTimeoutError as exc:
            return VerifyPassportResponse(
                success=False,
                passport_id=canonical_id,
                verification_status="ERROR",
                message="Cannot verify passport: Backend request timed out.",
                error=str(exc),
            )
        except (BackendResponseError, BackendError) as exc:
            return VerifyPassportResponse(
                success=False,
                passport_id=canonical_id,
                verification_status="ERROR",
                message="Cannot verify passport: Backend returned an error.",
                error=str(exc),
            )

        # 3. Interpret Authoritative Backend Verification
        status = str(data.get("status", "valid")).lower()
        hash_verified = bool(data.get("hash_verified", False))
        passport_hash = str(data.get("passport_hash", ""))
        draft_id = str(data.get("draft_id", ""))
        scan_id = str(data.get("scan_id", ""))
        review_id = str(data.get("review_id", ""))
        created_at = str(data.get("created_at", ""))
        snapshot = data.get("metadata_snapshot", {})

        # Build safe metadata summary
        metadata_summary: Dict[str, Any] = {}
        if isinstance(snapshot, dict):
            metadata_summary = {
                "reviewer_id": snapshot.get("reviewer_id"),
                "draft_title": snapshot.get("draft_title"),
                "total_findings": snapshot.get("total_findings", 0),
                "policy_versions": list(snapshot.get("policy_versions", {}).keys()),
            }

        # 4. Strict Classification
        if not hash_verified:
            verification_status = "TAMPERED"
            message = (
                f"CRITICAL INTEGRITY FAILURE: Content Passport '{canonical_id}' has been TAMPERED with. "
                f"The stored cryptographic hash ({passport_hash[:16]}...) does NOT match the recomputed "
                f"canonical snapshot hash. This asset must NOT be published."
            )
        elif status == "revoked":
            verification_status = "REVOKED"
            message = (
                f"Content Passport '{canonical_id}' is REVOKED by brand governance. "
                f"Cryptographic hash is verified, but certificate permissions have been rescinded."
            )
        elif status == "valid" and hash_verified:
            verification_status = "VERIFIED"
            message = (
                f"Content Passport '{canonical_id}' is VERIFIED and cryptographically authentic. "
                f"Canonical SHA-256 fingerprint matches the frozen audit snapshot."
            )
        else:
            verification_status = "UNKNOWN"
            message = f"Content Passport state is unconfirmed: status='{status}', hash_verified={hash_verified}."

        return VerifyPassportResponse(
            success=True,
            passport_id=canonical_id,
            verification_status=verification_status,
            hash_verified=hash_verified,
            passport_hash=passport_hash,
            status=status,
            draft_id=draft_id if draft_id else None,
            scan_id=scan_id if scan_id else None,
            review_id=review_id if review_id else None,
            created_at=created_at if created_at else None,
            metadata_summary=metadata_summary,
            message=message,
        )
