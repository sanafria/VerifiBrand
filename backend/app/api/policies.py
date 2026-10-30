"""Policy Card API Endpoints (Owned by Zoya & Nimra for Backend & Governance).

Implements:
- GET /api/policies: List active or filtered policy cards.
- POST /api/policies: Create a new policy card and initial immutable version.
- GET /api/policies/{policy_id}: Retrieve single policy by ID/key, with optional ?version=X for historical snapshots.
- PATCH /api/policies/{policy_id}: Update policy card with immutable version bump.
- POST /api/policies/{policy_id}/archive: Soft-archive a policy without deleting historical version records.
"""
from datetime import date, datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.db import db_manager
from backend.app.schemas.policy import (
    CardType,
    PolicyCardCreate,
    PolicyCardResponse,
    PolicyCardUpdate,
    PolicyListResponse,
    PolicyStatus,
    SeverityLevel,
    normalize_policy_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["Policies"])

# In-memory realistic seed storage for development, testing, and offline resilience
_SEEDED_MOCK_POLICIES: List[Dict[str, Any]] = [
    {
        "id": UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"),
        "policy_key": "pol_term_001",
        "title": "Brand Addressing Terminology",
        "card_type": CardType.TERMINOLOGY,
        "rule_text": "The brand prohibits the term 'Customers' and requires the term 'Members'. Always refer to account holders as members.",
        "approved_value": "Members",
        "source_quote": "The brand prohibits the term 'Customers' and requires the term 'Members'.",
        "valid_from": date(2026, 1, 1),
        "valid_until": None,
        "severity": SeverityLevel.BLOCKER,
        "status": PolicyStatus.ACTIVE,
        "version": 1,
        "rules": [
            {
                "type": "terminology",
                "prohibited": "Customers",
                "replacement": "Members",
                "quote": "The brand prohibits the term 'Customers' and requires the term 'Members'.",
            }
        ],
        "metadata": {"prohibited_terms": [{"term": "Customers", "replacement": "Members"}]},
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 1, 0, 0, 0),
    },
    {
        "id": UUID("b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"),
        "policy_key": "pol_offer_002",
        "title": "Summer Discount Promotion Validity",
        "card_type": CardType.OFFER,
        "rule_text": "Summer Discount promotion is valid through 2026-06-30. After this date, standard pricing applies.",
        "approved_value": "Standard Pricing",
        "source_quote": "Summer Discount promotion is valid through 2026-06-30.",
        "valid_from": date(2026, 5, 1),
        "valid_until": date(2026, 6, 30),
        "severity": SeverityLevel.BLOCKER,
        "status": PolicyStatus.ACTIVE,
        "version": 1,
        "rules": [
            {
                "type": "offer_validity",
                "offer_name": "Summer Discount",
                "valid_until": "2026-06-30",
                "quote": "Summer Discount promotion is valid through 2026-06-30.",
            }
        ],
        "metadata": {"offer_name": "Summer Discount", "valid_until": "2026-06-30"},
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 1, 0, 0, 0),
    },
    {
        "id": UUID("c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f"),
        "policy_key": "pol_claim_003",
        "title": "Superlative Market Claims Evidence",
        "card_type": CardType.CLAIM,
        "rule_text": "Any superlative claim such as 'India''s No. 1' must be supported by certified market share documentation.",
        "approved_value": "Certified Documentation Required",
        "source_quote": "Any superlative claim such as 'India''s No. 1' must be supported by certified market share documentation.",
        "valid_from": date(2026, 1, 1),
        "valid_until": None,
        "severity": SeverityLevel.BLOCKER,
        "status": PolicyStatus.ACTIVE,
        "version": 1,
        "rules": [
            {
                "type": "unsupported_claim",
                "claim_pattern": "India's No. 1",
                "quote": "Any superlative claim such as 'India''s No. 1' must be supported by certified market share documentation.",
            }
        ],
        "metadata": {"required_evidence": "Market share audit report"},
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 1, 0, 0, 0),
    },
    {
        "id": UUID("d4e5f6a7-b89c-0d1e-2f3a-4b5c6d7e8f9a"),
        "policy_key": "pol_num_004",
        "title": "Bonus Points Transaction Limit",
        "card_type": CardType.FACT,
        "rule_text": "Members can earn up to 500 bonus points per transaction. Any claim stating higher earnings is prohibited.",
        "approved_value": "500 bonus points",
        "source_quote": "Members can earn up to 500 bonus points per transaction.",
        "valid_from": date(2026, 1, 1),
        "valid_until": None,
        "severity": SeverityLevel.WARNING,
        "status": PolicyStatus.ACTIVE,
        "version": 1,
        "rules": [
            {
                "type": "numerical_limit",
                "entity": "bonus points",
                "max_value": 500,
                "quote": "Members can earn up to 500 bonus points per transaction.",
            }
        ],
        "metadata": {"limit": 500, "unit": "points"},
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 1, 0, 0, 0),
    },
]

# Snapshot version history store (records exact immutable copies)
_SEEDED_MOCK_VERSIONS: List[Dict[str, Any]] = [
    {
        "policy_card_id": p["id"],
        "version": p["version"],
        "title": p["title"],
        "card_type": p["card_type"],
        "rule_text": p["rule_text"],
        "approved_value": p["approved_value"],
        "source_quote": p["source_quote"],
        "valid_from": p["valid_from"],
        "valid_until": p["valid_until"],
        "severity": p["severity"],
        "rules": p["rules"],
        "metadata": p["metadata"],
        "created_at": p["created_at"],
    }
    for p in _SEEDED_MOCK_POLICIES
]

# Runtime working copies
_mock_policies: List[Dict[str, Any]] = [dict(p) for p in _SEEDED_MOCK_POLICIES]
_mock_versions: List[Dict[str, Any]] = [dict(v) for v in _SEEDED_MOCK_VERSIONS]


def reset_mock_policies() -> None:
    """Reset mock policy and version stores to clean seed state for test isolation."""
    global _mock_policies, _mock_versions
    _mock_policies = [dict(p) for p in _SEEDED_MOCK_POLICIES]
    _mock_versions = [dict(v) for v in _SEEDED_MOCK_VERSIONS]



def _parse_json_field(val: Any, default: Any, expected_type: Optional[type] = None) -> Any:
    """Helper to safely deserialize JSON fields into Python dict or list.

    Handles:
    - Already decoded dict/list
    - Single-encoded JSON string ('[]' -> [])
    - Double-encoded JSON string ('"[]"' -> [])
    - None or empty string -> default
    - Ensures result matches expected_type if specified
    """
    if val is None:
        return default

    if isinstance(val, (dict, list)):
        if expected_type and not isinstance(val, expected_type):
            return default
        return val

    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return default
        try:
            parsed = json.loads(cleaned)
            # Handle possible double-serialization in database (e.g. '"[]"' -> '[]')
            if isinstance(parsed, str) and (parsed.startswith("{") or parsed.startswith("[")):
                try:
                    parsed2 = json.loads(parsed)
                    if isinstance(parsed2, (dict, list)):
                        parsed = parsed2
                except Exception:
                    pass
            if expected_type and not isinstance(parsed, expected_type):
                logger.warning(
                    "Parsed JSON field expected %s but got %s: %s",
                    expected_type.__name__,
                    type(parsed).__name__,
                    val,
                )
                return default
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception as exc:
            logger.warning("Failed to decode JSON field: %s (error: %s)", val, exc)
            return default

    return default


def _parse_json_rules(val: Any) -> list:
    """Safely decode rules column into a Python list."""
    res = _parse_json_field(val, default=[], expected_type=list)
    return res if isinstance(res, list) else []


def _parse_json_metadata(val: Any) -> dict:
    """Safely decode metadata column into a Python dict."""
    res = _parse_json_field(val, default={}, expected_type=dict)
    return res if isinstance(res, dict) else {}


def _row_to_response(row: Union[dict, Any]) -> PolicyCardResponse:
    """Helper to convert asyncpg Record or dictionary to PolicyCardResponse schema."""
    is_dict = isinstance(row, dict)

    raw_id = row.get("id") if is_dict else row["id"]
    if isinstance(raw_id, str):
        row_id = UUID(raw_id)
    else:
        row_id = raw_id

    policy_key = (
        row.get("policy_key")
        if is_dict
        else (row["policy_key"] if "policy_key" in row else None)
    )

    rules_val = _parse_json_rules(row.get("rules") if is_dict else row["rules"])
    meta_val = _parse_json_metadata(
        row.get("metadata") if is_dict else row["metadata"]
    )

    raw_status = row.get("status") if is_dict else row["status"]
    status_clean = normalize_policy_status(raw_status)

    card_type_raw = row.get("card_type") if is_dict else row["card_type"]
    card_type_enum = (
        card_type_raw
        if isinstance(card_type_raw, CardType)
        else CardType(str(card_type_raw).lower())
    )

    severity_raw = row.get("severity") if is_dict else row["severity"]
    severity_enum = (
        severity_raw
        if isinstance(severity_raw, SeverityLevel)
        else SeverityLevel(str(severity_raw).lower())
    )

    return PolicyCardResponse(
        id=row_id,
        policy_key=policy_key,
        title=row.get("title") if is_dict else row["title"],
        card_type=card_type_enum,
        rule_text=row.get("rule_text") if is_dict else row["rule_text"],
        approved_value=row.get("approved_value")
        if is_dict
        else row["approved_value"],
        source_quote=row.get("source_quote") if is_dict else row["source_quote"],
        valid_from=row.get("valid_from") if is_dict else row["valid_from"],
        valid_until=row.get("valid_until") if is_dict else row["valid_until"],
        severity=severity_enum,
        status=status_clean,
        version=row.get("version", 1) if is_dict else row["version"],
        rules=rules_val,
        metadata=meta_val,
        created_at=row.get("created_at", datetime.now(timezone.utc))
        if is_dict
        else row["created_at"],
        updated_at=row.get("updated_at", datetime.now(timezone.utc))
        if is_dict
        else row["updated_at"],
    )


def _is_db_connected() -> bool:
    """Check whether live PostgreSQL pool is connected and usable."""
    return db_manager.pool is not None


@router.get(
    "",
    response_model=PolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Policy Cards",
    description="Retrieve all brand policy cards with optional category, status, and search filters.",
)
async def list_policies(
    card_type: Optional[CardType] = Query(None, description="Filter by card category"),
    status_filter: Optional[str] = Query(
        "active",
        alias="status",
        description="Filter by status ('active', 'inactive', 'approved', 'archived', 'all'; default 'active')",
    ),
    search: Optional[str] = Query(None, description="Keyword search in title, rules, and source quote"),
) -> PolicyListResponse:
    """List policy cards according to query filters."""
    # Determine target status filter
    filter_norm = str(status_filter).lower().strip() if status_filter else "active"
    match_status: Optional[str] = None
    if filter_norm in ("active", "approved"):
        match_status = "active"
    elif filter_norm in ("inactive", "archived", "draft"):
        match_status = "inactive"
    elif filter_norm == "all":
        match_status = None

    if _is_db_connected():
        try:
            conditions = []
            params: List[Any] = []

            if card_type:
                params.append(card_type.value)
                conditions.append(f"card_type = ${len(params)}")

            if match_status:
                params.append(match_status)
                conditions.append(f"status = ${len(params)}")

            if search and search.strip():
                params.append(f"%{search.strip().lower()}%")
                idx = len(params)
                conditions.append(
                    f"(LOWER(title) LIKE ${idx} OR LOWER(rule_text) LIKE ${idx} OR LOWER(source_quote) LIKE ${idx} OR LOWER(COALESCE(policy_key, '')) LIKE ${idx})"
                )

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                       valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at
                FROM policy_cards
                {where_clause}
                ORDER BY created_at DESC;
            """
            rows = await db_manager.fetch(query, *params)
            items = [_row_to_response(row) for row in rows]
            return PolicyListResponse(items=items, total=len(items))
        except Exception as exc:
            logger.warning("Postgres query failed, using in-memory store: %s", exc)

    # In-memory store fallback
    results = list(_mock_policies)

    if card_type:
        results = [p for p in results if p["card_type"] == card_type]

    if match_status:
        results = [
            p
            for p in results
            if normalize_policy_status(p["status"]).value == match_status
        ]

    if search and search.strip():
        q = search.strip().lower()
        results = [
            p
            for p in results
            if (
                q in p["title"].lower()
                or q in p["rule_text"].lower()
                or q in p["source_quote"].lower()
                or (p.get("policy_key") and q in p["policy_key"].lower())
            )
        ]

    # Sort descending by created_at
    results.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    items = [_row_to_response(p) for p in results]
    return PolicyListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=PolicyCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Policy Card",
    description="Create a new policy card and register its initial immutable version 1.",
)
async def create_policy(payload: PolicyCardCreate) -> PolicyCardResponse:
    """Create a new policy card and initial immutable version record."""
    card_id = payload.id or uuid4()
    now = datetime.now(timezone.utc)
    policy_key = payload.policy_key or f"pol_{payload.card_type.value}_{card_id.hex[:6]}"
    initial_status = normalize_policy_status(payload.status)

    if _is_db_connected():
        try:
            insert_policy_query = """
                INSERT INTO policy_cards (
                    id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                    valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 1, $12::jsonb, $13::jsonb, $14, $14)
                RETURNING id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                          valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at;
            """
            insert_version_query = """
                INSERT INTO policy_card_versions (
                    policy_card_id, version, title, card_type, rule_text,
                    approved_value, source_quote, valid_from, valid_until, severity, rules, metadata, created_at
                ) VALUES ($1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12)
                ON CONFLICT (policy_card_id, version) DO NOTHING;
            """

            row = await db_manager.fetchrow(
                insert_policy_query,
                card_id,
                policy_key,
                payload.title,
                payload.card_type.value,
                payload.rule_text,
                payload.approved_value,
                payload.source_quote,
                payload.valid_from,
                payload.valid_until,
                payload.severity.value,
                initial_status.value,
                json.dumps(payload.rules if isinstance(payload.rules, list) else []),
                json.dumps(payload.metadata if isinstance(payload.metadata, dict) else {}),
                now,
            )

            if row:
                await db_manager.execute(
                    insert_version_query,
                    row["id"],
                    row["title"],
                    row["card_type"],
                    row["rule_text"],
                    row["approved_value"],
                    row["source_quote"],
                    row["valid_from"],
                    row["valid_until"],
                    row["severity"],
                    json.dumps(payload.rules if isinstance(payload.rules, list) else []),
                    json.dumps(payload.metadata if isinstance(payload.metadata, dict) else {}),
                    now,
                )
                return _row_to_response(row)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Database insert failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database insert failed: {exc}",
            )

    # In-memory store fallback
    new_card: Dict[str, Any] = {
        "id": card_id,
        "policy_key": policy_key,
        "title": payload.title,
        "card_type": payload.card_type,
        "rule_text": payload.rule_text,
        "approved_value": payload.approved_value,
        "source_quote": payload.source_quote,
        "valid_from": payload.valid_from,
        "valid_until": payload.valid_until,
        "severity": payload.severity,
        "status": initial_status,
        "version": 1,
        "rules": list(payload.rules),
        "metadata": dict(payload.metadata),
        "created_at": now,
        "updated_at": now,
    }
    _mock_policies.insert(0, new_card)
    _mock_versions.append(
        {
            "policy_card_id": card_id,
            "version": 1,
            "title": payload.title,
            "card_type": payload.card_type,
            "rule_text": payload.rule_text,
            "approved_value": payload.approved_value,
            "source_quote": payload.source_quote,
            "valid_from": payload.valid_from,
            "valid_until": payload.valid_until,
            "severity": payload.severity,
            "rules": list(payload.rules),
            "metadata": dict(payload.metadata),
            "created_at": now,
        }
    )
    return _row_to_response(new_card)


@router.get(
    "/{policy_id}",
    response_model=PolicyCardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Single Policy Card (Supports ?version=X)",
    description="Retrieve a single policy card by UUID or policy_key. Supports ?version=X for immutable historical snapshots.",
)
async def get_policy(
    policy_id: str,
    version: Optional[int] = Query(
        None, description="Exact historical version number (retrieves immutable snapshot)"
    ),
) -> PolicyCardResponse:
    """Retrieve current policy or exact historical version."""
    # Check if policy_id is UUID or slug string
    is_uuid = False
    parsed_uuid: Optional[UUID] = None
    try:
        parsed_uuid = UUID(policy_id)
        is_uuid = True
    except ValueError:
        is_uuid = False

    if _is_db_connected():
        try:
            # 1. If explicit historical version requested:
            if version is not None:
                if is_uuid:
                    version_query = """
                        SELECT v.policy_card_id AS id, p.policy_key, v.version, v.title, v.card_type,
                               v.rule_text, v.approved_value, v.source_quote, v.valid_from, v.valid_until,
                               v.severity, p.status, v.rules, v.metadata, v.created_at, p.updated_at
                        FROM policy_card_versions v
                        JOIN policy_cards p ON p.id = v.policy_card_id
                        WHERE v.policy_card_id = $1 AND v.version = $2;
                    """
                    row = await db_manager.fetchrow(version_query, parsed_uuid, version)
                else:
                    version_query = """
                        SELECT v.policy_card_id AS id, p.policy_key, v.version, v.title, v.card_type,
                               v.rule_text, v.approved_value, v.source_quote, v.valid_from, v.valid_until,
                               v.severity, p.status, v.rules, v.metadata, v.created_at, p.updated_at
                        FROM policy_card_versions v
                        JOIN policy_cards p ON p.id = v.policy_card_id
                        WHERE p.policy_key = $1 AND v.version = $2;
                    """
                    row = await db_manager.fetchrow(version_query, policy_id, version)

                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Historical policy version {version} for policy '{policy_id}' not found.",
                    )
                return _row_to_response(row)

            # 2. Latest active card lookup:
            if is_uuid:
                current_query = """
                    SELECT id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                           valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at
                    FROM policy_cards
                    WHERE id = $1;
                """
                row = await db_manager.fetchrow(current_query, parsed_uuid)
            else:
                current_query = """
                    SELECT id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                           valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at
                    FROM policy_cards
                    WHERE policy_key = $1;
                """
                row = await db_manager.fetchrow(current_query, policy_id)

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Policy card '{policy_id}' not found.",
                )
            return _row_to_response(row)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("DB lookup failed for policy '%s': %s", policy_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database lookup failed: {exc}",
            )

    # In-memory store fallback
    matched_card: Optional[Dict[str, Any]] = None
    for p in _mock_policies:
        if is_uuid and p["id"] == parsed_uuid:
            matched_card = p
            break
        elif str(p["id"]) == policy_id or p.get("policy_key") == policy_id:
            matched_card = p
            break

    if not matched_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy card '{policy_id}' not found.",
        )

    # If historical version requested:
    if version is not None:
        target_version_record = None
        for v in _mock_versions:
            if (
                v["policy_card_id"] == matched_card["id"]
                and v["version"] == version
            ):
                target_version_record = v
                break
        if not target_version_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Historical policy version {version} for policy '{policy_id}' not found.",
            )
        # Assemble historical response
        hist_copy = dict(matched_card)
        hist_copy.update(target_version_record)
        hist_copy["id"] = matched_card["id"]
        hist_copy["policy_key"] = matched_card.get("policy_key")
        return _row_to_response(hist_copy)

    return _row_to_response(matched_card)


@router.patch(
    "/{policy_id}",
    response_model=PolicyCardResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Policy Card (Version Bump)",
    description="Update an existing policy card. Content changes bump version and save historical snapshots.",
)
async def update_policy(
    policy_id: str,
    payload: PolicyCardUpdate,
) -> PolicyCardResponse:
    """Update a policy card and save a new immutable version snapshot if content changed."""
    is_uuid = False
    parsed_uuid: Optional[UUID] = None
    try:
        parsed_uuid = UUID(policy_id)
        is_uuid = True
    except ValueError:
        is_uuid = False

    now = datetime.now(timezone.utc)

    if _is_db_connected():
        try:
            if is_uuid:
                fetch_query = "SELECT * FROM policy_cards WHERE id = $1;"
                existing = await db_manager.fetchrow(fetch_query, parsed_uuid)
            else:
                fetch_query = "SELECT * FROM policy_cards WHERE policy_key = $1;"
                existing = await db_manager.fetchrow(fetch_query, policy_id)

            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Policy card '{policy_id}' not found.",
                )

            # Determine updated values
            new_title = payload.title if payload.title is not None else existing["title"]
            new_rule_text = payload.rule_text if payload.rule_text is not None else existing["rule_text"]
            new_approved_value = (
                payload.approved_value if payload.approved_value is not None else existing["approved_value"]
            )
            new_source_quote = (
                payload.source_quote if payload.source_quote is not None else existing["source_quote"]
            )
            new_valid_from = (
                payload.valid_from if payload.valid_from is not None else existing["valid_from"]
            )
            new_valid_until = (
                payload.valid_until if payload.valid_until is not None else existing["valid_until"]
            )
            new_severity = (
                payload.severity.value if payload.severity is not None else existing["severity"]
            )
            new_status = (
                normalize_policy_status(payload.status).value
                if payload.status is not None
                else existing["status"]
            )
            new_card_type = (
                payload.card_type.value if payload.card_type is not None else existing["card_type"]
            )
            existing_rules_parsed = _parse_json_rules(existing["rules"])
            existing_metadata_parsed = _parse_json_metadata(existing["metadata"])

            if payload.rules is not None:
                rules_to_save = payload.rules if isinstance(payload.rules, list) else []
            else:
                rules_to_save = existing_rules_parsed
            new_rules = json.dumps(rules_to_save)

            if payload.metadata is not None:
                metadata_to_save = payload.metadata if isinstance(payload.metadata, dict) else {}
            else:
                metadata_to_save = existing_metadata_parsed
            new_metadata = json.dumps(metadata_to_save)

            # Check if content changed
            content_changed = (
                new_title != existing["title"]
                or new_rule_text != existing["rule_text"]
                or new_approved_value != existing["approved_value"]
                or new_source_quote != existing["source_quote"]
                or new_valid_from != existing["valid_from"]
                or new_valid_until != existing["valid_until"]
                or new_severity != existing["severity"]
                or new_card_type != existing["card_type"]
                or (payload.rules is not None and rules_to_save != existing_rules_parsed)
                or (payload.metadata is not None and metadata_to_save != existing_metadata_parsed)
            )

            new_version = existing["version"] + 1 if content_changed else existing["version"]

            update_query = """
                UPDATE policy_cards
                SET title = $1,
                    rule_text = $2,
                    approved_value = $3,
                    source_quote = $4,
                    valid_from = $5,
                    valid_until = $6,
                    severity = $7,
                    status = $8,
                    version = $9,
                    card_type = $10,
                    rules = $11::jsonb,
                    metadata = $12::jsonb,
                    updated_at = $13
                WHERE id = $14
                RETURNING id, policy_key, title, card_type, rule_text, approved_value, source_quote,
                          valid_from, valid_until, severity, status, version, rules, metadata, created_at, updated_at;
            """
            insert_version_query = """
                INSERT INTO policy_card_versions (
                    policy_card_id, version, title, card_type, rule_text,
                    approved_value, source_quote, valid_from, valid_until, severity, rules, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb, $13)
                ON CONFLICT (policy_card_id, version) DO NOTHING;
            """

            updated_row = await db_manager.fetchrow(
                update_query,
                new_title,
                new_rule_text,
                new_approved_value,
                new_source_quote,
                new_valid_from,
                new_valid_until,
                new_severity,
                new_status,
                new_version,
                new_card_type,
                new_rules,
                new_metadata,
                now,
                existing["id"],
            )

            if not updated_row:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update policy card record in database.",
                )

            if content_changed:
                await db_manager.execute(
                    insert_version_query,
                    existing["id"],
                    new_version,
                    new_title,
                    new_card_type,
                    new_rule_text,
                    new_approved_value,
                    new_source_quote,
                    new_valid_from,
                    new_valid_until,
                    new_severity,
                    new_rules,
                    new_metadata,
                    now,
                )

            return _row_to_response(updated_row)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Database update failed for policy '%s': %s", policy_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database update failed: {exc}",
            )

    # In-memory store fallback
    matched_idx = -1
    for i, p in enumerate(_mock_policies):
        if is_uuid and p["id"] == parsed_uuid:
            matched_idx = i
            break
        elif str(p["id"]) == policy_id or p.get("policy_key") == policy_id:
            matched_idx = i
            break

    if matched_idx == -1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy card '{policy_id}' not found.",
        )

    current = _mock_policies[matched_idx]

    new_title = payload.title if payload.title is not None else current["title"]
    new_rule_text = payload.rule_text if payload.rule_text is not None else current["rule_text"]
    new_approved_value = (
        payload.approved_value if payload.approved_value is not None else current.get("approved_value")
    )
    new_source_quote = (
        payload.source_quote if payload.source_quote is not None else current["source_quote"]
    )
    new_valid_from = (
        payload.valid_from if payload.valid_from is not None else current.get("valid_from")
    )
    new_valid_until = (
        payload.valid_until if payload.valid_until is not None else current.get("valid_until")
    )
    new_severity = payload.severity if payload.severity is not None else current["severity"]
    new_status = (
        normalize_policy_status(payload.status)
        if payload.status is not None
        else current["status"]
    )
    new_card_type = payload.card_type if payload.card_type is not None else current["card_type"]
    new_rules = list(payload.rules) if payload.rules is not None else list(current.get("rules", []))
    new_metadata = dict(payload.metadata) if payload.metadata is not None else dict(current.get("metadata", {}))

    content_changed = (
        new_title != current["title"]
        or new_rule_text != current["rule_text"]
        or new_approved_value != current.get("approved_value")
        or new_source_quote != current["source_quote"]
        or new_valid_from != current.get("valid_from")
        or new_valid_until != current.get("valid_until")
        or new_severity != current["severity"]
        or new_card_type != current["card_type"]
        or (payload.rules is not None and payload.rules != current.get("rules", []))
    )

    new_version = current["version"] + 1 if content_changed else current["version"]

    updated_card = {
        **current,
        "title": new_title,
        "rule_text": new_rule_text,
        "approved_value": new_approved_value,
        "source_quote": new_source_quote,
        "valid_from": new_valid_from,
        "valid_until": new_valid_until,
        "severity": new_severity,
        "status": new_status,
        "version": new_version,
        "card_type": new_card_type,
        "rules": new_rules,
        "metadata": new_metadata,
        "updated_at": now,
    }
    _mock_policies[matched_idx] = updated_card

    if content_changed:
        _mock_versions.append(
            {
                "policy_card_id": current["id"],
                "version": new_version,
                "title": new_title,
                "card_type": new_card_type,
                "rule_text": new_rule_text,
                "approved_value": new_approved_value,
                "source_quote": new_source_quote,
                "valid_from": new_valid_from,
                "valid_until": new_valid_until,
                "severity": new_severity,
                "rules": new_rules,
                "metadata": new_metadata,
                "created_at": now,
            }
        )

    return _row_to_response(updated_card)


@router.post(
    "/{policy_id}/archive",
    response_model=PolicyCardResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive Policy Card",
    description="Soft-archive a policy card (sets status to inactive) without deleting its historical version history.",
)
async def archive_policy(policy_id: str) -> PolicyCardResponse:
    """Soft-archive policy by setting status to inactive while preserving all historical versions."""
    return await update_policy(
        policy_id=policy_id,
        payload=PolicyCardUpdate(status="inactive"),
    )
