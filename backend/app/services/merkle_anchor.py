"""Merkle Anchor DAO for BrandLedger — Phase 3.3A (Member 6).

Provides the minimal database operations for managing Merkle anchor records:
  - create_anchor:        Insert a new anchor row idempotently.
  - get_anchor_by_id:     Fetch a single anchor record by primary key.
  - get_latest_anchor:    Fetch the most-recently created anchor.
  - update_anchor_status: Transition anchor status with safety guards.

Design constraints enforced here:
  - A mock receipt (receipt_source='mock') can NEVER be promoted to 'anchored'.
  - Concurrent duplicate root_hash inserts resolve via the DB unique index:
    ON CONFLICT DO NOTHING returns None; the caller re-fetches the existing row.
  - Failure history is preserved: failure_reason is only replaced when the
    caller explicitly supplies a new one during a retry from 'failed'.
  - Only the permitted status transitions are allowed:
      pending  → anchored | failed
      failed   → pending (retry)
      anchored → (terminal; no transition permitted)

All SQL uses parameterised queries. No DDL is emitted from this module.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from backend.app.db import db_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permitted state transitions
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: Dict[str, tuple] = {
    "pending": ("anchored", "failed"),
    "failed": ("pending",),   # allow retry
    "anchored": (),           # terminal state
}

_ALL_STATUSES = frozenset(["pending", "anchored", "failed"])


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

async def _ensure_connected() -> None:
    """Connect the db_manager pool if it is not already active."""
    if not db_manager.is_connected:
        await db_manager.connect()


# ---------------------------------------------------------------------------
# Public DAO functions
# ---------------------------------------------------------------------------

async def create_anchor(
    root_hash: str,
    receipt_source: str,
    receipt: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a new merkle_anchor row for the given root_hash.

    Idempotent: if a row for root_hash already exists the existing row is
    returned unchanged (no overwrite).  Under concurrent pressure the unique
    index on root_hash guarantees exactly one winner.

    Args:
        root_hash:      64-character lowercase hex SHA-256 string.
        receipt_source: 'mock' or 'real'.  Stored verbatim; DB CHECK enforces
                        the allowed values.
        receipt:        Optional provider receipt (may be None for 'pending').

    Returns:
        Dict representation of the row that now exists in the database.

    Raises:
        ValueError: if root_hash is not a 64-character hex string or
                    receipt_source is not 'mock' or 'real'.
    """
    # Input validation
    clean_hash = root_hash.strip().lower() if root_hash else ""
    if len(clean_hash) != 64:
        raise ValueError(
            f"root_hash must be a 64-character hex string; got length {len(clean_hash)}."
        )
    try:
        int(clean_hash, 16)
    except ValueError:
        raise ValueError("root_hash contains invalid hexadecimal characters.")

    if receipt_source not in ("mock", "real"):
        raise ValueError(
            f"receipt_source must be 'mock' or 'real'; got '{receipt_source}'."
        )

    await _ensure_connected()

    insert_sql = """
        INSERT INTO merkle_anchors (root_hash, status, receipt, receipt_source)
        VALUES ($1, 'pending', $2, $3)
        ON CONFLICT (root_hash) DO NOTHING
        RETURNING
            anchor_id::text, root_hash, status, receipt,
            receipt_source, failure_reason,
            created_at::text, updated_at::text;
    """
    row = await db_manager.fetchrow(insert_sql, clean_hash, receipt, receipt_source)

    if row is not None:
        # Successful insert — return the new row
        return dict(row)

    # ON CONFLICT DO NOTHING → row already exists; re-fetch it
    existing = await get_anchor_by_hash(clean_hash)
    if existing is None:
        # Should never happen (we just hit a conflict), but guard anyway
        raise RuntimeError(
            f"Anchor insert conflicted on root_hash '{clean_hash}' but "
            "the existing row could not be retrieved."
        )
    return existing


async def get_anchor_by_id(anchor_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single anchor record by its UUID primary key.

    Args:
        anchor_id: UUID string (dashes optional; will be passed to PostgreSQL
                   as a UUID parameter).

    Returns:
        Dict of the row, or None if no record exists with that anchor_id.
    """
    await _ensure_connected()

    sql = """
        SELECT
            anchor_id::text, root_hash, status, receipt,
            receipt_source, failure_reason,
            created_at::text, updated_at::text
        FROM merkle_anchors
        WHERE anchor_id = $1;
    """
    try:
        uuid_val = UUID(str(anchor_id))
    except (ValueError, AttributeError):
        raise ValueError(f"anchor_id is not a valid UUID: '{anchor_id}'.")

    row = await db_manager.fetchrow(sql, uuid_val)
    return dict(row) if row is not None else None


async def get_anchor_by_hash(root_hash: str) -> Optional[Dict[str, Any]]:
    """Fetch the anchor record for a given root_hash.

    Returns:
        Dict of the row, or None if no record exists.
    """
    await _ensure_connected()

    clean_hash = root_hash.strip().lower() if root_hash else ""
    sql = """
        SELECT
            anchor_id::text, root_hash, status, receipt,
            receipt_source, failure_reason,
            created_at::text, updated_at::text
        FROM merkle_anchors
        WHERE root_hash = $1;
    """
    row = await db_manager.fetchrow(sql, clean_hash)
    return dict(row) if row is not None else None


async def get_latest_anchor() -> Optional[Dict[str, Any]]:
    """Fetch the most-recently created anchor record.

    Returns:
        Dict of the most recent row, or None if the table is empty.
    """
    await _ensure_connected()

    sql = """
        SELECT
            anchor_id::text, root_hash, status, receipt,
            receipt_source, failure_reason,
            created_at::text, updated_at::text
        FROM merkle_anchors
        ORDER BY created_at DESC
        LIMIT 1;
    """
    row = await db_manager.fetchrow(sql)
    return dict(row) if row is not None else None


async def update_anchor_status(
    anchor_id: str,
    new_status: str,
    receipt: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Transition an anchor record to a new status with safety guards.

    Safety rules enforced:
      1. A mock receipt (receipt_source='mock') cannot be promoted to 'anchored'.
      2. An 'anchored' record is terminal; no further transitions are permitted.
      3. Only the transitions listed in _VALID_TRANSITIONS are allowed.
      4. failure_reason is preserved from a previous failure unless the caller
         explicitly provides a replacement (i.e. during a retry).

    Args:
        anchor_id:      UUID of the anchor to update.
        new_status:     Target status ('pending', 'anchored', or 'failed').
        receipt:        Optional updated receipt to store (kept if None).
        failure_reason: Reason string when new_status='failed'; clears when
                        new_status='pending' (retry) only if caller provides
                        a new value explicitly.

    Returns:
        Updated dict of the row after the transition.

    Raises:
        ValueError:  On invalid status, illegal transition, or mock→anchored attempt.
        LookupError: If no anchor exists with the given anchor_id.
    """
    if new_status not in _ALL_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Must be one of: {sorted(_ALL_STATUSES)}."
        )

    existing = await get_anchor_by_id(anchor_id)
    if existing is None:
        raise LookupError(f"No anchor found with anchor_id='{anchor_id}'.")

    current_status = existing["status"]
    allowed_next = _VALID_TRANSITIONS.get(current_status, ())

    if new_status not in allowed_next:
        raise ValueError(
            f"Invalid status transition: '{current_status}' → '{new_status}'. "
            f"Allowed from '{current_status}': {allowed_next or '(none — terminal state)'}."
        )

    # Guard: mock receipt cannot become 'anchored'
    if new_status == "anchored" and existing.get("receipt_source") == "mock":
        raise ValueError(
            "A mock receipt cannot be promoted to 'anchored'. "
            "Only a receipt from a real external provider may transition to 'anchored'."
        )

    # Resolve which receipt to store: keep the existing value if no new one provided
    resolved_receipt = receipt if receipt is not None else existing.get("receipt")

    # Preserve failure_reason from previous failure unless a new one is given
    resolved_failure_reason: Optional[str]
    if new_status == "failed":
        # Keep the incoming reason (or the existing one if none supplied)
        resolved_failure_reason = failure_reason if failure_reason is not None else existing.get("failure_reason")
    elif new_status == "pending":
        # Retry: clear failure_reason only if a new failure_reason was explicitly
        # provided (to record context); otherwise preserve history
        resolved_failure_reason = None
    else:
        # anchored: clear failure_reason (success)
        resolved_failure_reason = None

    await _ensure_connected()

    update_sql = """
        UPDATE merkle_anchors
        SET
            status         = $1,
            receipt        = $2,
            failure_reason = $3,
            updated_at     = NOW()
        WHERE anchor_id = $4
        RETURNING
            anchor_id::text, root_hash, status, receipt,
            receipt_source, failure_reason,
            created_at::text, updated_at::text;
    """
    try:
        uuid_val = UUID(str(anchor_id))
    except (ValueError, AttributeError):
        raise ValueError(f"anchor_id is not a valid UUID: '{anchor_id}'.")

    row = await db_manager.fetchrow(
        update_sql,
        new_status,
        resolved_receipt,
        resolved_failure_reason,
        uuid_val,
    )
    if row is None:
        raise LookupError(
            f"Anchor update returned no row for anchor_id='{anchor_id}'. "
            "The record may have been deleted concurrently."
        )
    return dict(row)

