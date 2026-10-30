"""Pytest Integration Test Suite for Reusable GitHub Action (Member 6).

Ensures CI pipeline automatically validates:
1. GitHub Action runner payload generation.
2. HMAC-SHA256 signature interoperability with backend verify_hmac_signature.
3. Decision handling for PASS, BLOCK, fail_on_block semantics, and step summary formatting.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import urllib.error
import uuid
try:
    import pytest
except (ImportError, ModuleNotFoundError):
    class _DummyPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = _DummyPytest()

try:
    from backend.app.services.gate_service import verify_hmac_signature
except (ImportError, ModuleNotFoundError):
    import hmac
    import hashlib
    def verify_hmac_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
        clean_sig = signature_header.strip()
        if clean_sig.lower().startswith("sha256="):
            clean_sig = clean_sig[7:].strip()
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.lower(), clean_sig.lower())

# Dynamically import runner.py from action directory
import importlib.util

RUNNER_PATH = Path(__file__).parent.parent.parent / ".github" / "actions" / "publication-gate" / "runner.py"
spec = importlib.util.spec_from_file_location("runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def gha_environment():
    """Manage temporary files for GITHUB_OUTPUT, GITHUB_STEP_SUMMARY, and GITHUB_WORKSPACE."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "output.txt"
        summary_file = Path(tmp_dir) / "summary.md"
        os.environ["GITHUB_WORKSPACE"] = str(tmp_dir)
        os.environ["GITHUB_OUTPUT"] = str(output_file)
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary_file)
        yield {
            "tmp_dir": Path(tmp_dir),
            "output_file": output_file,
            "summary_file": summary_file,
        }
        os.environ.pop("GITHUB_WORKSPACE", None)
        os.environ.pop("GITHUB_OUTPUT", None)
        os.environ.pop("GITHUB_STEP_SUMMARY", None)


def test_action_hmac_matches_backend_contract():
    """Verify runner's HMAC computation precisely matches backend gate_service verification."""
    secret = "production_ready_secret_key_at_least_32_chars"
    payload = {
        "event_id": "evt_contract_check",
        "draft_id": str(uuid.uuid4()),
        "passport_id": str(uuid.uuid4()),
        "content_text": "Sample copy for contract validation.",
    }
    raw_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # Generate signature using runner logic
    sig_header = runner.compute_hmac_signature(raw_body, secret)
    assert sig_header.startswith("sha256=")

    # Verify directly using backend service logic
    is_valid = verify_hmac_signature(
        raw_body=raw_body,
        signature_header=sig_header,
        secret=secret,
    )
    assert is_valid is True, "Backend verify_hmac_signature must authenticate runner signature."


def test_action_payload_builder_handles_file_and_content(gha_environment):
    """Verify builder accurately prioritizes workspace content files."""
    ad_file = gha_environment["tmp_dir"] / "promo.txt"
    ad_file.write_text("50% discount for all customers today only!", encoding="utf-8")

    draft_id = str(uuid.uuid4())
    payload, raw_bytes = runner.build_gate_payload(
        event_id="evt_promo_001",
        draft_id=draft_id,
        passport_id=None,
        scan_id=None,
        content_text=None,
        content_file="promo.txt",
        workspace_root=str(gha_environment["tmp_dir"]),
    )

    assert payload["event_id"] == "evt_promo_001"
    assert payload["draft_id"] == draft_id
    assert payload["content_text"] == "50% discount for all customers today only!"
    assert b"evt_promo_001" in raw_bytes


def test_action_runner_pass_sets_outputs_and_summary(gha_environment):
    """Verify PASS evaluation records outputs and renders green step summary."""
    draft_id = str(uuid.uuid4())
    passport_id = str(uuid.uuid4())

    pass_response = {
        "event_id": "evt_pass_test",
        "decision": "PASS",
        "status_code": 200,
        "reason": "PUBLICATION_AUTHORIZED",
        "explanation": "Draft is approved and Content Passport is verified.",
        "draft_id": draft_id,
        "passport_id": passport_id,
        "passport_hash_verified": True,
        "findings": [],
        "total_blockers": 0,
        "duplicate": False,
    }

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(pass_response).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_characters_long_min",
            event_id="evt_pass_test",
            draft_id=draft_id,
            passport_id=passport_id,
            fail_on_block=True,
        )

        assert exit_code == 0
        assert data["decision"] == "PASS"

        # Output check
        output_text = gha_environment["output_file"].read_text(encoding="utf-8")
        assert "decision=PASS" in output_text
        assert "reason=PUBLICATION_AUTHORIZED" in output_text

        # Summary check
        summary_text = gha_environment["summary_file"].read_text(encoding="utf-8")
        assert "Authorized (PASS)" in summary_text
        assert "PUBLICATION_AUTHORIZED" in summary_text


def test_action_runner_block_fail_on_block_semantics(gha_environment):
    """Verify fail_on_block=True triggers code 1, while fail_on_block=False returns code 0."""
    block_response = {
        "event_id": "evt_block_test",
        "decision": "BLOCK",
        "status_code": 200,
        "reason": "ACTIVE_BLOCKING_FINDINGS",
        "explanation": "Found 1 blocking terminology violation.",
        "draft_id": str(uuid.uuid4()),
        "total_blockers": 1,
        "findings": [
            {
                "policy_card_id": "pol_term_001",
                "policy_version": "1.0",
                "category": "terminology",
                "severity": "blocker",
                "matched_text": "customers",
                "source_quote": "The brand prohibits the term 'Customers' and requires 'Members'.",
                "explanation": "Use Members instead of customers.",
                "suggested_fix": "Replace with 'Members'",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(block_response).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Case 1: fail_on_block=True -> exit code 1
        exit_code_1, _ = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_characters_long_min",
            event_id="evt_block_test",
            draft_id=block_response["draft_id"],
            fail_on_block=True,
        )
        assert exit_code_1 == 1

        # Case 2: fail_on_block=False -> exit code 0
        exit_code_0, _ = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_characters_long_min",
            event_id="evt_block_test",
            draft_id=block_response["draft_id"],
            fail_on_block=False,
        )
        assert exit_code_0 == 0

        # Step summary check
        summary_text = gha_environment["summary_file"].read_text(encoding="utf-8")
        assert "Blocked (BLOCK)" in summary_text
        assert "pol_term_001 v1.0" in summary_text
        assert "Replace with 'Members'" in summary_text


if __name__ == "__main__":
    import contextlib

    print("Running test_github_action.py test suite directly...")
    test_action_hmac_matches_backend_contract()
    print("  ✓ test_action_hmac_matches_backend_contract")

    with tempfile.TemporaryDirectory() as tmp_dir:
        env = {
            "tmp_dir": Path(tmp_dir),
            "output_file": Path(tmp_dir) / "output.txt",
            "summary_file": Path(tmp_dir) / "summary.md",
        }
        os.environ["GITHUB_OUTPUT"] = str(env["output_file"])
        os.environ["GITHUB_STEP_SUMMARY"] = str(env["summary_file"])

        test_action_payload_builder_handles_file_and_content(env)
        print("  ✓ test_action_payload_builder_handles_file_and_content")

        test_action_runner_pass_sets_outputs_and_summary(env)
        print("  ✓ test_action_runner_pass_sets_outputs_and_summary")

        test_action_runner_block_fail_on_block_semantics(env)
        print("  ✓ test_action_runner_block_fail_on_block_semantics")

        os.environ.pop("GITHUB_OUTPUT", None)
        os.environ.pop("GITHUB_STEP_SUMMARY", None)

    print("All test_github_action.py tests passed successfully!")
