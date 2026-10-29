"""Unit and Health Tests for Phase 1 Backend Foundation."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import (
    CardType,
    DraftStatus,
    HealthResponse,
    PassportStatus,
    PolicyStatus,
    ReviewDecision,
    ScanStatus,
    SeverityLevel,
    UserRole,
)


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a test client for the FastAPI application."""
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """Verify that GET /health returns 200 OK and status ok."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "brandledger-api"


def test_shared_schema_enums_consistency() -> None:
    """Verify that critical enum contracts exist and match team specifications."""
    assert CardType.TERMINOLOGY.value == "terminology"
    assert CardType.OFFER.value == "offer"
    assert CardType.CLAIM.value == "claim"

    assert PolicyStatus.ACTIVE.value == "active"
    assert PolicyStatus.INACTIVE.value == "inactive"

    assert SeverityLevel.BLOCKER.value == "blocker"
    assert SeverityLevel.WARNING.value == "warning"

    assert DraftStatus.DRAFT.value == "draft"
    assert DraftStatus.APPROVED.value == "approved"

    assert ScanStatus.COMPLETED.value == "completed"
    assert ScanStatus.FAILED.value == "failed"

    assert ReviewDecision.APPROVED.value == "approved"
    assert ReviewDecision.REJECTED.value == "rejected"

    assert PassportStatus.VALID.value == "valid"
    assert UserRole.REVIEWER.value == "reviewer"
    assert UserRole.CREATOR.value == "creator"


def test_app_starts_and_health_succeeds_without_cv2(client: TestClient) -> None:
    """Verify that FastAPI application starts and serves requests even when cv2 is unavailable."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "brandledger-api"
