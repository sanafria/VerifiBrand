"""Unit tests for Merkle Anchor DAO and Provider — Phase 3.3A (Member 6).

All tests in this file are database-free unit tests.  To avoid pulling in the
full backend dependency chain (asyncpg, dateutil, etc.) we import
merkle_anchor.py and anchor_provider.py directly via importlib rather than
going through backend.app.services.__init__.

Async DAO functions are tested using asyncio.run() so that pytest-asyncio is
not required.

If any future test requires a live database it MUST be marked:
    @pytest.mark.integration
and excluded from the default unit-test run.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Direct module loading helpers (bypass __init__.py import chain)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent  # .../BrandLedger


def _load_module(rel_path: str, name: str):
    """Load a Python module directly from its file path without going through __init__."""
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_anchor_provider():
    return _load_module(
        "backend/app/services/anchor_provider.py",
        "anchor_provider_isolated",
    )


def _make_db_mock() -> MagicMock:
    """Return a MagicMock that matches the db_manager interface."""
    mock = MagicMock()
    mock.is_connected = True
    mock.connect = AsyncMock()
    mock.fetchrow = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value="OK")
    return mock


def _load_merkle_anchor_with_mock_db() -> tuple:
    """Load merkle_anchor module with a pre-injected mock db_manager.

    Returns (module, mock_db).
    """
    # Build a fake 'backend.app.db' module so merkle_anchor.py can import it
    fake_db_mod = types.ModuleType("backend.app.db")
    mock_db = _make_db_mock()
    fake_db_mod.db_manager = mock_db

    # Ensure the package hierarchy exists in sys.modules
    for pkg in ("backend", "backend.app", "backend.app.db"):
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)
    sys.modules["backend.app.db"] = fake_db_mod

    mod = _load_module(
        "backend/app/services/merkle_anchor.py",
        f"merkle_anchor_isolated_{uuid.uuid4().hex[:6]}",
    )
    # Point the module's db_manager reference at our mock
    mod.db_manager = mock_db
    return mod, mock_db


import types  # noqa: E402  (must be after the forward reference above)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(
    anchor_id: Optional[str] = None,
    root_hash: str = "a" * 64,
    status: str = "pending",
    receipt: Optional[str] = None,
    receipt_source: str = "mock",
    failure_reason: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "anchor_id": anchor_id or str(uuid.uuid4()),
        "root_hash": root_hash,
        "status": status,
        "receipt": receipt,
        "receipt_source": receipt_source,
        "failure_reason": failure_reason,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# 1. Provider tests (no DB, no network)
# ---------------------------------------------------------------------------

class TestAnchorProvider:
    """Tests for anchor_provider.get_anchor_provider() factory."""

    def test_default_env_returns_mock(self):
        """With ANCHOR_ENV unset, factory returns MockAnchorProvider."""
        mod = _load_anchor_provider()
        env = {k: v for k, v in os.environ.items() if k != "ANCHOR_ENV"}
        with patch.dict(os.environ, env, clear=True):
            provider = mod.get_anchor_provider()
        assert type(provider).__name__ == "MockAnchorProvider"

    def test_test_env_returns_mock(self):
        """ANCHOR_ENV=test returns MockAnchorProvider."""
        mod = _load_anchor_provider()
        with patch.dict(os.environ, {"ANCHOR_ENV": "test"}):
            provider = mod.get_anchor_provider()
        assert type(provider).__name__ == "MockAnchorProvider"

    def test_production_raises_not_implemented(self):
        """ANCHOR_ENV=production must raise NotImplementedError."""
        mod = _load_anchor_provider()
        with patch.dict(os.environ, {"ANCHOR_ENV": "production"}):
            with pytest.raises(NotImplementedError, match="not configured for production"):
                mod.get_anchor_provider()

    def test_unknown_env_fails_closed(self):
        """Unknown ANCHOR_ENV values must raise ValueError (fail-closed).

        Note: 'PRODUCTION' normalises to 'production' which raises
        NotImplementedError (also a closed failure, not a silent mock fallback).
        Both are accepted here.
        """
        mod = _load_anchor_provider()
        # Values that should raise ValueError (genuinely unknown)
        for bad in ("prod", "staging", "mock", "test2"):
            with patch.dict(os.environ, {"ANCHOR_ENV": bad}):
                with pytest.raises(ValueError, match="Unknown ANCHOR_ENV"):
                    mod.get_anchor_provider()

        # 'PRODUCTION' → normalises to 'production' → NotImplementedError (still fail-closed)
        with patch.dict(os.environ, {"ANCHOR_ENV": "PRODUCTION"}):
            with pytest.raises((ValueError, NotImplementedError)):
                mod.get_anchor_provider()

    def test_empty_string_env_fails_closed(self):
        """Empty ANCHOR_ENV string must also raise ValueError."""
        mod = _load_anchor_provider()
        with patch.dict(os.environ, {"ANCHOR_ENV": "   "}):
            with pytest.raises(ValueError, match="Unknown ANCHOR_ENV"):
                mod.get_anchor_provider()

    def test_mock_receipt_is_clearly_synthetic(self):
        """Mock provider receipt values are deterministic and contain 'mock'."""
        mod = _load_anchor_provider()
        with patch.dict(os.environ, {"ANCHOR_ENV": "test"}):
            provider = mod.get_anchor_provider()
        root = "b" * 64
        result = provider.anchor(root)
        assert result["external_id"] == f"mock-{root[:8]}"
        assert "mock" in result["receipt"]


# ---------------------------------------------------------------------------
# 2. DAO tests (mocked db_manager, no asyncpg)
# ---------------------------------------------------------------------------

class TestCreateAnchor:

    def test_successful_insert_returns_row(self):
        """A fresh root_hash is inserted and the new row is returned."""
        mod, db = _load_merkle_anchor_with_mock_db()
        expected = _row(root_hash="a" * 64, receipt_source="mock")
        db.fetchrow = AsyncMock(return_value=expected)

        result = asyncio.run(mod.create_anchor(root_hash="a" * 64, receipt_source="mock"))
        assert result["status"] == "pending"
        assert result["root_hash"] == "a" * 64
        assert result["receipt_source"] == "mock"

    def test_duplicate_root_returns_existing_row(self):
        """ON CONFLICT DO NOTHING → fetchrow returns None → re-fetch returns existing."""
        mod, db = _load_merkle_anchor_with_mock_db()
        existing = _row(root_hash="a" * 64, status="pending", receipt_source="mock")
        db.fetchrow = AsyncMock(side_effect=[None, existing])

        result = asyncio.run(mod.create_anchor(root_hash="a" * 64, receipt_source="mock"))
        assert result["status"] == "pending"
        assert db.fetchrow.call_count == 2

    def test_invalid_root_hash_raises_before_db(self):
        """root_hash that is not 64 hex chars must raise ValueError before any DB call."""
        mod, db = _load_merkle_anchor_with_mock_db()
        with pytest.raises(ValueError, match="64-character hex"):
            asyncio.run(mod.create_anchor(root_hash="tooshort", receipt_source="mock"))
        db.fetchrow.assert_not_called()

    def test_invalid_receipt_source_raises_before_db(self):
        """receipt_source values other than 'mock'/'real' must raise ValueError."""
        mod, db = _load_merkle_anchor_with_mock_db()
        with pytest.raises(ValueError, match="receipt_source"):
            asyncio.run(mod.create_anchor(root_hash="a" * 64, receipt_source="production"))
        db.fetchrow.assert_not_called()


class TestUpdateAnchorStatus:

    def test_mock_receipt_cannot_become_anchored(self):
        """receipt_source='mock' row must not transition to 'anchored'."""
        mod, db = _load_merkle_anchor_with_mock_db()
        aid = str(uuid.uuid4())
        existing = _row(anchor_id=aid, status="pending", receipt_source="mock")
        db.fetchrow = AsyncMock(return_value=existing)

        with pytest.raises(ValueError, match="mock receipt cannot be promoted"):
            asyncio.run(mod.update_anchor_status(anchor_id=aid, new_status="anchored"))
        # UPDATE must not have been called (only the SELECT for get_anchor_by_id)
        assert db.fetchrow.call_count == 1

    def test_valid_transition_pending_to_failed(self):
        """pending → failed stores the failure_reason."""
        mod, db = _load_merkle_anchor_with_mock_db()
        aid = str(uuid.uuid4())
        existing = _row(anchor_id=aid, status="pending", receipt_source="mock")
        updated = _row(anchor_id=aid, status="failed", receipt_source="mock",
                       failure_reason="provider_timeout")
        db.fetchrow = AsyncMock(side_effect=[existing, updated])

        result = asyncio.run(
            mod.update_anchor_status(anchor_id=aid, new_status="failed",
                                     failure_reason="provider_timeout")
        )
        assert result["status"] == "failed"
        assert result["failure_reason"] == "provider_timeout"

    def test_anchored_is_terminal(self):
        """No transition is permitted out of 'anchored' (terminal state)."""
        mod, db = _load_merkle_anchor_with_mock_db()
        aid = str(uuid.uuid4())
        existing = _row(anchor_id=aid, status="anchored",
                        receipt_source="real", receipt="real-receipt")
        db.fetchrow = AsyncMock(return_value=existing)

        with pytest.raises(ValueError, match="terminal state"):
            asyncio.run(mod.update_anchor_status(anchor_id=aid, new_status="pending"))

    def test_invalid_status_rejected_immediately(self):
        """An unrecognised target status raises ValueError before any DB lookup."""
        mod, db = _load_merkle_anchor_with_mock_db()
        with pytest.raises(ValueError, match="Invalid status"):
            asyncio.run(
                mod.update_anchor_status(anchor_id=str(uuid.uuid4()),
                                         new_status="unknown_state")
            )
        db.fetchrow.assert_not_called()

    def test_failure_reason_cleared_on_retry(self):
        """failed → pending (retry) clears failure_reason."""
        mod, db = _load_merkle_anchor_with_mock_db()
        aid = str(uuid.uuid4())
        existing = _row(anchor_id=aid, status="failed", receipt_source="mock",
                        failure_reason="previous_error")
        updated = _row(anchor_id=aid, status="pending", receipt_source="mock",
                       failure_reason=None)
        db.fetchrow = AsyncMock(side_effect=[existing, updated])

        result = asyncio.run(
            mod.update_anchor_status(anchor_id=aid, new_status="pending")
        )
        assert result["status"] == "pending"
        assert result["failure_reason"] is None

    def test_new_failure_reason_stored_on_second_failure(self):
        """pending → failed with a new reason stores that reason."""
        mod, db = _load_merkle_anchor_with_mock_db()
        aid = str(uuid.uuid4())
        existing = _row(anchor_id=aid, status="pending", receipt_source="mock")
        updated = _row(anchor_id=aid, status="failed", receipt_source="mock",
                       failure_reason="new_error")
        db.fetchrow = AsyncMock(side_effect=[existing, updated])

        result = asyncio.run(
            mod.update_anchor_status(anchor_id=aid, new_status="failed",
                                     failure_reason="new_error")
        )
        assert result["failure_reason"] == "new_error"

    def test_missing_anchor_raises_lookup_error(self):
        """LookupError is raised when the anchor_id does not exist."""
        mod, db = _load_merkle_anchor_with_mock_db()
        db.fetchrow = AsyncMock(return_value=None)

        with pytest.raises(LookupError, match="No anchor found"):
            asyncio.run(
                mod.update_anchor_status(anchor_id=str(uuid.uuid4()),
                                         new_status="failed")
            )


class TestGetLatestAnchor:

    def test_returns_none_when_table_empty(self):
        """get_latest_anchor returns None when no rows exist."""
        mod, db = _load_merkle_anchor_with_mock_db()
        db.fetchrow = AsyncMock(return_value=None)
        result = asyncio.run(mod.get_latest_anchor())
        assert result is None

    def test_returns_most_recent_row(self):
        """get_latest_anchor returns the dict from db_manager.fetchrow."""
        mod, db = _load_merkle_anchor_with_mock_db()
        expected = _row(status="pending")
        db.fetchrow = AsyncMock(return_value=expected)
        result = asyncio.run(mod.get_latest_anchor())
        assert result is not None
        assert result["status"] == "pending"


# ---------------------------------------------------------------------------
# Schema note (integration test placeholder — skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "Integration test: requires a live PostgreSQL database with the schema applied. "
        "Run manually: psql -f database/schema.sql && pytest -m integration"
    )
)
def test_schema_merkle_anchors_table_exists():
    """INTEGRATION: Verify merkle_anchors table exists after applying database/schema.sql."""
    pass
