"""Policy card schema and helper normalization functions for BrandLedger.

Supports robust extraction from various policy card representations
produced by Zoya's database model and Mahadevi's extraction pipeline.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PolicyCard(BaseModel):
    """Normalized policy card model for internal engine consumption."""
    id: str = Field(..., description="Unique policy card ID")
    version: str = Field(..., description="Policy version string")
    title: Optional[str] = Field(default="", description="Policy card title")
    category: Optional[str] = Field(default="", description="Policy category")
    content: str = Field(..., description="Full text/content of the approved policy")
    rules: Optional[list[dict[str, Any]]] = Field(default_factory=list, description="Structured rule definitions if available")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")


def normalize_policy_card(card_dict: dict[str, Any]) -> Optional[PolicyCard]:
    """Safely normalizes and validates a policy card dictionary.

    Returns None if essential fields (id, version, content) are missing or invalid,
    ensuring malformed records are handled gracefully without crashing the engine.
    """
    if not isinstance(card_dict, dict):
        return None

    card_id = (
        card_dict.get("id")
        or card_dict.get("policy_card_id")
        or card_dict.get("card_id")
    )
    version = (
        card_dict.get("version")
        or card_dict.get("policy_version")
        or card_dict.get("ver")
    )
    content = (
        card_dict.get("content")
        or card_dict.get("text")
        or card_dict.get("policy_text")
        or card_dict.get("description")
    )

    if not card_id or not version or content is None:
        return None

    card_id_str = str(card_id).strip()
    version_str = str(version).strip()
    content_str = str(content).strip()

    if not card_id_str or not version_str or not content_str:
        return None

    rules = card_dict.get("rules") or card_dict.get("rule_definitions") or []
    if not isinstance(rules, list):
        rules = []

    metadata = card_dict.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    title = str(card_dict.get("title") or card_dict.get("name") or "").strip()
    category = str(card_dict.get("category") or card_dict.get("type") or "").strip()

    return PolicyCard(
        id=card_id_str,
        version=version_str,
        title=title,
        category=category,
        content=content_str,
        rules=rules,
        metadata=metadata,
    )


# ==============================================================================
# API Contract Schemas (Owned by Nimra in UI, Zoya in Database & API)
# ==============================================================================

class CardType(str, Enum):
    """Supported Policy Card categories."""
    TERMINOLOGY = "terminology"
    OFFER = "offer"
    CLAIM = "claim"
    FACT = "fact"
    TONE = "tone"


class PolicyStatus(str, Enum):
    """Status of a policy card."""
    ACTIVE = "active"
    INACTIVE = "inactive"


def normalize_policy_status(status_val: Optional[Any]) -> PolicyStatus:
    """Map frontend and backend status representations to PolicyStatus."""
    if isinstance(status_val, PolicyStatus):
        return status_val
    if not status_val:
        return PolicyStatus.ACTIVE
    s = str(status_val).lower().strip()
    if s in ("active", "approved"):
        return PolicyStatus.ACTIVE
    if s in ("inactive", "archived", "draft"):
        return PolicyStatus.INACTIVE
    return PolicyStatus.ACTIVE


class SeverityLevel(str, Enum):
    """Finding severity level."""
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class PolicyCardBase(BaseModel):
    """Base fields for a BrandLedger Policy Card."""
    title: str = Field(..., min_length=2, max_length=255, description="Short policy title")
    card_type: CardType = Field(..., description="Category: terminology, offer, claim, fact, tone")
    rule_text: str = Field(..., min_length=3, description="Rule description or requirement")
    approved_value: Optional[str] = Field(None, description="Explicit approved text or value")
    source_quote: str = Field(..., min_length=3, description="Exact cited quote from brand source document")
    valid_from: Optional[date] = Field(None, description="Effective start date")
    valid_until: Optional[date] = Field(None, description="Expiration date (critical for offers)")
    severity: SeverityLevel = Field(default=SeverityLevel.BLOCKER, description="Default severity if violated")
    status: Optional[str] = Field(default="active", description="Policy status: active or inactive")
    policy_key: Optional[str] = Field(None, description="Stable human-readable policy key (e.g. pol_term_001)")
    rules: list[dict[str, Any]] = Field(default_factory=list, description="Structured rule definitions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary policy metadata")


class PolicyCardCreate(PolicyCardBase):
    """Payload to create a new policy card."""
    id: Optional[UUID] = Field(None, description="Optional pre-assigned UUID identifier")


class PolicyCardUpdate(BaseModel):
    """Payload to update an existing policy card with version bump."""
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    card_type: Optional[CardType] = None
    rule_text: Optional[str] = Field(None, min_length=3)
    approved_value: Optional[str] = None
    source_quote: Optional[str] = Field(None, min_length=3)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    severity: Optional[SeverityLevel] = None
    status: Optional[str] = None
    policy_key: Optional[str] = None
    rules: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None


class PolicyCardResponse(PolicyCardBase):
    """Policy Card representation returned by the API."""
    id: UUID = Field(..., description="Unique policy card ID")
    version: int = Field(default=1, description="Policy version number (immutable per version)")
    status: PolicyStatus = Field(default=PolicyStatus.ACTIVE, description="Active or inactive")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class PolicyListResponse(BaseModel):
    """Envelope for listing policies."""
    items: List[PolicyCardResponse] = Field(default_factory=list)
    total: int = Field(default=0)

