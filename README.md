# VerifiBrand

Verifiable brand compliance and cryptographic content passporting.

🌐 **Live Demo**: [https://verifibrand-9h26.vercel.app/](https://verifibrand-9h26.vercel.app/)

---

## Overview

VerifiBrand streamlines brand compliance reviews with deterministic scanning, verifiable rule receipts, and tamper-proof digital certificates:

- **Deterministic Scanning**: Evaluates collateral against terminology, offer validity, numerical facts, and claims substantiation.
- **"No Receipt, No Flag"**: Every flagged issue links directly to an active policy ID, version snapshot, and verbatim rule quotation.
- **Review Gating**: Enforces role separation to prevent creator self-approval.
- **Cryptographic Passports**: Generates immutable certificates with canonical SHA-256 fingerprints to detect post-approval tampering.

---

## Tech Stack

- **Frontend**: Next.js, React, TypeScript
- **Backend**: FastAPI, Python 3.11+, Pydantic v2
- **Database**: PostgreSQL 16
- **Extraction**: PyMuPDF, Tesseract OCR

---

## Quickstart

### Using Docker Compose (Recommended)

Start the entire application stack:

```bash
docker compose up --build
```

- **Web App**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Local Development

1. **Database**:
   ```bash
   docker compose up brandledger_db -d
   ```

2. **Backend**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Testing

```bash
# Backend test suite
pytest backend/tests

# Frontend tests
cd frontend && npm test
```

---

## Team

- [Sana Fria](https://github.com/sanafria)
- [Nimra Tariq](https://github.com/nimrafshaikh-sketch)
- [Zoya Nadeem](https://github.com/zoyatahasildar)
- [Zynab Farhan](https://github.com/zynab983)
- [Mahadevi Sabarad](https://github.com/madhusabarad)
- [Umme Haany Tandur](https://github.com/ummehaany)
