"""Automated Unit and Contract Tests for BrandLedger Publication Gate Action (Member 6).

Verifies:
1. Complete secret masking (never printing any secret characters).
2. Input validation for UUIDs, timeouts (positive numeric only), and URLs.
3. Strict workspace path containment for content files (rejecting absolute paths,
   directory traversal via '..', and symlink escapes).
4. HMAC-SHA256 signature generation matching the authoritative backend contract.
5. Successful gate evaluation (PASS) setting outputs and returning exit code 0.
6. Gate violation evaluation (BLOCK) triggering exit code 1 when fail_on_block=True.
7. Gate violation evaluation (BLOCK) returning exit code 0 when fail_on_block=False.
8. HTTP 401 Unauthorized handling (invalid or mismatched signature).
9. HTTP 409 Conflict handling (reused event_id with different payload).
10. Network failure / connection error handling.
11. Timeout handling.
12. Malformed non-JSON backend responses setting decision=BLOCK and reason=MALFORMED_RESPONSE.
13. Early configuration and signing errors setting decision=BLOCK and machine-readable reasons.
14. GitHub Step Summary Markdown generation with verbatim policy citations.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import uuid

# Import runner module under test
import importlib.util

RUNNER_PATH = Path(__file__).parent / "runner.py"
spec = importlib.util.spec_from_file_location("runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TestPublicationGateRunner(unittest.TestCase):
    """Comprehensive test suite for reusable publication gate GitHub Action runner."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self.temp_dir.name) / "workspace"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = Path(self.temp_dir.name) / "github_output.txt"
        self.summary_file = Path(self.temp_dir.name) / "github_step_summary.md"

        os.environ["GITHUB_WORKSPACE"] = str(self.workspace_dir)
        os.environ["GITHUB_OUTPUT"] = str(self.output_file)
        os.environ["GITHUB_STEP_SUMMARY"] = str(self.summary_file)

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("GITHUB_WORKSPACE", None)
        os.environ.pop("GITHUB_OUTPUT", None)
        os.environ.pop("GITHUB_STEP_SUMMARY", None)

    # =========================================================================
    # 1. Secret Masking (Fix 3: Never print any secret characters)
    # =========================================================================

    def test_mask_secret_fully_redacts(self):
        """Verify secrets are completely masked as [CONFIGURED] without leaking any characters."""
        self.assertEqual(runner.mask_secret(None), "<unset>")
        self.assertEqual(runner.mask_secret(""), "<unset>")
        self.assertEqual(runner.mask_secret("   "), "<unset>")
        self.assertEqual(runner.mask_secret("short"), "[CONFIGURED]")
        self.assertEqual(runner.mask_secret("super_secret_webhook_key_12345"), "[CONFIGURED]")

        # Confirm neither first nor last characters appear in diagnostic string
        masked = runner.mask_secret("production_secret_key_999")
        self.assertNotIn("prod", masked)
        self.assertNotIn("999", masked)
        self.assertEqual(masked, "[CONFIGURED]")

    # =========================================================================
    # 2. Input Validation: UUIDs & Timeouts (Fix 5)
    # =========================================================================

    def test_validate_uuid_success(self):
        valid = str(uuid.uuid4())
        self.assertEqual(runner.validate_uuid(valid, "draft_id"), valid)
        self.assertIsNone(runner.validate_uuid("", "draft_id"))
        self.assertIsNone(runner.validate_uuid(None, "draft_id"))

    def test_validate_uuid_invalid_raises(self):
        with self.assertRaises(ValueError) as ctx:
            runner.validate_uuid("not-a-valid-uuid", "draft_id")
        self.assertIn("must be a valid UUID", str(ctx.exception))
        self.assertIn("draft_id", str(ctx.exception))

    def test_validate_timeout_valid_positive(self):
        """Verify positive numbers and defaults are accepted."""
        self.assertEqual(runner.validate_timeout("10"), 10.0)
        self.assertEqual(runner.validate_timeout("30.5"), 30.5)
        self.assertEqual(runner.validate_timeout(15), 15.0)
        self.assertEqual(runner.validate_timeout(None), 30.0)
        self.assertEqual(runner.validate_timeout(""), 30.0)

    def test_validate_timeout_rejects_zero(self):
        """Verify zero timeout is rejected with configuration error."""
        with self.assertRaises(ValueError) as ctx:
            runner.validate_timeout("0")
        self.assertIn("must be greater than zero", str(ctx.exception))

    def test_validate_timeout_rejects_negative(self):
        """Verify negative timeout is rejected with configuration error."""
        with self.assertRaises(ValueError) as ctx:
            runner.validate_timeout("-5")
        self.assertIn("must be greater than zero", str(ctx.exception))

    def test_validate_timeout_rejects_non_numeric(self):
        """Verify non-numeric input is rejected with configuration error."""
        with self.assertRaises(ValueError) as ctx:
            runner.validate_timeout("invalid_timeout_str")
        self.assertIn("must be a positive number", str(ctx.exception))

    # =========================================================================
    # 3. Workspace Path Containment (Fix 4)
    # =========================================================================

    def test_workspace_path_containment_valid_relative(self):
        """Legitimate relative path inside workspace is read correctly."""
        rel_file = self.workspace_dir / "campaigns" / "launch.md"
        rel_file.parent.mkdir(parents=True, exist_ok=True)
        rel_file.write_text("# Launch Banner\n\nWelcome Members!", encoding="utf-8")

        content = runner.read_content_file("campaigns/launch.md", workspace_root=str(self.workspace_dir))
        self.assertEqual(content, "# Launch Banner\n\nWelcome Members!")

    def test_workspace_path_containment_rejects_absolute_path(self):
        """Absolute paths must be rejected upfront."""
        with self.assertRaises(ValueError) as ctx:
            runner.read_content_file("/etc/passwd", workspace_root=str(self.workspace_dir))
        self.assertIn("Absolute paths are not permitted", str(ctx.exception))

    def test_workspace_path_containment_rejects_parent_traversal(self):
        """Paths escaping workspace via '..' must be rejected."""
        with self.assertRaises(ValueError) as ctx:
            runner.read_content_file("../../outside.txt", workspace_root=str(self.workspace_dir))
        self.assertIn("resolves outside the repository workspace root", str(ctx.exception))

    def test_workspace_path_containment_rejects_symlink_escape(self):
        """Symlinks pointing to targets outside workspace must be rejected."""
        outside_file = Path(self.temp_dir.name) / "outside_target.txt"
        outside_file.write_text("outside secret content", encoding="utf-8")

        symlink_path = self.workspace_dir / "symlink_escape.txt"
        try:
            symlink_path.symlink_to(outside_file)
        except OSError:
            self.skipTest("Symlinks not supported on this filesystem.")

        with self.assertRaises(ValueError) as ctx:
            runner.read_content_file("symlink_escape.txt", workspace_root=str(self.workspace_dir))
        self.assertIn("resolves outside the repository workspace root", str(ctx.exception))

    def test_read_content_file_missing_raises_file_not_found(self):
        """Relative path that stays in workspace but does not exist raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError) as ctx:
            runner.read_content_file("nonexistent.txt", workspace_root=str(self.workspace_dir))
        self.assertIn("Content file not found", str(ctx.exception))

    # =========================================================================
    # 4. Payload Construction & HMAC Contract
    # =========================================================================

    def test_build_gate_payload_minimal(self):
        payload, raw_bytes = runner.build_gate_payload(
            event_id="evt_test_123",
            draft_id=None,
            passport_id=None,
            scan_id=None,
            content_text=None,
        )
        self.assertEqual(payload["event_id"], "evt_test_123")
        self.assertEqual(raw_bytes, b'{"event_id":"evt_test_123"}')

    def test_build_gate_payload_full(self):
        draft_id = str(uuid.uuid4())
        passport_id = str(uuid.uuid4())
        scan_id = str(uuid.uuid4())
        payload, raw_bytes = runner.build_gate_payload(
            event_id="evt_full_001",
            draft_id=draft_id,
            passport_id=passport_id,
            scan_id=scan_id,
            content_text="Welcome Members to our approved launch!",
        )
        self.assertEqual(payload["event_id"], "evt_full_001")
        self.assertEqual(payload["draft_id"], draft_id)
        self.assertEqual(payload["passport_id"], passport_id)
        self.assertEqual(payload["scan_id"], scan_id)
        self.assertEqual(payload["content_text"], "Welcome Members to our approved launch!")
        self.assertEqual(json.loads(raw_bytes.decode("utf-8")), payload)

    def test_build_gate_payload_auto_generates_event_id(self):
        payload, _ = runner.build_gate_payload(
            event_id=None,
            draft_id=str(uuid.uuid4()),
            passport_id=None,
            scan_id=None,
            content_text=None,
        )
        self.assertTrue(payload["event_id"].startswith("gha_"))

    def test_compute_hmac_signature(self):
        secret = "ci_test_webhook_secret_32_characters_long_min"
        raw_body = b'{"event_id":"evt_12345","draft_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6"}'

        sig = runner.compute_hmac_signature(raw_body, secret)
        self.assertTrue(sig.startswith("sha256="))
        self.assertEqual(len(sig[7:]), 64)

        try:
            from backend.app.services.gate_service import verify_hmac_signature
            is_valid = verify_hmac_signature(raw_body=raw_body, signature_header=sig, secret=secret)
            self.assertTrue(is_valid, "Signature must pass backend verify_hmac_signature")
        except (ImportError, ModuleNotFoundError):
            pass

    def test_compute_hmac_signature_empty_secret_raises(self):
        with self.assertRaises(ValueError) as ctx:
            runner.compute_hmac_signature(b"{}", "")
        self.assertIn("HMAC Secret is empty", str(ctx.exception))

    # =========================================================================
    # 5. Output Consistency on Failures (Fix 1)
    # =========================================================================

    def test_execute_gate_configuration_error_sets_outputs(self):
        """Invalid UUID input writes decision=BLOCK and reason=CONFIGURATION_ERROR."""
        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_min_here_0000",
            draft_id="not-a-valid-uuid",
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "CONFIGURATION_ERROR")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)
        self.assertIn("reason=CONFIGURATION_ERROR", output_content)

    def test_execute_gate_invalid_timeout_sets_outputs(self):
        """Invalid timeout value writes decision=BLOCK and reason=INVALID_TIMEOUT."""
        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_min_here_0000",
            draft_id=str(uuid.uuid4()),
            timeout_seconds=-10.0,
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "INVALID_TIMEOUT")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)
        self.assertIn("reason=INVALID_TIMEOUT", output_content)

    def test_execute_gate_signing_error_sets_outputs(self):
        """Blank secret writes decision=BLOCK and reason=SIGNING_ERROR."""
        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="",
            draft_id=str(uuid.uuid4()),
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "SIGNING_ERROR")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)
        self.assertIn("reason=SIGNING_ERROR", output_content)

    def test_execute_gate_invalid_backend_url_sets_outputs(self):
        """Malformed backend URL without http/https writes decision=BLOCK."""
        exit_code, data = runner.execute_publication_gate(
            backend_url="ftp://invalid.url.com",
            webhook_secret="test_secret_32_chars_min_here_0000",
            draft_id=str(uuid.uuid4()),
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "CONFIGURATION_ERROR")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)
        self.assertIn("reason=CONFIGURATION_ERROR", output_content)

    @patch("urllib.request.urlopen")
    def test_execute_gate_malformed_response_sets_outputs(self, mock_urlopen):
        """Non-JSON response writes decision=BLOCK and reason=MALFORMED_RESPONSE."""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = b"<html>502 Bad Gateway</html>"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_min_here_0000",
            draft_id=str(uuid.uuid4()),
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "MALFORMED_RESPONSE")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)
        self.assertIn("reason=MALFORMED_RESPONSE", output_content)

    # =========================================================================
    # 6. End-to-End PASS & BLOCK Flows
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_pass(self, mock_urlopen):
        draft_id = str(uuid.uuid4())
        passport_id = str(uuid.uuid4())

        pass_response = {
            "event_id": "evt_pass_001",
            "decision": "PASS",
            "status_code": 200,
            "reason": "PUBLICATION_AUTHORIZED",
            "explanation": "Content draft is approved, zero active blockers detected, and Content Passport verified.",
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
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_minimum_here",
            event_id="evt_pass_001",
            draft_id=draft_id,
            passport_id=passport_id,
            fail_on_block=True,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["decision"], "PASS")
        self.assertEqual(data["reason"], "PUBLICATION_AUTHORIZED")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=PASS", output_content)
        self.assertIn("reason=PUBLICATION_AUTHORIZED", output_content)

        summary_content = self.summary_file.read_text(encoding="utf-8")
        self.assertIn("Authorized (PASS)", summary_content)

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_block_fail_on_block_true(self, mock_urlopen):
        draft_id = str(uuid.uuid4())
        block_response = {
            "event_id": "evt_block_001",
            "decision": "BLOCK",
            "status_code": 200,
            "reason": "ACTIVE_BLOCKING_FINDINGS",
            "explanation": "Compliance scan contains 1 active blocking violation(s).",
            "draft_id": draft_id,
            "total_blockers": 1,
            "duplicate": False,
            "findings": [
                {
                    "policy_card_id": "pol_term_001",
                    "policy_version": "1.0",
                    "category": "terminology",
                    "severity": "blocker",
                    "matched_text": "customers",
                    "source_quote": "The brand prohibits the term 'Customers' and requires 'Members'.",
                    "explanation": "Disallowed term 'customers' detected.",
                    "suggested_fix": "Replace with 'Members'",
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps(block_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_minimum_here",
            event_id="evt_block_001",
            draft_id=draft_id,
            fail_on_block=True,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "ACTIVE_BLOCKING_FINDINGS")

        summary_content = self.summary_file.read_text(encoding="utf-8")
        self.assertIn("Blocked (BLOCK)", summary_content)
        self.assertIn("pol_term_001 v1.0", summary_content)
        self.assertIn("Replace with 'Members'", summary_content)

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_block_fail_on_block_false(self, mock_urlopen):
        block_response = {
            "event_id": "evt_block_002",
            "decision": "BLOCK",
            "status_code": 200,
            "reason": "DRAFT_NOT_APPROVED",
            "explanation": "Content draft requires human approval.",
            "draft_id": str(uuid.uuid4()),
            "total_blockers": 0,
            "findings": [],
        }

        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps(block_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="test_secret_32_chars_minimum_here",
            event_id="evt_block_002",
            draft_id=block_response["draft_id"],
            fail_on_block=False,
        )

        self.assertEqual(exit_code, 0, "BLOCK with fail_on_block=False must exit with code 0")
        self.assertEqual(data["decision"], "BLOCK")

        output_content = self.output_file.read_text(encoding="utf-8")
        self.assertIn("decision=BLOCK", output_content)

    # =========================================================================
    # 7. HTTP & Network Error Handling
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_http_401_unauthorized(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8000/api/gate/publish",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"detail":"Unauthorized: Invalid HMAC-SHA256 webhook signature."}'),
        )
        mock_urlopen.side_effect = mock_err

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="wrong_secret_here_32_characters",
            event_id="evt_unauth_001",
            draft_id=str(uuid.uuid4()),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "HTTP_401")
        self.assertIn("Invalid HMAC-SHA256", data["explanation"])

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_http_409_conflict(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8000/api/gate/publish",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=io.BytesIO(b'{"detail":"Conflict: Event ID has already been processed with a different payload."}'),
        )
        mock_urlopen.side_effect = mock_err

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="secret_32_characters_minimum_0000",
            event_id="evt_reused_conflict",
            draft_id=str(uuid.uuid4()),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "HTTP_409")

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:9999",
            webhook_secret="secret_32_characters_minimum_0000",
            event_id="evt_net_001",
            draft_id=str(uuid.uuid4()),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "NETWORK_ERROR")

    @patch("urllib.request.urlopen")
    def test_execute_publication_gate_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Request timed out")

        exit_code, data = runner.execute_publication_gate(
            backend_url="http://127.0.0.1:8000",
            webhook_secret="secret_32_characters_minimum_0000",
            event_id="evt_time_001",
            draft_id=str(uuid.uuid4()),
            timeout_seconds=5.0,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["decision"], "BLOCK")
        self.assertEqual(data["reason"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
