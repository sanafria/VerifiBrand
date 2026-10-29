# VerifiBrand

> **Verifiable Brand Compliance & Cryptographic Content Passporting**  
> 🌐 **Live Website**: [https://verifibrand-9h26.vercel.app/](https://verifibrand-9h26.vercel.app/)  
> *Future Stack Hackathon Submission*  
> *Status: Proof-of-Concept / Hackathon Prototype*

---

## ⚡ What VerifiBrand Does (In Short)

**VerifiBrand** is an enterprise brand governance platform that replaces subjective, vague creative reviews with **verifiable, audit-backed compliance** and **tamper-proof cryptographic certificates**.

1. **Ingests Marketing Collateral**: Ingests campaign text, banners, PDFs, and images with automatic dual-layer extraction (PyMuPDF + Tesseract OCR).
2. **"No Receipt, No Flag" Scanning**: Enforces deterministic brand policies (terminology, offer dates, numerical facts, claims). Scans cannot flag an asset without providing a verifiable "receipt": the exact policy ID, active version snapshot, and verbatim quote from the rulebook.
3. **Role-Enforced Human Approval**: Prohibits creator self-approval via separation-of-duties review gating (`/review`).
4. **Cryptographic Content Passports**: Generates an immutable digital certificate with a canonical **SHA-256 cryptographic fingerprint** (`/passports`), allowing brands, agencies, and publishers to verify that content has not been altered post-approval.

---

## 🚀 Recent Updates & New Capabilities

- **🌐 Live Production Deployment**: Deployed on Vercel at [https://verifibrand-9h26.vercel.app/](https://verifibrand-9h26.vercel.app/) with edge routing and simulated failover resilience.
- **✨ Complete Platform Rebrand**: Transitioned identity to **VerifiBrand** across all views, metadata, icons, and navigation with a refined navy & gold palette.
- **🧭 Interactive Guided Tour**: Step-by-step element spotlight tour (`GuidedTour.tsx`) guiding judges and users through the scan, review, and passport issuance pipeline.
- **📑 New Public Overview Pages**:
  - **[How It Works](https://verifibrand-9h26.vercel.app/how-it-works)**: Interactive 4-step compliance pipeline visualization.
  - **[Security & Trust](https://verifibrand-9h26.vercel.app/security)**: Cryptographic integrity guarantees, SHA-256 proof generation, and responsible governance.
  - **[Features](https://verifibrand-9h26.vercel.app/features)**: Comprehensive enterprise capability matrix.
  - **[Sample Review](https://verifibrand-9h26.vercel.app/demo-preview)**: Instant pre-populated marketing compliance evaluation demo.
- **🐳 Full-Stack Containerization**: Added multi-stage `Dockerfile` configurations for both frontend and backend alongside Docker Compose orchestrator.

---

## 1. Overview & Problem Statement

### The Problem
Marketing teams and brand compliance officers operate in constant friction. Marketers want to move fast across multiple channels (social media, banner ads, PDF flyers, campaigns), while compliance teams frequently reject creative assets with vague feedback such as *"this doesn't feel on-brand"* or *"check the guidelines from three years ago."*

This disconnect creates:
- **Painful revision bottlenecks** and lost time-to-market.
- **Accidental trademark, terminology, and legal violations**.
- **Zero cryptographic auditability** once assets are handed off to downstream publishers or advertising networks.

### The VerifiBrand Solution
VerifiBrand solves this friction by establishing a single, non-negotiable platform tenet:

> **"No receipt, no flag."**

In VerifiBrand, automated compliance scans cannot flag any content unless they cite:
1. The **exact active policy card ID**.
2. The **immutable policy version snapshot** evaluated at scan time.
3. A **literal, verbatim source quotation** from the approved brand rulebook.

Once compliant content is formally approved by a human reviewer, VerifiBrand issues an immutable **Content Passport**—a digital certificate anchored by a canonical **SHA-256 cryptographic fingerprint** that guarantees end-to-end tamper detection.

---

## 2. Core Features

- **Policy Library & Governance (Member 2)**:
  - Centralized repository of living brand policies across terminology, promotional validity, numerical facts, and claims.
  - Automatic version incrementing and historical archiving in PostgreSQL (`policy_card_versions`).
  - Brand identity voice pillars, approved color palettes, and exportable governance JSON.

- **Deterministic Compliance Scan Engine (Member 4)**:
  - 100% deterministic, rule-based scanning across four mandatory categories:
    1. *Terminology*: Case-insensitive prohibited term detection with approved replacements.
    2. *Expired Offers*: Date-boundary and promotional calendar validity checking.
    3. *Exact Facts & Numbers*: Contextual numerical limits and rewards caps.
    4. *Unsupported Claims*: Identifying superlative assertions requiring substantiation without assuming falsity.

- **Evidence Verifier ("No receipt, no flag") (Member 4)**:
  - Secondary verification gate that intercepts all raw findings.
  - Strips hallucinated or mismatched flags; verifies that cited policy cards exist, versions match, and source quotes are verbatim substrings of approved policy text.

- **File Upload & Visual OCR Pipeline (Member 5)**:
  - Multi-format asset ingestion (PNG, JPG, WEBP, BMP, TIFF, and PDF).
  - Dual extraction: PyMuPDF for native vector text layers, falling back to Tesseract OCR for rasterized graphics.
  - Image quality checks: Detection of low resolution, blur, estimated contrast, and logo similarity candidates.

- **Reviewer Approval Workflow & Gating (Member 3)**:
  - Dedicated review endpoint (`POST /api/reviews`) enforcing role authorization.
  - Prohibits content creator self-approval via `X-User-Role` header checks.
  - Formally transitions content draft status from `draft` to `approved` or `rejected`.

- **Cryptographic Content Passport (Member 3)**:
  - On approval, freezes an immutable metadata snapshot (draft content, reviewer ID, timestamp, applied policy versions).
  - Computes a canonical SHA-256 hash (sorted keys, compact separators).
  - On retrieval (`GET /api/passports/{id}`), dynamically recomputes the hash to detect database-level tampering (`hash_verified: true/false`).

---

## 3. Technology Stack

| Layer | Technologies | Role in VerifiBrand |
|---|---|---|
| **Frontend** | Next.js 16.4 (App Router), React 19, TypeScript 5, Vanilla CSS Modules | Policy Library UI, Brand Passport governance viewer, scan workspace boundary |
| **Backend API** | Python 3.11+, FastAPI 0.110+, Uvicorn, Pydantic v2 | RESTful routing, CORS configuration, schema validation, review orchestration |
| **Database** | PostgreSQL 16 (via Docker Compose), asyncpg 0.29+ | Relational persistence, immutable version snapshots, audit logging |
| **Rules Engine** | Python Standard Library (`re`, `hashlib`, `datetime`, `json`), python-dateutil | Deterministic regex rules, evidence verification, canonical SHA-256 hashing |
| **Extraction & OCR** | PyMuPDF (fitz) 1.24+, Tesseract OCR, pytesseract 0.3.10+, OpenCV, Pillow | PDF parsing, raster OCR, resolution/blur heuristics |
| **Testing** | Pytest 8.4+, pytest-asyncio, Node.js Native Test Runner (`--test`) | Unit tests, rule verification, schema validation, API integration tests |

---

## 4. Prerequisites

Before installing, ensure your host machine has the following tools installed:

1. **Python**: Version `3.11` or higher (`python3 --version`).
2. **Node.js**: Version `20.x` or higher (`node --version`) and `npm` (`npm --version`).
3. **Docker & Docker Compose**: Docker Desktop or Docker Engine with Compose V2 (`docker compose version`).
4. **Tesseract OCR** (Required for visual image OCR extraction):
   - **macOS (Homebrew)**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
   - **Windows**: Install via [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki).

---

## 5. Docker Setup & Full-Stack Containerization

VerifiBrand supports complete single-command containerization via Docker Compose, as well as database-only containerization for local development.

### Option A: Complete Full-Stack Containerization (Recommended)
Starts all three services: PostgreSQL 16 (port `5433:5432`), FastAPI Backend with Tesseract OCR pre-installed (port `8000`), and Next.js Web App (port `3000`).

1. **Start the entire application stack**:
   ```bash
   docker compose up --build -d
   ```

2. **Verify container health**:
   ```bash
   docker compose ps
   ```
   *Expected Output*:
   - `brandledger_postgres`: Up (healthy) on `5433->5432`
   - `brandledger_backend`: Up (healthy) on `8000->8000`
   - `brandledger_frontend`: Up on `3000->3000`

3. **Access the application**:
   - Web Application: [http://localhost:3000](http://localhost:3000)
   - Backend API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
   - API Health Check: [http://localhost:8000/health](http://localhost:8000/health)

4. **Stop all containers**:
   ```bash
   docker compose down
   ```

---

### Option B: Database-Only Mode (For Local Code Development)
If you prefer running Python and Next.js directly on your host machine for live hot-reloading:

1. **Start only the database**:
   ```bash
   docker compose up brandledger_db -d
   ```

2. **Verify database connection and schema initialization**:
   The container automatically executes `database/schema.sql` (DDL) and `database/seed.sql` on initial initialization.
   ```bash
   docker exec -it brandledger_postgres pg_isready -U brandledger_user -d brandledger
   ```

3. **Reset Database Volume** (if schema or seed SQL files are modified):
   Because PostgreSQL only executes initialization scripts when the data volume is empty, purge and rebuild the volume using:
   ```bash
   docker compose down -v
   docker compose up brandledger_db -d
   ```

---

## 6. Backend Setup & Startup

1. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   *(Windows: `.venv\Scripts\activate`)*

2. **Install backend dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Run the FastAPI development server**:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Verify backend health**:
   ```bash
   curl -s http://localhost:8000/health
   ```
   *Expected Response*: `{"status":"ok","service":"brandledger-api"}`

---

## 7. Frontend Setup & Startup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Start the Next.js development server**:
   ```bash
   npm run dev
   ```

4. **Open localhost in your browser**:
   - **Direct Browser URL**: Open [http://localhost:3000](http://localhost:3000)
   - **Terminal Commands to Open Automatically**:
     - **Windows (PowerShell)**:
       ```powershell
       Start-Process http://localhost:3000
       ```
     - **macOS**:
       ```bash
       open http://localhost:3000
       ```
     - **Linux**:
       ```bash
       xdg-open http://localhost:3000
       ```

5. **Available Application Routes**:

| Page / Capability | Localhost (Dev) | Live Production (Vercel) | Description |
|---|---|---|---|
| **Landing Page** | [localhost:3000](http://localhost:3000) | [/](https://verifibrand-9h26.vercel.app/) | Hero, platform pillars & architecture overview |
| **Guided Tour** | [localhost:3000/?tour=true](http://localhost:3000/?tour=true) | [/?tour=true](https://verifibrand-9h26.vercel.app/?tour=true) | Interactive element spotlight demo walkthrough |
| **How It Works** | [localhost:3000/how-it-works](http://localhost:3000/how-it-works) | [/how-it-works](https://verifibrand-9h26.vercel.app/how-it-works) | 4-step compliance pipeline visualization |
| **Security & Trust** | [localhost:3000/security](http://localhost:3000/security) | [/security](https://verifibrand-9h26.vercel.app/security) | Cryptographic SHA-256 passports & responsible AI |
| **Features Matrix** | [localhost:3000/features](http://localhost:3000/features) | [/features](https://verifibrand-9h26.vercel.app/features) | Enterprise feature checklist and breakdown |
| **Sample Review** | [localhost:3000/demo-preview](http://localhost:3000/demo-preview) | [/demo-preview](https://verifibrand-9h26.vercel.app/demo-preview) | Instant pre-populated marketing compliance demo |
| **Scan Workspace** | [localhost:3000/workspace](http://localhost:3000/workspace) | [/workspace](https://verifibrand-9h26.vercel.app/workspace) | Upload assets, OCR ingestion & live scan findings |
| **Policy Library** | [localhost:3000/policies](http://localhost:3000/policies) | [/policies](https://verifibrand-9h26.vercel.app/policies) | Authoritative brand rules & version management |
| **Brand Passport** | [localhost:3000/brand-passport](http://localhost:3000/brand-passport) | [/brand-passport](https://verifibrand-9h26.vercel.app/brand-passport) | Brand voice guidelines & color palette tokens |
| **Review Gateway** | [localhost:3000/review](http://localhost:3000/review) | [/review](https://verifibrand-9h26.vercel.app/review) | Human approval gate (creator self-approval blocked) |
| **Content Passports** | [localhost:3000/passports](http://localhost:3000/passports) | [/passports](https://verifibrand-9h26.vercel.app/passports) | Immutable cryptographic certificates & tamper test |
| **Audit Trail** | [localhost:3000/audit](http://localhost:3000/audit) | [/audit](https://verifibrand-9h26.vercel.app/audit) | Immutable verification log & receipt history |
| **Governance Insights**| [localhost:3000/insights](http://localhost:3000/insights) | [/insights](https://verifibrand-9h26.vercel.app/insights) | Risk scores, violation distributions & analytics |

---

## 8. Automated Testing & Validation

To maintain strict factual accuracy, all tests in VerifiBrand have been fully implemented, executed, and validated.

### 8.1 Complete Test Suite (131 Python Tests + 10 Frontend Tests — 100% Passing)

Run the full automated test suite locally:

```bash
# 1. Run Complete Python Suite (Unit, Integration, Gate, Agent, and E2E)
pytest backend/tests -v --durations=10

# Result: 131 passed, 2 skipped (host OCR binary), 0 failed in ~10s
```

```bash
# 2. Run Frontend Unit Tests
cd frontend
npm test
cd ..

# Result: 10 passed, 0 failed in ~0.5s
```

### 8.2 Breakdown of Automated Test Modules

1. **End-to-End Integration Tests (`test_e2e_workflow.py`, 7 tests)**:
   - Complete lifecycle validation: clean scan &rarr; reviewer approval &rarr; Content Passport generation &rarr; SHA-256 tamper verification &rarr; HMAC signed gate webhook &rarr; `PASS`.
   - Blocking content rejection with literal rule receipts &rarr; `BLOCK`.
   - Unapproved draft gate rejection &rarr; `BLOCK`.
   - Cryptographically tampered passport detection &rarr; `BLOCK`.
   - Webhook idempotency protection and 409 Conflict rejection for altered payloads.
   - Fetch.ai agent Action A, B, C, and ACP chat query execution against live backend.
   - Unavailable service resiliency (offline backend never returns false success).

2. **Fetch.ai Agent & ACP Protocol Suite (`test_agent.py`, 34 tests)**:
   - Sensitive secret masking (`masked_seed()`, `masked_api_key()`).
   - Action A (Check Creative Compliance: PASS, FLAG, BLOCK, input validation).
   - Action B (Explain Publication Blocks: evidence citations, scan fallback).
   - Action C (Verify Content Passport: VERIFIED, TAMPERED, REVOKED, NOT_FOUND, ERROR).
   - Agent Chat Protocol (ACP) message loop, immediate ACK, and formatted markdown replies for ASI:One.
   - Production security enforcement (refusal of development seeds).

3. **Authenticated Publication Gate Suite (`test_api_gate.py`, 16 tests)**:
   - HMAC-SHA256 signature verification over exact raw request bytes.
   - 401 Unauthorized for missing or invalid signatures.
   - Evidence-backed PASS/BLOCK evaluation with literal policy receipts.
   - Duplicate-event idempotency and safe concurrent delivery.

4. **Human Review & Content Passport Issuance (`test_api_reviews_passports.py`, 7 tests)**:
   - Separation-of-duties role enforcement (creators forbidden from self-approval).
   - Canonical SHA-256 fingerprint generation and tamper detection.

5. **Authoritative Scans & Policies (`test_api_scans.py`, `test_api_policies.py`, `test_health.py`, 17 tests)**:
   - Scans and findings persistence in PostgreSQL.
   - Policy card CRUD and version history tracking.

6. **Deterministic Rule Checks & Evidence Verifier (`test_rule_checks.py`, `test_evidence_verifier.py`, `test_policy_engine.py`, 36 tests)**:
   - "No receipt, no flag" proof verification, terminology, expired offers, numerical limits, claims substantiation.

7. **Database Schema DDL & Docker Config (`test_database_schema.py`, 6 tests)**:
   - Foreign key integrity, check constraints, and container mount validation.

8. **File Extraction & OCR Module (`test_api_uploads.py`, 8 tests)**:
   - Multi-format ingestion (PNG, JPEG, PDF), bad file rejection. Note: 2 tests requiring host tesseract binary are safely skipped when running without tesseract installed locally, and run in Docker/CI.

---

## 9. CI/CD & Deployment Readiness

### 9.1 GitHub Actions CI Pipeline (`.github/workflows/ci.yml`)
- Runs on pushes and PRs to `main`, `master`, and feature branches.
- Tests against supported Python matrix (`3.11`, `3.12`).
- Boots a real PostgreSQL 16 container as a CI service with automated healthchecks.
- Provisions database schema and seed data before running tests.
- Audits repository to guarantee no `.env` secret files are tracked in source control.
- Validates Docker Compose configuration and placeholder-only environment templates.
- Does **not** perform speculative automated production deployments on push.

### 9.2 Container Orchestration (`docker-compose.yml`)
Four production-ready services with persistent storage, health checks, and startup ordering:
1. `brandledger_db` (PostgreSQL 16 Alpine, port 5433)
2. `backend` (FastAPI backend, port 8000, depends on db healthy)
3. `agent` (Fetch.ai uAgent & ACP chat service, port 8001, depends on backend healthy)
4. `frontend` (Next.js 16 UI, port 3000, depends on backend healthy)

Detailed deployment steps, production secret requirements, and health checks are documented in **[docs/deployment.md](docs/deployment.md)**.

---

## 10. API Documentation

When the FastAPI backend is running, interactive API documentation is automatically available:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Key documented endpoints:
- `GET /health`: Service health check.
- `GET, POST, PATCH /api/policies`: Policy card authoring, listing, and versioning.
- `POST /api/scans`: Execute compliance scan against draft text with database persistence.
- `POST /api/scans/upload`: Multipart file upload with OCR/PDF text extraction.
- `POST /api/reviews`: Submit reviewer approval/rejection decision (enforces role authorization).
- `GET /api/passports/{id}`: Retrieve issued Content Passport with on-the-fly cryptographic SHA-256 verification.
- `POST /api/gate/publish`: Authenticated CMS publication gate (HMAC-SHA256 signature required).
- `GET /api/gate/{event_id}`: Retrieve recorded publication decision and evidence audit receipt.

---

## 11. Project Documentation Links

Comprehensive documentation generated for hackathon review:

- **Deployment & Operations Guide (Phase 5)**: [docs/deployment.md](docs/deployment.md)
  *Container configuration, CI/CD behavior, production secret hardening, and Agentverse registration.*
- **System Architecture**: [docs/architecture.md](docs/architecture.md)  
  *Detailed end-to-end data flow, database entity relationships, component boundaries, and security model.*
- **Acceptance Testing Specification**: [docs/acceptance-tests.md](docs/acceptance-tests.md)  
  *Feature-by-feature acceptance criteria, test execution baseline, and edge case coverage.*
- **3-Minute Demo Presentation Script**: [docs/demo-script.md](docs/demo-script.md)  
  *Timed 180-second pitch guide, verified demo snippets, contingency fallbacks, and judges Q&A defense matrix.*

---

## 11. Known Limitations & Architectural Boundaries

In accordance with strict hackathon transparency guidelines:

1. **Simulated Role Authorization (`X-User-Role`)**:
   Role enforcement in `backend/app/api/reviews.py` is simulated via HTTP headers (`X-User-Role: reviewer` or `admin`). While this effectively prevents accidental creator self-approval (`X-User-Role: creator` &rarr; HTTP 403), it is a development simulation and **not** a production authentication system (e.g., cryptographic JWTs, OAuth2, or session cookies).

2. **Frontend UI Boundary vs. Backend Routes**:
   The Next.js frontend implements the **Policy Library** (`/policies`), **Brand Passport Governance View** (`/brand-passport`), and **Scan Workspace Integration Boundary** (`/workspace`). The human review approval gate and Content Passport retrieval are hosted directly on the FastAPI backend and interactively demonstrated in Swagger UI (`http://localhost:8000/docs`).

3. **Frontend API Envelope Mode**:
   In `frontend/src/lib/api/policyClient.ts`, enabling `NEXT_PUBLIC_USE_BACKEND_CRUD=true` expects a direct array from `GET /api/policies`, whereas the backend returns `{ items: [...], total: ... }`. The frontend operates stably in development using its localStorage/mock data adapter.

4. **Visual Check Persistence**:
   Image quality metrics (blur, resolution, estimated contrast) from the extraction module are returned in the API response of `POST /api/scans/upload`, but only text compliance violations are persisted into the PostgreSQL `findings` table.

5. **Contrast Calculations**:
   Visual contrast assessments are calculated estimates across OCR bounding boxes; they do not represent official WCAG accessibility compliance audits (`wcag_verified: false`).

6. **Prototype Status**:
   This codebase is a hackathon proof-of-concept demonstrating verifiable brand compliance and Content Passporting. It is **not** certified for production environments.

---

## 12. Team Responsibilities & Ownership

| Team Member | Module Ownership | Deliverables |
|---|---|---|
| **Sana Fria** | Frontend Architecture & Scan Workspace (Member 1) | Interactive draft submission, real-time finding highlights & reviewer workflow specification (`/workspace`). |
| **Nimra Tariq** | Policy Library & Brand Passport UI (Member 2) | Authoritative brand policy management, versioning panel, brand voice pillars & governance passport (`/policies`, `/brand-passport`). |
| **Zoya Nadeem** | Backend API, Database Persistence & Review Engine (Member 3) | FastAPI route orchestration, PostgreSQL schema/migrations, scan/review persistence, and Content Passport issuance. |
| **Zynab Farhan** | Deterministic Rules Engine & Evidence Verification (Member 4) | "No receipt, no flag" rule checks (terminology, expired offers, numerical limits, unsupported claims), evidence verifier. |
| **Mahadevi Sabarad** | Extraction & Visual OCR Module (Member 5) | Multi-format file extractor (PDF/images), Tesseract OCR integration, visual quality warning flags. |
| **Umme Haany Tandur** | QA, Integration, Documentation & Submission Lead (Member 6) | Acceptance test suite, test audit & negative tests, system architecture docs, demo script & verification checklist. |
