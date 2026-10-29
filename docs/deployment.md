# VerifiBrand Deployment, CI/CD, and Operations Guide

> **Authoritative Operations Manual for Phase 5**
> Covers environment configuration, container deployment, GitHub Actions CI/CD, end-to-end validation, production security hardening, and Fetch.ai Agentverse integration.

---

## 1. Architecture & Service Topology

VerifiBrand consists of four decoupled services designed for reproducible deployment and secure communication:

```mermaid
graph TD
    Client["Client / Browser / CMS"] -->|HTTPS| Frontend["Next.js 16 Frontend (:3000)"]
    Client -->|HMAC-SHA256 Webhook| Backend["FastAPI Backend (:8000)"]
    Frontend -->|REST API| Backend
    Backend -->|Internal Bridge| DB[("PostgreSQL 16 (:5433/5432)")]
    Agent["Fetch.ai Agent (:8001)"] -->|REST Queries| Backend
    ASI["ASI:One / Agentverse"] -->|ACP Chat Protocol / Mailbox| Agent
```

### Services Summary

| Service | Container Name | Port | Description | Healthcheck |
|---|---|---|---|---|
| **PostgreSQL 16** | `brandledger_postgres` | `5433:5432` | Relational store for drafts, scans, findings, reviews, passports, and gate events. | `pg_isready -U brandledger_user -d brandledger` |
| **FastAPI Backend** | `brandledger_backend` | `8000:8000` | Rules engine, evidence verifier, human review gate, and HMAC-authenticated publication gate. | `curl -f http://localhost:8000/health` |
| **Fetch.ai Agent** | `brandledger_agent` | `8001:8001` | Autonomous uAgent implementing ACP Chat Protocol for ASI:One compliance explanations. | Process loop / port bind |
| **Next.js Frontend** | `brandledger_frontend` | `3000:3000` | Web application interface for policy management, scan workspace, and governance views. | HTTP GET `/` |

---

## 2. Environment Variables & Secret Requirements

### 2.1 Configuration Matrix

| Variable | Required In Prod | Default (Dev) | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Operating mode: `development`, `testing`, or `production`. |
| `DATABASE_URL` | Yes | `postgresql://brandledger_user:brandledger_secret@localhost:5433/brandledger` | Connection DSN for PostgreSQL. In production, default password is strictly rejected. |
| `CMS_WEBHOOK_SECRET` | Yes | `brandledger_cms_default_secret_dev` | Shared secret for HMAC-SHA256 webhook signatures. In production, default/dev values or secrets <16 chars are strictly rejected. |
| `ALLOWED_ORIGINS` | Yes | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of CORS-allowed origins. |
| `AGENT_NAME` | No | `verifibrand_agent` | Display name for Fetch.ai agent. |
| `AGENT_PORT` | No | `8001` | HTTP port for agent communication. |
| `AGENT_SEED` | Yes | `verifibrand-agent-development-seed-do-not-use-in-prod` | Mnemonic seed phrase for agent cryptographic address. In production, default dev seed is strictly rejected. |
| `AGENT_ENDPOINT` | Conditional | `None` | Public HTTPS URL for incoming agent webhooks. In production, HTTPS is strictly enforced. |
| `AGENTVERSE_API_KEY` | Conditional | `None` | Agentverse API token for cloud mailbox and Almanac registry. |
| `AGENTVERSE_MAILBOX` | No | `false` | When `true`, routes agent traffic through Agentverse Cloud Mailbox (recommended behind firewalls/NAT). |
| `BRANDLEDGER_DISABLE_AI` | No | `false` | When `true`, forces 100% deterministic rule scanning without external LLM calls. |
| `OPENAI_API_KEY` | Optional | `""` | Optional external LLM API key for ambiguous claim/tone evaluation. |

### 2.2 Production Security Policies

VerifiBrand enforces automated security validations during application startup in `production`:
1. **Refusal of Insecure Secrets**: If `ENVIRONMENT=production`, both the backend (`backend/app/config.py`) and agent (`agent/config.py`) strictly refuse to boot if `CMS_WEBHOOK_SECRET` or `AGENT_SEED` contain development defaults, words such as `dev` or `test`, or have insufficient entropy.
2. **Database Credential Validation**: Default container passwords (`brandledger_secret`) are rejected in production.
3. **No Committed Secrets**: `.env` and `agent/.env` are ignored by Git. `.env.example` files contain sanitized placeholder strings only.
4. **Secret Masking**: All agent diagnostic and configuration logs redact seeds and API tokens (`agent.config.AgentConfig.get_safe_summary()`).
5. **Exact Raw-Byte HMAC Signatures**: Webhook signatures are verified in constant time (`hmac.compare_digest`) against the exact raw unparsed request body.
6. **Payload Conflict Protection**: The publication gate verifies that repeated `event_id` deliveries cannot cause duplicate processing or return a cached result for an altered payload (returns `HTTP 409 Conflict`).

---

## 3. Database Initialization & Migrations

VerifiBrand uses idempotent PostgreSQL DDL scripts:

1. **Schema Initialization (`database/schema.sql`)**:
   Defines all 7 core tables with strict constraints, foreign keys, and indexes:
   - `policy_cards` & `policy_card_versions`
   - `content_drafts`
   - `scans`
   - `findings`
   - `reviews`
   - `passports`
   - `publication_events` (with `payload_hash` column for idempotency conflict protection)

2. **Seed Data (`database/seed.sql`)**:
   Populates approved baseline brand rules and version history using safe `ON CONFLICT DO NOTHING` clauses.

3. **Runtime Schema Verification (`ensure_gate_schema()`)**:
   During FastAPI startup, `lifespan` runs `ensure_gate_schema()` to ensure the `publication_events` table and `payload_hash` column exist without requiring manual migration scripts.

---

## 4. Local Setup & Execution Commands

### 4.1 Prerequisites
- Python 3.11 or 3.12 (Python 3.13 also supported locally)
- Docker & Docker Compose
- Tesseract OCR (optional locally, installed in Docker/CI)

### 4.2 Local Python Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd BrandLedger

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r agent/requirements.txt

# 4. Configure local environment
cp .env.example .env
```

### 4.3 Database Startup

```bash
# Start PostgreSQL via Docker Compose
docker compose up -d brandledger_db

# Check database readiness
docker compose exec brandledger_db pg_isready -U brandledger_user -d brandledger
```

### 4.4 Running Backend & Agent Locally

```bash
# Terminal 1: Run FastAPI Backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Run Fetch.ai Agent
python -m agent.main
```

### 4.5 Full Containerized Orchestration

To run all four services (Database, Backend, Agent, Frontend) in Docker:

```bash
# Build and start all services in background
docker compose up --build -d

# View service logs
docker compose logs -f backend agent

# Check service health
docker compose ps
```

---

## 5. Automated CI/CD Workflow (`.github/workflows/ci.yml`)

The repository includes an automated GitHub Actions CI pipeline:

### Workflow Characteristics
- **Triggers**: On pull requests and pushes to `main`, `master`, `feat/**`, `feature/**`.
- **Python Matrix**: Explicitly tests against supported Python versions (`3.11`, `3.12`).
- **PostgreSQL Service Container**: Spins up a real `postgres:16-alpine` service on port 5433 with automated health checks.
- **Database Provisioning**: Executes `database/schema.sql` and `database/seed.sql` before tests run.
- **System Dependencies**: Installs `tesseract-ocr`, `tesseract-ocr-eng`, `postgresql-client`, and `curl`.
- **Reproducible Dependency Installs**: Installs `requirements.txt` and `agent/requirements.txt`.
- **Safe Test Configuration**: Injects test-only secrets (`CMS_WEBHOOK_SECRET`, `AGENT_SEED`) and forces deterministic scanning (`BRANDLEDGER_DISABLE_AI=true`).
- **Honest Test Reporting**: Runs all 131 tests with verbose duration reporting.
- **Security & Secret Audit**: Checks that `.env` files are not tracked in Git, `.env.example` contains only placeholders, and Docker Compose syntax is valid.
- **No Automatic Production Deployments**: Does not perform speculative deployments on CI runs.

---

## 6. End-to-End Validation Testing

A dedicated end-to-end integration test suite (`backend/tests/test_e2e_workflow.py`) exercises the complete cross-service lifecycle:

### Test Execution Commands

```bash
# Run End-to-End Integration Suite
pytest backend/tests/test_e2e_workflow.py -v

# Run Complete Repository Test Suite (133 Tests)
pytest backend/tests -v --durations=10
```

### Verified End-to-End Test Matrix

| Step | Test Name | Criteria Verified |
|---|---|---|
| **1–8** | `test_e2e_happy_path_publication_lifecycle` | Clean scan &rarr; Reviewer approval &rarr; Passport issuance &rarr; SHA-256 verification &rarr; Signed gate request &rarr; Decision: `PASS` (`PUBLICATION_AUTHORIZED`). |
| **4 & 9** | `test_e2e_blocking_content_rejected_at_scan_and_gate` | Prohibited terminology ("Customers") caught by scanner with literal policy receipt; gate evaluates to `BLOCK` (`ACTIVE_BLOCKING_FINDINGS`). |
| **9** | `test_e2e_unapproved_draft_blocked_at_gate` | Clean scan without human reviewer approval evaluated at gate &rarr; Decision: `BLOCK` (`DRAFT_NOT_APPROVED`). |
| **9** | `test_e2e_tampered_passport_blocked_at_gate` | Corrupted snapshot hash in database detected during on-the-fly gate verification &rarr; Decision: `BLOCK` (`PASSPORT_TAMPERED`). |
| **10** | `test_e2e_idempotency_and_conflict_protection` | Resending exact same payload returns cached decision (`duplicate=True`); resending same `event_id` with altered payload raises `HTTP 409 Conflict`. |
| **11** | `test_e2e_agent_actions_and_acp_against_backend` | Agent exercises Action A (compliance check), Action B (block explanation), Action C (passport verification), and ACP chat queries against live backend. |
| **12** | `test_e2e_unavailable_services_never_become_false_success` | Backend offline returns `success=False` and `decision="BLOCK"`; missing/invalid HMAC signatures return `401 Unauthorized`; malformed JSON returns `400 Bad Request`. |

---

## 7. Production Deployment & Health Checks

### 7.1 Production Deployment Procedure

When deploying to a production host (e.g., AWS ECS, GCP Cloud Run, DigitalOcean, or Kubernetes):

1. **Provision Managed PostgreSQL**:
   - Create private managed PostgreSQL instance (e.g. AWS RDS or Supabase).
   - Apply `database/schema.sql` and `database/seed.sql`.
   - Never expose PostgreSQL on public IP addresses.

2. **Generate Strong Production Secrets**:
   ```bash
   # Generate CMS Webhook Secret (at least 32 characters)
   openssl rand -hex 32

   # Generate 12 or 24 word mnemonic seed for Fetch.ai Agent
   # e.g., using python -c "from uagents import Agent; print(Agent().wallet.seed)"
   ```

3. **Configure Environment**:
   - Set `ENVIRONMENT=production`.
   - Set `DATABASE_URL` with secure production credentials.
   - Set `CMS_WEBHOOK_SECRET` to the generated secret.
   - Set `AGENT_SEED` to the private mnemonic phrase.
   - Set `ALLOWED_ORIGINS` to the exact frontend domain(s).

4. **Deploy Containers**:
   Deploy `backend` and `agent` container images built from `backend/Dockerfile` and `agent/Dockerfile`.

5. **Execute Health Checks**:
   ```bash
   # Backend Health Check
   curl -f https://api.yourdomain.com/health
   # Expected: {"status":"healthy","database":"connected","timestamp":"..."}

   # Gate Event Verification
   curl -I https://api.yourdomain.com/api/gate/health-probe
   ```

---

## 8. Agentverse Registration & Live ASI:One Verification

To register the VerifiBrand agent on Fetch.ai Agentverse and enable discovery in ASI:One:

### Prerequisites
- Account at [https://agentverse.ai](https://agentverse.ai).
- Agentverse API Key (Profile &rarr; API Keys).
- Public HTTPS URL or Agentverse Mailbox enabled.

### Registration Procedure

1. **Configure Agent Environment**:
   ```env
   AGENTVERSE_API_KEY=your_live_agentverse_api_token
   AGENTVERSE_MAILBOX=true
   AGENT_HANDLE=verifibrand
   ```

2. **Run Registration Utility**:
   ```bash
   python -m agent.register
   ```
   *The script registers the agent's cryptographic address, public metadata description, and search tags (`brand-safety`, `compliance`, `content-passport`, `asi-one`) on the Agentverse Almanac.*

3. **Live ASI:One Chat Verification**:
   - Log into the ASI:One portal.
   - Search for `@verifibrand` or query the agent directly.
   - Send: `"Verify brand passport <UUID>"` or `"Check compliance: Welcome Customers!"`.
   - The agent receives the message via the Agent Chat Protocol (ACP), queries the authoritative backend, and responds with verbatim evidence receipts and cryptographic verification status.

---

## 9. Known Limitations & Credential Boundaries

1. **Live External Verification**: Automated CI and local test suites validate the complete workflow against local services without requiring live external Agentverse API keys. Live Agentverse and ASI:One interactions require external network credentials and manual registration.
2. **Host Tesseract OCR**: When running tests natively on host OS without `tesseract` installed, OCR upload tests in `test_api_uploads.py` are safely skipped via `pytest.mark.skipif(not tesseract_available())`. In Docker and GitHub Actions CI, `tesseract-ocr` is installed and tests run in full.
3. **Role Enforcement (`X-User-Role`)**: Reviewer role authorization in `POST /api/reviews` simulates separation-of-duties access control via request headers. Production deployments should attach an API gateway or OAuth2/JWT middleware to validate reviewer identity tokens before proxying to the backend.
