#!/usr/bin/env python3
"""Reusable GitHub Action Runner for BrandLedger Publication Gate (Member 6).

Responsibilities:
1. Parse action inputs from environment variables or command-line arguments.
2. Read content files if specified (e.g. content_file), strictly enforcing workspace path containment.
3. Construct exact PublishGateRequest payload per backend/app/schemas/gate.py.
4. Compute HMAC-SHA256 signature using constant-time verified contract.
5. Invoke POST /api/gate/publish with exact raw-body bytes and X-BrandLedger-Signature header.
6. Parse PublishGateResponse, extract decision, reason, and verbatim evidence citations.
7. Write structured outputs to $GITHUB_OUTPUT on BOTH successes and failures.
8. Append formatted Markdown receipts to $GITHUB_STEP_SUMMARY.
9. Enforce fail_on_block behavior (exit code 1 on BLOCK when enabled, 0 when disabled).
10. Strict security: Never log secrets, private keys, or full signatures.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple


def mask_secret(val: Optional[str]) -> str:
    """Safely mask sensitive strings for diagnostic reporting without leaking any characters."""
    if not val or not val.strip():
        return "<unset>"
    return "[CONFIGURED]"


def validate_uuid(val: Optional[str], field_name: str) -> Optional[str]:
    """Validate that a string conforms to UUID format if provided."""
    if not val or not val.strip():
        return None
    cleaned = val.strip()
    try:
        uuid_obj = uuid.UUID(cleaned)
        return str(uuid_obj)
    except (ValueError, AttributeError):
        raise ValueError(
            f"Invalid configuration: '{field_name}' must be a valid UUID. Received: '{cleaned}'"
        )


def validate_timeout(val: Any) -> float:
    """Validate timeout_seconds input. Must be a positive numeric value (> 0)."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return 30.0

    raw_val = str(val).strip()
    try:
        timeout_float = float(raw_val)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid configuration: 'timeout_seconds' must be a positive number. Received: '{raw_val}'"
        )

    if timeout_float <= 0:
        raise ValueError(
            f"Invalid configuration: 'timeout_seconds' must be greater than zero. Received: {timeout_float}"
        )

    return timeout_float


def read_content_file(
    file_path: Optional[str],
    workspace_root: Optional[str] = None,
) -> Optional[str]:
    """Read content from workspace file if provided, strictly enforcing workspace containment.

    Rejects:
    - Absolute paths
    - Paths escaping workspace root via '..'
    - Symlinks pointing outside the workspace root
    """
    if not file_path or not file_path.strip():
        return None

    cleaned_path = file_path.strip()
    path_obj = Path(cleaned_path)

    # 1. Reject absolute paths upfront
    if path_obj.is_absolute():
        raise ValueError(
            f"Security boundary violation: Absolute paths are not permitted for 'content_file' ('{cleaned_path}'). "
            "Specify a relative path within the repository workspace."
        )

    # 2. Determine and resolve workspace root
    ws_raw = workspace_root or os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
    ws_canonical = Path(ws_raw).resolve()

    # 3. Resolve candidate path against canonical workspace root
    candidate_path = (ws_canonical / path_obj).resolve()

    # 4. Enforce workspace containment (canonical path must reside within ws_canonical)
    try:
        candidate_path.relative_to(ws_canonical)
    except ValueError:
        raise ValueError(
            f"Security boundary violation: Path '{cleaned_path}' resolves outside the repository workspace root."
        )

    # 5. Check file existence
    if not candidate_path.is_file():
        raise FileNotFoundError(
            f"Content file not found at path: '{cleaned_path}'."
        )

    with open(candidate_path, "r", encoding="utf-8") as f:
        return f.read()


def build_gate_payload(
    event_id: Optional[str],
    draft_id: Optional[str],
    passport_id: Optional[str],
    scan_id: Optional[str],
    content_text: Optional[str],
    content_file: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> Tuple[Dict[str, Any], bytes]:
    """Construct exact PublishGateRequest payload and canonical UTF-8 bytes."""
    # Resolve event ID: generate unique run-scoped ID if omitted
    resolved_event_id = event_id.strip() if event_id and event_id.strip() else None
    if not resolved_event_id:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        resolved_event_id = f"gha_{run_id}_{attempt}_{uuid.uuid4().hex[:8]}"

    # Validate UUIDs
    clean_draft_id = validate_uuid(draft_id, "draft_id")
    clean_passport_id = validate_uuid(passport_id, "passport_id")
    clean_scan_id = validate_uuid(scan_id, "scan_id")

    # Resolve content copy (file input takes precedence or supplements content_text)
    resolved_content = None
    if content_file:
        resolved_content = read_content_file(content_file, workspace_root=workspace_root)
    elif content_text and content_text.strip():
        resolved_content = content_text.strip()

    payload: Dict[str, Any] = {
        "event_id": resolved_event_id,
    }
    if clean_draft_id:
        payload["draft_id"] = clean_draft_id
    if clean_passport_id:
        payload["passport_id"] = clean_passport_id
    if clean_scan_id:
        payload["scan_id"] = clean_scan_id
    if resolved_content is not None:
        payload["content_text"] = resolved_content

    # Deterministic JSON serialization without whitespace
    body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return payload, body_bytes


def compute_hmac_signature(body_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature over exact raw request body bytes.

    Matches backend/app/services/gate_service.py:verify_hmac_signature contract.
    Returns format: 'sha256=<hex_digest>'
    """
    if not secret or not secret.strip():
        raise ValueError("HMAC Secret is empty. 'webhook_secret' input must not be blank.")

    sig_hex = hmac.new(
        secret.strip().encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={sig_hex}"


def write_github_output(name: str, value: Any) -> None:
    """Set a GitHub Action output variable in $GITHUB_OUTPUT."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    val_str = str(value)
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            if "\n" in val_str:
                delimiter = f"EOF_{uuid.uuid4().hex[:8]}"
                f.write(f"{name}<<{delimiter}\n{val_str}\n{delimiter}\n")
            else:
                f.write(f"{name}={val_str}\n")
    except Exception as exc:
        print(f"::warning::Failed writing output '{name}' to GITHUB_OUTPUT: {exc}", file=sys.stderr)


def write_step_summary(markdown_text: str) -> None:
    """Append formatted Markdown content to $GITHUB_STEP_SUMMARY."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown_text.rstrip() + "\n\n")
    except Exception as exc:
        print(f"::warning::Failed appending to GITHUB_STEP_SUMMARY: {exc}", file=sys.stderr)


def format_step_summary(
    response_data: Dict[str, Any],
    backend_url: str,
) -> str:
    """Generate rich GitHub Step Summary with metrics and policy receipt citations."""
    decision = str(response_data.get("decision", "BLOCK")).upper()
    reason = str(response_data.get("reason", "UNKNOWN"))
    explanation = str(response_data.get("explanation", ""))
    event_id = str(response_data.get("event_id", ""))
    draft_id = response_data.get("draft_id") or "N/A"
    passport_id = response_data.get("passport_id") or "N/A"
    passport_verified = response_data.get("passport_hash_verified")
    total_blockers = response_data.get("total_blockers", 0)
    is_duplicate = response_data.get("duplicate", False)
    findings: List[Dict[str, Any]] = response_data.get("findings", [])

    verified_badge = "✅ Verified" if passport_verified is True else ("❌ Tampered / Failed" if passport_verified is False else "N/A")

    if decision == "PASS":
        header = "## 🛡️ BrandLedger Publication Gate: Authorized (PASS)"
        status_callout = "> **Outcome:** `PASS` — All brand safety policies cleared and Content Passport cryptographically verified."
    else:
        header = "## 🚫 BrandLedger Publication Gate: Blocked (BLOCK)"
        status_callout = f"> **Outcome:** `BLOCK` — Publication halted due to `{reason}`."

    lines = [
        header,
        "",
        status_callout,
        "",
        "### 📊 Evaluation Metadata",
        "",
        "| Attribute | Value |",
        "|---|---|",
        f"| **Decision** | `{decision}` |",
        f"| **Reason Code** | `{reason}` |",
        f"| **Event ID** | `{event_id}` |",
        f"| **Draft ID** | `{draft_id}` |",
        f"| **Content Passport** | `{passport_id}` |",
        f"| **Passport SHA-256 Seal** | {verified_badge} |",
        f"| **Active Blockers** | `{total_blockers}` |",
        f"| **Duplicate Event** | `{'Yes (cached)' if is_duplicate else 'No (fresh)'}` |",
        f"| **Evaluated By** | `{backend_url}` |",
        "",
        "### 📝 Explanation",
        "",
        f"> {explanation}",
        "",
    ]

    if findings:
        lines.extend([
            "### 🔍 Cited Policy Violations",
            "",
            "The following literal brand policy violations prevented publication authorization:",
            "",
            "| # | Policy Card | Category | Severity | Matched Copy | Verbatim Policy Rule Citation | Recommended Fix |",
            "|---|---|---|---|---|---|---|",
        ])
        for idx, f in enumerate(findings, start=1):
            p_id = f.get("policy_card_id", "UNKNOWN")
            p_ver = f.get("policy_version", "1.0")
            cat = f.get("category", "general")
            sev = f.get("severity", "blocker")
            matched = f.get("matched_text", "").replace("|", "\\|")
            quote = f.get("source_quote", "").replace("|", "\\|")
            fix = f.get("suggested_fix", f.get("explanation", "")).replace("|", "\\|")

            lines.append(
                f"| {idx} | `{p_id} v{p_ver}` | `{cat}` | `{sev}` | `{matched}` | *\"{quote}\"* | {fix} |"
            )
        lines.append("")

    return "\n".join(lines)


def execute_publication_gate(
    backend_url: str,
    webhook_secret: str,
    event_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    passport_id: Optional[str] = None,
    scan_id: Optional[str] = None,
    content_text: Optional[str] = None,
    content_file: Optional[str] = None,
    fail_on_block: bool = True,
    timeout_seconds: float = 30.0,
    workspace_root: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Execute publication gate check against BrandLedger API.

    Returns:
        Tuple[exit_code, response_data]
    """
    clean_backend_url = backend_url.strip().rstrip("/")
    if not (clean_backend_url.startswith("http://") or clean_backend_url.startswith("https://")):
        err_msg = (
            f"Invalid configuration: 'backend_url' must begin with 'http://' or 'https://'. "
            f"Received: '{clean_backend_url}'"
        )
        print(f"::error::{err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "CONFIGURATION_ERROR")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "CONFIGURATION_ERROR", "explanation": err_msg}

    # 1. Validate timeout parameter
    try:
        clean_timeout = validate_timeout(timeout_seconds)
    except ValueError as exc:
        err_msg = str(exc)
        print(f"::error::Configuration Error: {err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "INVALID_TIMEOUT")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "INVALID_TIMEOUT", "explanation": err_msg}

    target_endpoint = f"{clean_backend_url}/api/gate/publish"

    # 2. Build payload & raw bytes
    try:
        payload_dict, body_bytes = build_gate_payload(
            event_id=event_id,
            draft_id=draft_id,
            passport_id=passport_id,
            scan_id=scan_id,
            content_text=content_text,
            content_file=content_file,
            workspace_root=workspace_root,
        )
    except Exception as exc:
        err_msg = str(exc)
        print(f"::error::Configuration Error: {err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "CONFIGURATION_ERROR")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "CONFIGURATION_ERROR", "explanation": err_msg}

    # 3. Compute HMAC-SHA256 signature
    try:
        signature_header = compute_hmac_signature(body_bytes, webhook_secret)
    except Exception as exc:
        err_msg = str(exc)
        print(f"::error::HMAC Signing Error: {err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "SIGNING_ERROR")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "SIGNING_ERROR", "explanation": err_msg}

    # 4. Prepare HTTP Request
    req = urllib.request.Request(
        url=target_endpoint,
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-BrandLedger-Signature": signature_header,
            "User-Agent": "BrandLedger-Publication-Gate-Action/1.0",
        },
        method="POST",
    )

    print(f"Submitting publication gate evaluation to: {target_endpoint}")
    print(f"Event ID: {payload_dict['event_id']}")
    if "draft_id" in payload_dict:
        print(f"Draft ID: {payload_dict['draft_id']}")
    if "passport_id" in payload_dict:
        print(f"Passport ID: {payload_dict['passport_id']}")
    print(f"HMAC Authentication: Active (Secret: {mask_secret(webhook_secret)})")

    # 5. Dispatch HTTP Call
    try:
        with urllib.request.urlopen(req, timeout=clean_timeout) as response:
            status_code = response.getcode()
            raw_resp_bytes = response.read()
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="replace")
        status_code = http_err.code
        print(f"::error::BrandLedger API returned HTTP {status_code}: {http_err.reason}", file=sys.stderr)

        detail_msg = f"HTTP {status_code}: {http_err.reason}"
        try:
            parsed_err = json.loads(err_body)
            if "detail" in parsed_err:
                detail_msg = str(parsed_err["detail"])
        except Exception:
            if err_body:
                detail_msg = err_body[:200]

        print(f"::error::Error Detail: {detail_msg}", file=sys.stderr)

        write_github_output("decision", "BLOCK")
        write_github_output("reason", f"HTTP_{status_code}")
        write_github_output("explanation", detail_msg)
        return 1, {"decision": "BLOCK", "reason": f"HTTP_{status_code}", "explanation": detail_msg}

    except urllib.error.URLError as url_err:
        err_msg = f"Network connection failure to '{clean_backend_url}': {url_err.reason}"
        print(f"::error::{err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "NETWORK_ERROR")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "NETWORK_ERROR", "explanation": err_msg}

    except TimeoutError:
        err_msg = f"Publication Gate request timed out after {clean_timeout} seconds."
        print(f"::error::{err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "TIMEOUT")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "TIMEOUT", "explanation": err_msg}

    except Exception as exc:
        err_msg = f"Unexpected publication gate error: {exc}"
        print(f"::error::{err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "UNEXPECTED_ERROR")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "UNEXPECTED_ERROR", "explanation": err_msg}

    # 6. Parse JSON Response
    try:
        resp_json = json.loads(raw_resp_bytes.decode("utf-8"))
    except Exception as exc:
        err_msg = f"Invalid response format: Failed to parse JSON from backend: {exc}"
        print(f"::error::{err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "MALFORMED_RESPONSE")
        write_github_output("explanation", err_msg)
        return 1, {"decision": "BLOCK", "reason": "MALFORMED_RESPONSE", "explanation": err_msg}

    # 7. Extract Decision Attributes
    decision = str(resp_json.get("decision", "BLOCK")).upper()
    reason = str(resp_json.get("reason", "UNKNOWN"))
    explanation = str(resp_json.get("explanation", ""))
    total_blockers = int(resp_json.get("total_blockers", 0))
    passport_id_out = resp_json.get("passport_id") or ""
    passport_hash_verified = resp_json.get("passport_hash_verified")
    findings = resp_json.get("findings", [])
    duplicate = bool(resp_json.get("duplicate", False))

    print(f"Publication Gate Decision: {decision} (Reason: {reason})")
    print(f"Explanation: {explanation}")
    if total_blockers > 0:
        print(f"Blocking Violations Detected: {total_blockers}")

    # 8. Write Action Outputs
    write_github_output("decision", decision)
    write_github_output("reason", reason)
    write_github_output("explanation", explanation)
    write_github_output("total_blockers", total_blockers)
    write_github_output("passport_id", passport_id_out)
    write_github_output("passport_hash_verified", str(passport_hash_verified).lower() if passport_hash_verified is not None else "")
    write_github_output("findings_summary", json.dumps(findings))
    write_github_output("duplicate", str(duplicate).lower())

    # 9. Render Step Summary
    summary_markdown = format_step_summary(resp_json, clean_backend_url)
    write_step_summary(summary_markdown)

    # 10. Handle fail_on_block
    if decision == "BLOCK":
        if fail_on_block:
            print("::error::BrandLedger Publication Gate evaluated to BLOCK. Failing step (fail_on_block=true).", file=sys.stderr)
            return 1, resp_json
        else:
            print("::warning::BrandLedger Publication Gate evaluated to BLOCK, but fail_on_block is disabled. Proceeding.", file=sys.stderr)
            return 0, resp_json

    print("::notice::BrandLedger Publication Gate evaluated to PASS. Creative publication authorized.")
    return 0, resp_json


def parse_args_and_env() -> Dict[str, Any]:
    """Parse inputs from CLI arguments with fallback to GitHub Actions environment variables."""
    parser = argparse.ArgumentParser(
        description="BrandLedger Publication Gate Runner for GitHub Actions",
    )
    parser.add_argument("--backend-url", default=None, help="BrandLedger backend API base URL")
    parser.add_argument("--webhook-secret", default=None, help="CMS webhook HMAC secret")
    parser.add_argument("--event-id", default=None, help="Unique event/delivery ID")
    parser.add_argument("--draft-id", default=None, help="UUID of content draft")
    parser.add_argument("--passport-id", default=None, help="UUID of Content Passport")
    parser.add_argument("--scan-id", default=None, help="UUID of compliance scan")
    parser.add_argument("--content-text", default=None, help="Creative text to evaluate")
    parser.add_argument("--content-file", default=None, help="Path to workspace file to evaluate")
    parser.add_argument("--fail-on-block", default=None, help="Fail step if gate returns BLOCK ('true'/'false')")
    parser.add_argument("--timeout-seconds", default=None, help="HTTP request timeout")

    parsed, _ = parser.parse_known_args()

    # Resolution precedence: CLI Argument -> INPUT_<NAME> -> Standard Env Var -> Default
    backend_url = (
        parsed.backend_url
        or os.environ.get("INPUT_BACKEND_URL")
        or os.environ.get("BRANDLEDGER_URL")
        or "http://localhost:8000"
    )

    webhook_secret = (
        parsed.webhook_secret
        or os.environ.get("INPUT_WEBHOOK_SECRET")
        or os.environ.get("CMS_WEBHOOK_SECRET")
        or ""
    )

    event_id = parsed.event_id or os.environ.get("INPUT_EVENT_ID") or None
    draft_id = parsed.draft_id or os.environ.get("INPUT_DRAFT_ID") or None
    passport_id = parsed.passport_id or os.environ.get("INPUT_PASSPORT_ID") or None
    scan_id = parsed.scan_id or os.environ.get("INPUT_SCAN_ID") or None
    content_text = parsed.content_text or os.environ.get("INPUT_CONTENT_TEXT") or None
    content_file = parsed.content_file or os.environ.get("INPUT_CONTENT_FILE") or None

    raw_fail_on_block = (
        parsed.fail_on_block
        if parsed.fail_on_block is not None
        else os.environ.get("INPUT_FAIL_ON_BLOCK", "true")
    )
    fail_on_block = str(raw_fail_on_block).strip().lower() in ("true", "1", "yes")

    raw_timeout = (
        parsed.timeout_seconds
        if parsed.timeout_seconds is not None
        else os.environ.get("INPUT_TIMEOUT_SECONDS", "30")
    )
    timeout_seconds = validate_timeout(raw_timeout)

    return {
        "backend_url": backend_url,
        "webhook_secret": webhook_secret,
        "event_id": event_id,
        "draft_id": draft_id,
        "passport_id": passport_id,
        "scan_id": scan_id,
        "content_text": content_text,
        "content_file": content_file,
        "fail_on_block": fail_on_block,
        "timeout_seconds": timeout_seconds,
    }


def main() -> None:
    """CLI and GitHub Actions execution entry point."""
    try:
        config = parse_args_and_env()
    except ValueError as exc:
        err_msg = str(exc)
        print(f"::error::Configuration Error: {err_msg}", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "CONFIGURATION_ERROR")
        write_github_output("explanation", err_msg)
        sys.exit(1)

    if not config["webhook_secret"]:
        print("::error::Missing required input: 'webhook_secret' is unset or empty.", file=sys.stderr)
        write_github_output("decision", "BLOCK")
        write_github_output("reason", "MISSING_SECRET")
        write_github_output("explanation", "webhook_secret must be provided to sign requests.")
        sys.exit(1)

    exit_code, _ = execute_publication_gate(
        backend_url=config["backend_url"],
        webhook_secret=config["webhook_secret"],
        event_id=config["event_id"],
        draft_id=config["draft_id"],
        passport_id=config["passport_id"],
        scan_id=config["scan_id"],
        content_text=config["content_text"],
        content_file=config["content_file"],
        fail_on_block=config["fail_on_block"],
        timeout_seconds=config["timeout_seconds"],
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
