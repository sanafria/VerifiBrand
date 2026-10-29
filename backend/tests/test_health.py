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


def test_backend_settings_rejects_insecure_production_webhook_secret() -> None:
    """Verify that backend Settings rejects dev or weak CMS_WEBHOOK_SECRET in production."""
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="Insecure development CMS_WEBHOOK_SECRET detected"):
        Settings(
            ENVIRONMENT="production",
            CMS_WEBHOOK_SECRET="brandledger_cms_default_secret_dev",
            DATABASE_URL="postgresql://prod_user:strong_prod_pass@127.0.0.1:5432/prod_db",
        )

    with pytest.raises(ValueError, match="Insecure development CMS_WEBHOOK_SECRET detected"):
        Settings(
            ENVIRONMENT="production",
            CMS_WEBHOOK_SECRET="short_dev_key",
            DATABASE_URL="postgresql://prod_user:strong_prod_pass@127.0.0.1:5432/prod_db",
        )


def test_backend_settings_rejects_insecure_production_database_password() -> None:
    """Verify that backend Settings rejects default dev database password in production."""
    from backend.app.config import Settings

    with pytest.raises(ValueError, match="Default development database credentials detected"):
        Settings(
            ENVIRONMENT="production",
            CMS_WEBHOOK_SECRET="super_secure_production_webhook_secret_32chars",
            DATABASE_URL="postgresql://brandledger_user:brandledger_secret@127.0.0.1:5432/brandledger",
        )


def test_backend_settings_accepts_valid_production_configuration() -> None:
    """Verify that backend Settings accepts strong, secure values in production."""
    from backend.app.config import Settings

    settings = Settings(
        ENVIRONMENT="production",
        CMS_WEBHOOK_SECRET="super_secure_production_webhook_secret_32chars",
        DATABASE_URL="postgresql://prod_user:strong_prod_pass@127.0.0.1:5432/prod_db",
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.CMS_WEBHOOK_SECRET == "super_secure_production_webhook_secret_32chars"
