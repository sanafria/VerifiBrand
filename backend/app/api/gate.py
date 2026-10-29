"""Publication Gate API Router for BrandLedger (Owned by Member 6).

Implements:
- POST /api/gate/publish: Authenticated CMS webhook verifying creative publication eligibility.
  * HMAC-SHA256 raw-body signature verification (X-BrandLedger-Signature).
  * Duplicate-event idempotency protection via PostgreSQL publication_events.
  * Evidence-backed PASS / BLOCK decision evaluation reusing existing services.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request, status

from backend.app.config import settings
from backend.app.schemas.gate import PublishGateRequest, PublishGateResponse
from backend.app.services.gate_service import (
    compute_payload_hash,
    evaluate_publication_eligibility,
    get_duplicate_publication_event,
    get_recorded_gate_event,
    record_publication_event,
    verify_hmac_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gate", tags=["Publication Gate"])


@router.post(
    "/publish",
    response_model=PublishGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate CMS Publication Eligibility",
    description=(
        "Authenticates incoming CMS webhooks using HMAC-SHA256, provides duplicate-event "
        "protection, and determines whether an asset is authorized for publication based on "
        "human reviewer sign-offs, zero active blockers, and cryptographic Content Passport verification."
    ),
)
async def publish_gate(
    request: Request,
    x_brandledger_signature: Optional[str] = Header(
        None,
        alias="X-BrandLedger-Signature",
        description="HMAC-SHA256 signature calculated over raw request body",
    ),
) -> PublishGateResponse:
    """Evaluate pre-publication compliance gate for CMS webhook events."""
    raw_body = await request.body()

    # 1. Enforce Authentication Header Presence
    if not x_brandledger_signature or not x_brandledger_signature.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing X-BrandLedger-Signature header.",
        )

    # 2. Retrieve Webhook Secret
    secret = settings.CMS_WEBHOOK_SECRET
    if not secret or not secret.strip():
        logger.error("CMS_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: CMS webhook secret is unset.",
        )

    # 3. Verify HMAC-SHA256 Signature (Constant-Time)
    is_valid_sig = verify_hmac_signature(
        raw_body=raw_body,
        signature_header=x_brandledger_signature,
        secret=secret,
    )
    if not is_valid_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid HMAC-SHA256 webhook signature.",
        )

    # 4. Parse Raw Body to JSON
    try:
        body_str = raw_body.decode("utf-8")
        json_data = json.loads(body_str)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed request: Invalid JSON body ({str(exc)}).",
        )

    # 5. Validate Request Schema
    try:
        payload = PublishGateRequest.model_validate(json_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Schema validation error: {str(exc)}",
        )

    # 6. Idempotency Check: Verify repeated event ID
    existing_record = await get_recorded_gate_event(payload.event_id)
    if existing_record is not None:
        existing_decision, stored_hash = existing_record
        incoming_hash = compute_payload_hash(payload)

        # Confirm that repeated event IDs cannot cause duplicate processing or return a misleading result for a different payload
        is_conflict = False
        if stored_hash and stored_hash != incoming_hash:
            is_conflict = True
        elif existing_decision.draft_id and payload.draft_id and str(existing_decision.draft_id) != str(payload.draft_id):
            is_conflict = True
        elif existing_decision.passport_id and payload.passport_id and str(existing_decision.passport_id) != str(payload.passport_id):
            is_conflict = True

        if is_conflict:
            logger.warning(
                "Conflict detected: Event ID '%s' has already been processed with a different payload.",
                payload.event_id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflict: Event ID '{payload.event_id}' has already been processed with a different payload. "
                    "Repeated event IDs cannot cause duplicate processing or return a misleading result for a different payload."
                ),
            )

        logger.info("Duplicate CMS event detected for event_id='%s'; returning cached decision.", payload.event_id)
        return existing_decision

    # 7. Authoritative Publication Eligibility Evaluation
    decision = await evaluate_publication_eligibility(payload)

    # 8. Idempotent Persistence in PostgreSQL
    incoming_hash = compute_payload_hash(payload)
    persisted_decision = await record_publication_event(
        payload.event_id, decision, payload_hash=incoming_hash
    )

    return persisted_decision


@router.get(
    "/{event_id}",
    response_model=PublishGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Recorded Publication Event",
    description="Retrieve a previously evaluated and recorded publication gate decision by event ID.",
)
async def get_gate_event(event_id: str) -> PublishGateResponse:
    """Retrieve recorded publication gate decision and evidence by event ID."""
    cached = await get_duplicate_publication_event(event_id)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Publication event '{event_id}' not found.",
        )
    return cached
