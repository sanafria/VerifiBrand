"""Unit tests validating Database Schema (schema.sql), Seed Data (seed.sql), and Docker configuration."""
from pathlib import Path
import re
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "schema.sql"
SEED_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "seed.sql"
DOCKER_COMPOSE_PATH = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"


MIGRATION_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "migrations" / "001_unique_scan_constraints.sql"


def test_schema_file_exists() -> None:
    """Verify database/schema.sql exists and is non-empty."""
    assert SCHEMA_PATH.exists(), f"Schema file not found at {SCHEMA_PATH}"
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    assert len(content) > 200


def test_schema_defines_all_six_core_tables() -> None:
    """Verify that all six core BrandLedger entities plus version history are defined."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    expected_tables = [
        "policy_cards",
        "policy_card_versions",
        "content_drafts",
        "scans",
        "findings",
        "reviews",
        "passports",
    ]

    for table in expected_tables:
        pattern = rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table}\b"
        match = re.search(pattern, content, re.IGNORECASE)
        assert match is not None, f"Expected table '{table}' not found in schema.sql"


def test_schema_foreign_key_relationships() -> None:
    """Verify critical relational foreign key integrity across tables."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "REFERENCES content_drafts(id)" in content, "Missing FK to content_drafts"
    assert "REFERENCES scans(id)" in content, "Missing FK to scans"
    assert "REFERENCES reviews(id)" in content, "Missing FK to reviews in passports"
    assert "REFERENCES policy_cards(id)" in content, "Missing FK to policy_cards in policy_card_versions"


def test_schema_check_constraints() -> None:
    """Verify status and type check constraints match team contracts."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    # Card types
    assert "'terminology'" in content
    assert "'offer'" in content
    assert "'claim'" in content

    # Review decisions
    assert "'approved'" in content
    assert "'rejected'" in content

    # Passport statuses
    assert "'valid'" in content
    assert "'revoked'" in content


def test_seed_file_exists_and_is_idempotent() -> None:
    """Verify database/seed.sql exists and uses safe ON CONFLICT clauses."""
    assert SEED_PATH.exists(), f"Seed file not found at {SEED_PATH}"
    content = SEED_PATH.read_text(encoding="utf-8")

    # Safe rerun check
    assert "ON CONFLICT" in content, "seed.sql must be idempotent with ON CONFLICT"

    # Core demo policies
    assert "pol_term_001" in content
    assert "pol_offer_002" in content
    assert "pol_claim_003" in content
    assert "pol_num_004" in content

    # Populates version history
    assert "INSERT INTO policy_card_versions" in content


def test_docker_compose_configuration() -> None:
    """Verify docker-compose.yml defines PostgreSQL container on port 5433 with schema mounts."""
    assert DOCKER_COMPOSE_PATH.exists(), "docker-compose.yml not found"
    content = DOCKER_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "postgres:16-alpine" in content
    assert "5433:5432" in content
    assert "01_schema.sql" in content
    assert "02_seed.sql" in content


def test_schema_defines_scan_id_uniqueness_constraints() -> None:
    """Verify schema.sql defines named UNIQUE constraints for reviews.scan_id and passports.scan_id."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    # reviews table scan_id uniqueness
    assert "CONSTRAINT uq_reviews_scan_id UNIQUE (scan_id)" in content, (
        "Expected named constraint 'uq_reviews_scan_id' in reviews table definition"
    )

    # passports table scan_id uniqueness
    assert "CONSTRAINT uq_passports_scan_id UNIQUE (scan_id)" in content, (
        "Expected named constraint 'uq_passports_scan_id' in passports table definition"
    )

    # passports table review_id uniqueness preserved
    assert "review_id UUID NOT NULL UNIQUE REFERENCES reviews(id)" in content, (
        "Expected passports.review_id to retain its UNIQUE constraint"
    )

    # No redundant index on reviews(scan_id)
    assert "idx_reviews_scan_id" not in content, (
        "Redundant index idx_reviews_scan_id should be omitted when uq_reviews_scan_id is defined"
    )


def test_migration_001_file_exists_and_enforces_rules() -> None:
    """Verify migration 001 exists, is repeatable, and uses safe non-destructive checks."""
    assert MIGRATION_PATH.exists(), f"Migration file not found at {MIGRATION_PATH}"
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    # Constraint names match schema.sql
    assert "uq_reviews_scan_id" in content
    assert "uq_passports_scan_id" in content

    # Precondition duplicate detection
    assert "HAVING COUNT(*) > 1" in content
    assert "RAISE EXCEPTION" in content

    # Catalog check idempotency
    assert "pg_constraint" in content
    assert "DO $$" in content

    # Drops redundant non-unique index if present
    assert "idx_reviews_scan_id" in content
