"""Review and Content Passport Service for BrandLedger (Owned by Zoya).

Implements:
- Validation of scan completion and draft ownership.
- Human review decision persistence.
- Content draft status updates.
- Deterministic canonical snapshot assembly and SHA-256 hashing.
- Immutable Content Passport creation on approval.
- Passport retrieval with cryptographic hash verification.
"""
from datetime import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncpg
from fastapi import HTTPException, status

from backend.app.db import db_manager
from backend.app.schemas.passport import PassportResponse, PassportStatus
from backend.app.schemas.review import ReviewCreate, ReviewDecision, ReviewResponse

logger = logging.getLogger(__name__)


def compute_canonical_passport_hash(snapshot: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash over canonically sorted JSON representation.

    Rules for canonical representation:
    - Keys sorted alphabetically (sort_keys=True)
    - Compact separators without extra whitespace (',', ':')
    - UTF-8 encoding
    """
    canonical_json = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


async def submit_review_decision(
    payload: ReviewCreate,
    reviewer_id: str,
    reviewer_name: str,
) -> ReviewResponse:
    """Submit a human review decision and generate a Content Passport if approved.

    Executes atomically within a single database transaction:
    1. Locks the scan row with FOR UPDATE OF s to serialize concurrent reviews.
    2. Validates scan existence, draft relationship, and completed status.
    3. Checks for existing reviews on the locked scan.
    4. Persists the review decision in the reviews table.
    5. Updates the content_drafts lifecycle status.
    6. For approved reviews, loads findings, builds canonical metadata, and inserts passport.
    7. All writes commit together; any failure rolls back all changes automatically.
    """
    try:
        async with db_manager.transaction() as conn:
            # 1. Validate that the scan exists and acquire an exclusive row lock on the scan
            scan_row = await conn.fetchrow(
                """
                SELECT s.id, s.draft_id, s.status, d.title AS draft_title, d.content_text AS draft_content
                FROM scans s
                JOIN content_drafts d ON d.id = s.draft_id
                WHERE s.id = $1
                FOR UPDATE OF s;
                """,
                payload.scan_id,
            )

            if not scan_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Scan with ID '{payload.scan_id}' not found.",
                )

            # 2. Validate scan belongs to draft
            if scan_row["draft_id"] != payload.draft_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scan '{payload.scan_id}' does not belong to Draft '{payload.draft_id}'.",
                )

            # 3. Validate scan is completed
            if scan_row["status"] != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scan is not completed (status: '{scan_row['status']}'). Only completed scans can be reviewed.",
                )

            # 4. Check for duplicate review submission on this scan (protected by FOR UPDATE lock)
            existing_review = await conn.fetchrow(
                "SELECT id, decision FROM reviews WHERE scan_id = $1;",
                payload.scan_id,
            )
            if existing_review:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Scan '{payload.scan_id}' has already been reviewed (decision: {existing_review['decision']}).",
                )

            # 5. Persist the review record
            insert_review_query = """
                INSERT INTO reviews (
                    draft_id, scan_id, reviewer_id, reviewer_name, decision, comment
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, created_at;
            """

            review_record = await conn.fetchrow(
                insert_review_query,
                payload.draft_id,
                payload.scan_id,
                reviewer_id,
                reviewer_name,
                payload.decision.value,
                payload.comment or "",
            )

            if not review_record:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to persist review decision.",
                )

            review_id = review_record["id"]
            created_at = review_record["created_at"]

            # 6. Update draft lifecycle status
            new_draft_status = "approved" if payload.decision == ReviewDecision.APPROVED else "rejected"
            await conn.execute(
                "UPDATE content_drafts SET status = $1, updated_at = NOW() WHERE id = $2;",
                new_draft_status,
                payload.draft_id,
            )

            passport_id: Optional[UUID] = None

            # 7. If approved: assemble immutable snapshot, compute hash, and issue Content Passport
            if payload.decision == ReviewDecision.APPROVED:
                # Load all findings cited in this scan
                findings_rows = await conn.fetch(
                    """
                    SELECT policy_card_id, policy_version, category, severity, matched_text, source_quote
                    FROM findings
                    WHERE scan_id = $1
                    ORDER BY created_at ASC;
                    """,
                    payload.scan_id,
                )

                policy_versions_applied = sorted(
                    [
                        {
                            "policy_card_id": str(f["policy_card_id"] or ""),
                            "policy_version": str(f["policy_version"]),
                        }
                        for f in findings_rows
                    ],
                    key=lambda x: (x["policy_card_id"], x["policy_version"]),
                )

                findings_summary = [
                    {
                        "category": f["category"],
                        "severity": f["severity"],
                        "matched_text": f["matched_text"],
                        "source_quote": f["source_quote"],
                    }
                    for f in findings_rows
                ]

                # Assemble stable snapshot
                metadata_snapshot: Dict[str, Any] = {
                    "draft_id": str(payload.draft_id),
                    "draft_title": scan_row["draft_title"],
                    "draft_content": scan_row["draft_content"],
                    "scan_id": str(payload.scan_id),
                    "review_id": str(review_id),
                    "reviewer_id": reviewer_id,
                    "reviewer_name": reviewer_name,
                    "decision": "approved",
                    "comment": payload.comment or "",
                    "policy_versions_applied": policy_versions_applied,
                    "findings_summary": findings_summary,
                    "total_findings": len(findings_rows),
                    "issued_at": created_at.isoformat(),
                }

                # Compute SHA-256 hash over canonical representation
                passport_hash = compute_canonical_passport_hash(metadata_snapshot)

                insert_passport_query = """
                    INSERT INTO passports (
                        draft_id, scan_id, review_id, passport_hash, status, metadata_snapshot
                    ) VALUES ($1, $2, $3, $4, 'valid', $5::jsonb)
                    RETURNING id;
                """

                passport_record = await conn.fetchrow(
                    insert_passport_query,
                    payload.draft_id,
                    payload.scan_id,
                    review_id,
                    passport_hash,
                    json.dumps(metadata_snapshot),
                )

                if not passport_record:
                    raise RuntimeError("Failed to persist Content Passport record.")

                passport_id = passport_record["id"]

    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scan '{payload.scan_id}' has already been reviewed.",
        )
    except Exception as exc:
        logger.error(f"Review transaction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record review decision due to an internal error.",
        )

    return ReviewResponse(
        id=review_id,
        draft_id=payload.draft_id,
        scan_id=payload.scan_id,
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
        decision=payload.decision,
        comment=payload.comment or "",
        passport_id=passport_id,
        created_at=created_at,
    )


async def get_passport(passport_id: UUID) -> PassportResponse:
    """Retrieve Content Passport from database and re-verify its cryptographic hash."""
    query = """
        SELECT id, draft_id, scan_id, review_id, passport_hash, status,
               metadata_snapshot, created_at
        FROM passports
        WHERE id = $1;
    """

    row = await db_manager.fetchrow(query, passport_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content Passport with ID '{passport_id}' not found.",
        )

    snapshot = row["metadata_snapshot"]
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except Exception:
            snapshot = {}

    # Verify hash integrity
    computed_hash = compute_canonical_passport_hash(snapshot)
    hash_verified = (computed_hash == row["passport_hash"])

    if not hash_verified:
        logger.warning(
            f"PASSPORT INTEGRITY COMPROMISED: Stored hash '{row['passport_hash']}' != computed '{computed_hash}'"
        )

    return PassportResponse(
        id=row["id"],
        draft_id=row["draft_id"],
        scan_id=row["scan_id"],
        review_id=row["review_id"],
        passport_hash=row["passport_hash"],
        status=PassportStatus(row["status"]),
        metadata_snapshot=snapshot,
        hash_verified=hash_verified,
        created_at=row["created_at"],
    )
