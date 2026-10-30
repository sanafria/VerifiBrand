# BrandLedger — Acceptance Testing Specification & Test Plan

**Document Owner:** Umme Haany Tandur  
**Role:** QA, Integration, Testing & Submission Lead (Member 6)  
**Project:** BrandLedger Brand Governance & Deterministic Policy Compliance Platform  
**Target Submission:** Future Stack Hackathon  
**Document Version:** 1.1 (Factual Accuracy & Code-Verified Review)  

---

## 1. Purpose and Scope of Acceptance Testing

### 1.1 Purpose
The purpose of this document is to define the formal acceptance testing criteria, test procedures, expected results, and pass/fail boundaries for the BrandLedger platform. It establishes a repeatable, transparent verification process to ensure all components delivered by Members 1 through 5 meet their functional requirements, respect system integration boundaries, and strictly enforce the core platform tenet: **"No receipt, no flag."**

### 1.2 Scope
This specification covers:
1. **API Endpoints:** Health, Policy CRUD, Scans, File Uploads, Human Review Gates, and Content Passports.
2. **Deterministic Rules Engine:** Terminology enforcement, offer expiration, numerical limits, claim substantiation, and verbatim evidence verification.
3. **Extraction & Visual Pipeline:** Format validation, PDF layer extraction, Tesseract OCR fallback, visual defect detection (resolution, blur, contrast), and logo matching.
4. **Relational Database Integrity:** PostgreSQL schema constraints, version snapshots, foreign key cascades, and data preservation.
5. **Human Governance & Cryptographic Certification:** Header-based role authorization, reviewer decision handling, canonical snapshot generation, and SHA-256 hash tamper detection.
6. **Frontend Integration Boundaries:** Policy Library, Brand Passport viewer, and Workspace contract testing.

---

## 2. Testing Prerequisites and Environment Setup

Acceptance tests require the following services and configuration:

### 2.1 Database Container (PostgreSQL 16)
The stateful integration endpoints require the local PostgreSQL container running on port `5433`:
```bash
# Start PostgreSQL container with schema.sql and seed.sql pre-loaded
docker compose up -d

# Verify container health (should return 'healthy')
docker ps --filter "name=brandledger_postgres"
```

### 2.2 Environment Configuration
Ensure `.env` exists in the repository root:
```bash
cp .env.example .env
```
Key required environment variables:
- `ENVIRONMENT=development`
- `HOST=0.0.0.0`
- `PORT=8000`
- `DATABASE_URL=postgresql://brandledger_user:brandledger_secret@localhost:5433/brandledger`
- `BL_MAX_FILE_MB=20`
- `BL_OCR_LANG=eng`

### 2.3 System Dependencies
- **Tesseract OCR:** Required for image and scanned PDF extraction (`tesseract` on PATH or specified via `TESSERACT_CMD`).
- **Python 3.11+ / Node.js 18+:** Required for running backend and frontend test runners.

---

## 3. System Components and Features Under Test

| Component ID | Subsystem | Owner | Primary Function Under Test |
|---|---|---|---|
| **CMP-1** | Scan Workspace Boundary | Member 1 (Sana) | Contract serialization between approved policies and scan payload. |
| **CMP-2** | Policy Library & Brand Passport | Member 2 (Nimra) | Policy authoring, category filtering, quote verification, brand profile viewing. |
| **CMP-3** | Shared API & Relational DB | Member 3 (Zoya) | PostgreSQL schema, Policy CRUD, Scan persistence, Review gate, Passport issuance. |
| **CMP-4** | Deterministic Rules Engine | Member 4 (Zynab) | Terminology, Expired Offers, Numerical limits, Claims, and Evidence Verifier. |
| **CMP-5** | Extraction & Visual Pipeline | Member 5 (Mahadevi)| PDF layer parsing, OCR fallback, blur/resolution checks, logo matcher. |
| **CMP-6** | Cryptographic Hashing | Member 3 & 4 | Canonical snapshot assembly and SHA-256 tamper detection. |
| **CMP-7** | Publication Gate & GitHub Action | Member 6 (Umme Haany) | HMAC-SHA256 authenticated pre-publication gate, duplicate-event idempotency, and reusable GitHub Action CI packaging. |

---

## 4. Positive Acceptance Test Scenarios

These scenarios validate that standard, valid workflows execute correctly and return expected HTTP status codes and structured payloads.

### Summary Table of Positive Tests

| Test ID | Feature / Component | Endpoint / Action | Expected Status | Primary Verification |
|---|---|---|---|---|
| **AT-001** | Service Health | `GET /health` | `200 OK` | Service reports `status: ok` and service name. |
| **AT-002** | List Seed Policies | `GET /api/policies` | `200 OK` | Returns wrapped envelope with $\ge 4$ seeded policy cards. |
| **AT-003** | Create Policy Card | `POST /api/policies` | `201 Created` | Creates policy, assigns UUID, snapshots version 1. Quote is literal substring. |
| **AT-004** | Update Policy (Version Bump) | `PATCH /api/policies/{id}`| `200 OK` | Updates rule text, increments version to 2, snapshots version 2. |
| **AT-005** | In-Memory Direct Scan | `POST /api/scan` | `200 OK` | Validates text against provided cards; returns verified findings. |
| **AT-006** | Stateful Scan Persistence | `POST /api/scans` | `201 Created` | Persists draft, runs DB policies, saves findings in PostgreSQL. |
| **AT-007** | Retrieve Persisted Scan | `GET /api/scans/{id}` | `200 OK` | Returns saved findings and completed scan record. |
| **AT-008** | File Upload (Text PDF) | `POST /api/scans/upload` | `201 Created` | Extracts text layer (`text_layer`), executes scan, returns scan + extraction. |
| **AT-009** | Image Upload (OCR) | `POST /api/scans/upload` | `201 Created` | Runs Tesseract OCR (`ocr`), finds promo entities, completes scan. |
| **AT-010** | Review Approval & Passport | `POST /api/reviews` | `201 Created` | Approves draft, creates Content Passport with SHA-256 hash. |
| **AT-011** | Passport Hash Verification | `GET /api/passports/{id}`| `200 OK` | Loads certificate; computes matching SHA-256 hash (`hash_verified: true`). |
| **AT-012** | Pre-Publication Gate Webhook (PASS) | `POST /api/gate/publish` | `200 OK` | Signed request with valid passport & approval returns decision `PASS` (`PUBLICATION_AUTHORIZED`). |
| **AT-013** | Reusable GitHub Action Execution | `.github/actions/publication-gate` | `Exit 0` | Action runner signs payload, receives PASS, writes step outputs, and renders Markdown summary. |

---

### Detailed Test Specifications

#### AT-001: API Service Health Check
- **Component:** Core API Gateway (`backend/app/main.py`)
- **Preconditions:** Backend server running on `http://127.0.0.1:8000`.
- **Test Steps:**
  1. Send `GET http://127.0.0.1:8000/health`.
- **Expected Result:**
  - Status Code: `200 OK`
  - Response Body:
    ```json
    {
      "status": "ok",
      "service": "brandledger-api"
    }
    ```

#### AT-002: Query Policy Cards with Filtering
- **Component:** Policy Management API (`backend/app/api/policies.py`)
- **Preconditions:** PostgreSQL container running with `seed.sql` executed.
- **Test Steps:**
  1. Send `GET /api/policies?card_type=terminology&status=active`.
- **Expected Result:**
  - Status Code: `200 OK`
  - Envelope contains `items` array and `total >= 1`.
  - All items in `items` have `card_type == "terminology"` and `status == "active"`.
  - Item contains non-empty `source_quote` and `version >= 1`.

#### AT-003: Policy Card Creation with Verbatim Quote & Version 1 Snapshot
- **Component:** Policy API (`backend/app/api/policies.py`)
- **Preconditions:** PostgreSQL container running.
- **Test Steps:**
  1. Send `POST /api/policies` with payload:
     ```json
     {
       "title": "Social Influencer Disclosure Requirement",
       "card_type": "claim",
       "rule_text": "All sponsored influencer content must prominently display #ad in compliance with advertising standards.",
       "approved_value": "#ad",
       "source_quote": "All sponsored influencer content must prominently display #ad",
       "severity": "blocker"
     }
     ```
     *(Note: `source_quote` is an exact, literal substring of `rule_text`, satisfying both backend schema validation and the "No receipt, no flag" verbatim substring requirement.)*
- **Expected Result:**
  - Status Code: `201 Created`
  - Response contains a valid `id` (UUID), `version == 1`, `status == "active"`.
  - Database contains corresponding snapshot in `policy_card_versions` where `policy_card_id == id` and `version == 1`.

#### AT-004: Policy Card Content Update and Version Increment
- **Component:** Policy API (`backend/app/api/policies.py`)
- **Preconditions:** Policy card created via AT-003 exists in database.
- **Test Steps:**
  1. Send `PATCH /api/policies/{id}` with payload:
     ```json
     {
       "rule_text": "All sponsored influencer content must prominently display #ad or #sponsored in compliance with advertising standards.",
       "approved_value": "#ad or #sponsored",
       "source_quote": "All sponsored influencer content must prominently display #ad or #sponsored"
     }
     ```
- **Expected Result:**
  - Status Code: `200 OK`
  - Returned policy has `version == 2`.
  - Database contains two records in `policy_card_versions` for this ID: version 1 and version 2.

#### AT-005: Direct In-Memory Draft Scan
- **Component:** Policy Engine (`backend/app/main.py:api_scan_draft`)
- **Preconditions:** Server running. Does not require database persistence.
- **Test Steps:**
  1. Send `POST /api/scan` with payload:
     ```json
     {
       "content_text": "Our customers can earn up to 800 bonus points with Summer Discount!",
       "policy_cards": [
         {
           "id": "pol_term_001",
           "version": "1.0",
           "content": "The brand prohibits the term 'Customers' and requires 'Members'.",
           "rules": [{"type": "terminology", "prohibited": "Customers", "replacement": "Members", "quote": "The brand prohibits the term 'Customers' and requires 'Members'."}]
         },
         {
           "id": "pol_offer_002",
           "version": "2.0",
           "content": "Summer Discount promotion is valid through 2026-06-30.",
           "metadata": {"offer_name": "Summer Discount", "valid_until": "2026-06-30", "quote": "Summer Discount promotion is valid through 2026-06-30."}
         }
       ],
       "scan_date": "2026-07-01"
     }
     ```
- **Expected Result:**
  - Status Code: `200 OK`
  - `total_findings >= 2`.
  - Finding 1: Category `terminology`, cites `pol_term_001`, version `1.0`, `is_verified == true`.
  - Finding 2: Category `expired_offer`, cites `pol_offer_002`, version `2.0`, `is_verified == true`.

#### AT-006: Database-Backed Scan Orchestration
- **Component:** Scan Service (`backend/app/api/scans.py`)
- **Preconditions:** Seeded policies in PostgreSQL.
- **Test Steps:**
  1. Send `POST /api/scans` with payload:
     ```json
     {
       "title": "Summer Campaign Post",
       "content_text": "Our customers can enjoy the Summer Discount!",
       "scan_date": "2026-07-01"
     }
     ```
- **Expected Result:**
  - Status Code: `201 Created`
  - Response contains `scan_id`, `draft_id`, and `status == "completed"`.
  - Findings are persisted in `findings` table in PostgreSQL.
  - `has_blockers == true`.

#### AT-007: Persisted Scan Result Retrieval
- **Component:** Scan Service (`backend/app/api/scans.py`)
- **Preconditions:** Scan ID from AT-006 exists.
- **Test Steps:**
  1. Send `GET /api/scans/{scan_id}`.
- **Expected Result:**
  - Status Code: `200 OK`
  - Response matches persisted record: `scan_id`, `draft_id`, `status == "completed"`.
  - Findings array contains persisted findings with cited source quotes.

#### AT-008: Upload and Scan Selectable-Text PDF
- **Component:** Extraction Module (`backend/app/api/uploads.py`)
- **Preconditions:** Sample file `backend/extraction_module/dataset/pdfs/pdf_selectable_text.pdf` exists.
- **Test Steps:**
  1. Send `POST /api/scans/upload` with multipart form data:
     - `file`: `pdf_selectable_text.pdf`
     - `title`: "Summer Flyer PDF"
     - `scan_date`: "2026-07-01"
- **Expected Result:**
  - Status Code: `201 Created`
  - Response contains `extraction.extraction_method == "text_layer"`.
  - Response contains `scan.status == "completed"`.

#### AT-009: Upload and Scan Raster Image with OCR
- **Component:** Extraction Module (`backend/app/api/uploads.py`)
- **Preconditions:** Sample file `backend/extraction_module/dataset/images/img_clear_offer.png` exists; Tesseract installed.
- **Test Steps:**
  1. Send `POST /api/scans/upload` with multipart form data:
     - `file`: `img_clear_offer.png`
     - `title`: "Spring Sale Banner"
- **Expected Result:**
  - Status Code: `201 Created`
  - `extraction.extraction_method == "ocr"` and `extraction.ocr.used == true`.
  - `extraction.extracted_text` contains `"SPRING SALE"`.
  - `extraction.entities.dates` contains normalized date `"2026-03-31"`.
  - `extraction.entities.percentages` contains value `20.0`.
  - `extraction.visual_warnings` does not contain `LOW_OCR_CONFIDENCE`, `LOW_RESOLUTION`, or `POSSIBLE_BLUR`.

#### AT-010: Reviewer Approval and Content Passport Issuance
- **Component:** Review Service (`backend/app/api/reviews.py`)
- **Preconditions:** Completed compliant scan exists.
- **Test Steps:**
  1. Send `POST /api/reviews` with headers:
     - `X-User-Role: reviewer`
     - `X-User-Id: rev-101`
     - `X-User-Name: Compliance Officer Sarah`
  2. Request body:
     ```json
     {
       "draft_id": "<valid_draft_id>",
       "scan_id": "<valid_scan_id>",
       "decision": "approved",
       "comment": "All checks cleared. Copy conforms to guidelines."
     }
     ```
- **Expected Result:**
  - Status Code: `201 Created`
  - Response contains `decision == "approved"` and a non-null `passport_id` (UUID).
  - Draft status in `content_drafts` updated to `"approved"`.
  - New row created in `passports` table with `status == "valid"` and a 64-character hex `passport_hash`.

#### AT-011: Content Passport Retrieval and Hash Verification
- **Component:** Passport Service (`backend/app/api/passports.py`)
- **Preconditions:** Passport ID issued in AT-010 exists.
- **Test Steps:**
  1. Send `GET /api/passports/{passport_id}`.
- **Expected Result:**
  - Status Code: `200 OK`
  - Response contains `id == passport_id`, `status == "valid"`.
  - `hash_verified == true` (dynamically re-computed SHA-256 hash matches stored `passport_hash`).
  - `metadata_snapshot` contains draft text, applied policy versions, findings summary, and reviewer metadata.

---

## 5. Negative Acceptance Test Scenarios

These scenarios test error handling, input validation, security boundaries, and graceful degradation.

### Summary Table of Negative Tests

| Test ID | Error Category | Endpoint / Condition | Expected Status | Expected Error / Detail |
|---|---|---|---|---|
| **AT-012** | Invalid Date Format | `POST /api/scan` with `scan_date: "invalid"` | `400 Bad Request` | Detail contains `"Invalid scan_date format"`. |
| **AT-013** | Empty Scan Content | `POST /api/scans` with `content_text: "   "` | `422 Unprocessable` | Detail states `Draft content_text must not be empty.` |
| **AT-014** | Nonexistent Policy | `PATCH /api/policies/{unknown_uuid}` | `404 Not Found` | Detail states `Policy card with ID '...' not found.` |
| **AT-015** | Unsupported Upload Format | `POST /api/scans/upload` with `.docx` file | `422 Unprocessable` | Error code contains `UNSUPPORTED_FORMAT`. |
| **AT-016** | Corrupt File Upload | `POST /api/scans/upload` with zero-byte image | `422 Unprocessable` | Error code contains `EMPTY_FILE` or `CORRUPT_FILE`. |
| **AT-017** | No Text Extracted | `POST /api/scans/upload` with blank image | `422 Unprocessable` | Error code `NO_TEXT_EXTRACTED` (requires human review). |
| **AT-018** | Creator Self-Approval | `POST /api/reviews` with `X-User-Role: creator` | `403 Forbidden` | Creators prohibited from approving content. |
| **AT-019** | Missing Role Header | `POST /api/reviews` without `X-User-Role` | `403 Forbidden` | Header required error. |
| **AT-020** | Duplicate Review Attempt | `POST /api/reviews` on already reviewed scan | `409 Conflict` | Detail indicates scan has already been reviewed. |
| **AT-021** | Mismatched Scan and Draft | `POST /api/reviews` with mismatched IDs | `400 Bad Request` | Detail indicates scan does not belong to draft. |
| **AT-022** | Tampered Passport Snapshot | `GET /api/passports/{id}` after DB modification | `200 OK` | `hash_verified: false` (tamper detected). |
| **AT-023** | Quote Verification Rejection | `filter_and_verify_findings` with fabricated quote | Suppressed / Rejected | Finding omitted ("No receipt, no flag"). |
| **AT-025** | Missing/Invalid Webhook Signature | `POST /api/gate/publish` without valid signature | `401 Unauthorized` | Detail states `Missing X-BrandLedger-Signature` or `Invalid HMAC-SHA256`. |
| **AT-026** | Publication Block on Active Findings | `POST /api/gate/publish` with active blockers | `200 OK` | `decision: BLOCK`, `reason: ACTIVE_BLOCKING_FINDINGS` with verbatim receipts. |
| **AT-027** | Publication Block on Unapproved Draft | `POST /api/gate/publish` on unapproved draft | `200 OK` | `decision: BLOCK`, `reason: DRAFT_NOT_APPROVED`. |
| **AT-028** | Publication Block on Tampered Passport | `POST /api/gate/publish` with tampered snapshot | `200 OK` | `decision: BLOCK`, `reason: PASSPORT_TAMPERED`. |
| **AT-029** | GitHub Action Step Failure | `.github/actions/publication-gate` on BLOCK | `Exit 1` | Action fails step when `fail_on_block: true` and logs Markdown violations table. |

---

### Detailed Negative Test Specifications

#### AT-012: Invalid Scan Date Format
- **Test Steps:**
  1. Send `POST /api/scan` with `"scan_date": "01-07-2026"` (invalid format; expects YYYY-MM-DD).
- **Expected Result:**
  - Status Code: `400 Bad Request`
  - Detail message: `"Invalid scan_date format: '01-07-2026'. Expected parseable date (e.g., YYYY-MM-DD)."`

#### AT-013: Empty Scan Content Text
- **Test Steps:**
  1. Send `POST /api/scans` with payload `{"title": "Empty Post", "content_text": "   "}`.
- **Expected Result:**
  - Status Code: `422 Unprocessable Content`
  - Detail message: `"Draft content_text must not be empty."`

#### AT-014: Nonexistent Policy Card Update
- **Test Steps:**
  1. Send `PATCH /api/policies/00000000-0000-0000-0000-000000000000` with payload `{"title": "New Title"}`.
- **Expected Result:**
  - Status Code: `404 Not Found`
  - Detail message: `"Policy card with ID '00000000-0000-0000-0000-000000000000' not found."`

#### AT-015: Unsupported File Upload Format
- **Test Steps:**
  1. Upload `dataset/edge_cases/unsupported.docx` to `POST /api/scans/upload`.
- **Expected Result:**
  - Status Code: `422 Unprocessable Entity`
  - Error body contains `errors` array with `code: "UNSUPPORTED_FORMAT"`. No draft or scan is created in the database.

#### AT-017: Extraction Produces No Text
- **Test Steps:**
  1. Upload `dataset/images/img_blank.png` (blank image) to `POST /api/scans/upload`.
- **Expected Result:**
  - Status Code: `422 Unprocessable Entity`
  - Response detail: `"No readable text was found in this file. No scan was created. This is NOT a clean result - the file needs human review."`
  - Error code: `NO_TEXT_EXTRACTED`.

#### AT-018: Creator Self-Approval Attempt
- **Test Steps:**
  1. Send `POST /api/reviews` with header `X-User-Role: creator`.
- **Expected Result:**
  - Status Code: `403 Forbidden`
  - Response detail: `"Forbidden: Creators are not authorized to approve content (self-approval prohibited)."`

#### AT-019: Missing Role Authorization Header
- **Test Steps:**
  1. Send `POST /api/reviews` without `X-User-Role` header.
- **Expected Result:**
  - Status Code: `403 Forbidden`
  - Response detail: `"Forbidden: Authentication required. Please provide X-User-Role header (e.g., 'reviewer' or 'admin')."`

#### AT-020: Duplicate Review Submission on Same Scan
- **Test Steps:**
  1. Complete review submission via AT-010.
  2. Re-send identical `POST /api/reviews` request for the same `scan_id`.
- **Expected Result:**
  - Status Code: `409 Conflict`
  - Response detail: `"Scan '<scan_id>' has already been reviewed (decision: approved)."`

#### AT-021: Mismatched Scan and Draft Identifiers
- **Test Steps:**
  1. Send `POST /api/reviews` providing a `draft_id` that does not match the `scan_id`'s associated draft.
- **Expected Result:**
  - Status Code: `400 Bad Request`
  - Response detail: `"Scan '<scan_id>' does not belong to Draft '<draft_id>'."`

#### AT-022: Tampered Passport Detection
- **Test Steps:**
  1. Issue a valid Content Passport via AT-010.
  2. Simulate unauthorized database tampering by modifying the stored `metadata_snapshot` column in PostgreSQL:
     ```sql
     UPDATE passports SET metadata_snapshot = jsonb_set(metadata_snapshot, '{reviewer_name}', '"Tampered Officer"') WHERE id = '<passport_id>';
     ```
  3. Send `GET /api/passports/{passport_id}`.
- **Expected Result:**
  - Status Code: `200 OK`
  - Response contains `hash_verified: false`.
  - Log warning generated: `"PASSPORT INTEGRITY COMPROMISED: Stored hash ... != computed ..."`.

#### AT-023: Fabricated Evidence Quote Rejection ("No Receipt, No Flag")
- **Test Steps:**
  1. Pass a draft to the evidence verifier where a finding attempts to cite a quote that does not exist as a literal substring of the policy card text.
- **Expected Result:**
  - Evidence verifier function `filter_and_verify_findings` rejects the finding.
  - The returned verified findings list does **not** include the fabricated finding.

---

## 6. End-to-End Governance Lifecycle Scenario (AT-024)

This acceptance scenario verifies the complete six-stage compliance lifecycle across all system components, including draft resubmission using `ScanCreate.draft_id`.

```mermaid
sequenceDiagram
    autonumber
    actor Governance as Governance Lead
    actor Marketer as Content Creator
    actor Reviewer as Compliance Officer
    participant API as FastAPI Backend
    participant DB as PostgreSQL 16
    participant Engine as Policy Engine

    Note over Governance,DB: Step 1: Policy Authoring & Versioning
    Governance->>API: POST /api/policies (Create Cashback Policy v1)
    API->>DB: INSERT into policy_cards & policy_card_versions
    API-->>Governance: 201 Created (Policy ID: P-101, Version 1)

    Note over Marketer,Engine: Step 2: Draft Submission & Initial Scan
    Marketer->>API: POST /api/scans (Submit Campaign Copy with violations)
    API->>DB: INSERT into content_drafts (status: 'draft') -> returns draft_id D-1
    API->>DB: INSERT into scans (draft_id: D-1, status: 'pending') -> returns scan_id S-1
    API->>Engine: scan_draft(content, active_policies, scan_date)
    Engine->>Engine: Evaluate Terminology, Dates & Facts
    Engine->>Engine: Verify Quotes ("No receipt, no flag")
    Engine-->>API: Return Verified Findings (e.g. 1 Terminology Blocker)
    API->>DB: INSERT into findings (scan_id: S-1)
    API->>DB: UPDATE scans SET status = 'completed' WHERE id = S-1
    API-->>Marketer: 201 Created (scan_id: S-1, draft_id: D-1, total_findings: 1)

    Note over Marketer,API: Step 3: Creator Revision (draft_id Rescan)
    Marketer->>API: POST /api/scans (draft_id: D-1, cleaned_content)
    API->>DB: UPDATE content_drafts SET content_text = cleaned WHERE id = D-1
    API->>DB: INSERT into scans (draft_id: D-1, status: 'pending') -> returns scan_id S-2
    API->>Engine: scan_draft(cleaned_content)
    Engine-->>API: Return 0 Findings
    API->>DB: UPDATE scans SET status = 'completed' WHERE id = S-2
    API-->>Marketer: 201 Created (scan_id: S-2, draft_id: D-1, total_findings: 0, has_blockers: false)

    Note over Reviewer,DB: Step 4: Human Review Gate
    Reviewer->>API: POST /api/reviews (draft_id: D-1, scan_id: S-2, decision: 'approved', X-User-Role: 'reviewer')
    API->>DB: Verify scan S-2 status == 'completed' & belongs to D-1
    API->>DB: INSERT into reviews -> returns review_id R-1
    API->>DB: UPDATE content_drafts SET status = 'approved' WHERE id = D-1

    Note over Reviewer,DB: Step 5: Cryptographic Certification
    API->>API: Assemble canonical snapshot & compute SHA-256 hash
    API->>DB: INSERT into passports (draft_id: D-1, scan_id: S-2, review_id: R-1, hash, status='valid')
    API-->>Reviewer: 201 Created (passport_id: UUID)

    Note over Governance,API: Step 6: Audit Verification
    Governance->>API: GET /api/passports/{passport_id}
    API->>API: Re-compute SHA-256 hash across loaded snapshot
    API-->>Governance: 200 OK (hash_verified: true, valid certificate)
```

### Verified Schema Note on Draft Rescanning
In `backend/app/schemas/scan.py`, `ScanCreate` explicitly includes:
```python
draft_id: Optional[UUID] = Field(None, description="Optional existing draft ID for rescan")
```
When `draft_id` is provided in `POST /api/scans`, `scan_service.py` executes:
1. Queries `SELECT id FROM content_drafts WHERE id = $1;`. If not found, raises `HTTP 404`.
2. Updates existing draft: `UPDATE content_drafts SET title = $1, content_text = $2, updated_at = NOW() WHERE id = $3;`.
3. Creates a new scan attempt linked to that same draft: `INSERT INTO scans (draft_id, status, scan_date) VALUES ($1, 'pending', $2);`.
4. The reviewer reviews the second scan attempt (`scan_id: S-2`), ensuring full audit separation between failed drafts and approved drafts.

---

## 7. Automated Test Baseline and Execution Status

To maintain 100% factual accuracy, tests in BrandLedger are categorized into **Executed Automated Baseline** (directly run and verified by QA) and **Proposed Integration Scenarios** (requiring dependencies and external services).

### 7.1 Automated Tests Executed and Verified by QA

A total of **52 automated unit tests** were executed and verified as **100% passing**:

| Test Group | Executed Command | Runner | Verified Test Count | Result |
|---|---|---|---|---|
| **Frontend Policy Store** | `npm test` *(in `frontend/`)* | Node.js native test runner (`node --experimental-strip-types`) | **10 tests** | **10 PASS, 0 FAIL** (~75ms) |
| **Deterministic Rule Checks** | `/opt/anaconda3/bin/pytest backend/tests/test_rule_checks.py` | pytest-8.4.2 | **17 tests** | **17 PASS, 0 FAIL** |
| **Evidence Verifier** | `/opt/anaconda3/bin/pytest backend/tests/test_evidence_verifier.py` | pytest-8.4.2 | **12 tests** | **12 PASS, 0 FAIL** |
| **Policy Engine Orchestration** | `/opt/anaconda3/bin/pytest backend/tests/test_policy_engine.py` | pytest-8.4.2 | **7 tests** | **7 PASS, 0 FAIL** |
| **Database Schema DDL** | `/opt/anaconda3/bin/pytest backend/tests/test_database_schema.py` | pytest-8.4.2 | **6 tests** | **6 PASS, 0 FAIL** |
| **Total Verified Passing** | | | **52 tests** | **100% Pass Rate** |

### 7.2 Tests Not Yet Executed (Pending Environment Setup)
The following test suites exist in the repository but have **not** been executed due to local environment prerequisites:
1. **Extraction Module Unit Tests (`backend/extraction_module/tests/test_extraction.py`, 8 tests):**
   - *Status:* Unexecuted in current shell.
   - *Reason:* Requires `opencv-python-headless` (`cv2`) and `pytesseract` which are specified in `backend/extraction_module/requirements.txt` but not installed in the base Python environment.
2. **API & Database Integration Tests (`test_api_policies.py`, `test_api_scans.py`, `test_api_reviews_passports.py`, `test_api_uploads.py`, `test_health.py`):**
   - *Status:* Unexecuted in current shell.
   - *Reason:* Requires `asyncpg` driver in the active Python environment and active PostgreSQL container on port `5433`.

---

## 8. Known Limitations, Mock Boundaries, and Incomplete Integrations

The acceptance test suite identifies the following architectural boundaries and gaps:

1. **Frontend-to-Backend Envelope Mismatch:**
   - In `frontend/src/lib/api/policyClient.ts`, enabling `NEXT_PUBLIC_USE_BACKEND_CRUD=true` queries `GET /api/policies`.
   - The backend returns `{ "items": [...], "total": ... }`, whereas `policyClient.ts` expects a direct array (`data.length`). In development, the frontend relies on `mockData.ts` and the localStorage adapter.
2. **Header-Based Authorization Simulation:**
   - Role authorization via `X-User-Role` is a development simulation. It prevents accidental creator self-approval in the workflow but does not validate cryptographically signed tokens or user passwords.
3. **Extraction Database Persistence:**
   - Visual checks (blur, resolution, estimated contrast) and logo similarity results are returned in the response of `POST /api/scans/upload`, but are not persisted into the PostgreSQL `findings` table (the relational schema stores text policy violations only).
4. **Contrast Calculation Nature:**
   - Contrast calculations in the extraction module are estimates derived from OCR bounding boxes and do not certify official WCAG compliance (`wcag_verified: false`).

---

## 9. Acceptance Criteria and Sign-Off Boundary

| Criteria Category | Condition for Final Acceptance |
|---|---|
| **Core Principle Enforcement** | Zero findings reported without valid `policy_card_id`, exact `policy_version`, and verbatim `source_quote`. |
| **Data Preservation** | Updating policy card content increments version number and preserves prior versions in `policy_card_versions`. |
| **Reviewer Gate Integrity** | Requests with `X-User-Role: creator` or missing role headers are rejected with HTTP 403. |
| **Audit Traceability** | Content Passports compute canonical SHA-256 hashes; any manual DB modification evaluates to `hash_verified: false`. |
| **Safe Failure Handling** | Uploads with unreadable or empty text fail explicitly with HTTP 422 and require human review. |

---

*Acceptance Testing Specification authored by Umme Haany Tandur (QA, Integration, Testing & Submission Lead).*
