-- ==============================================================================
-- BrandLedger Core Database Schema (Supabase / PostgreSQL)
-- Owned by Zoya (Backend Lead)
--
-- Entities:
--   1. policy_cards & policy_card_versions (Living Brand Rules & Immutable History)
--   2. content_drafts (Submitted Content Lifecycle)
--   3. scans (Individual Scan Attempts)
--   4. findings (Evidence-Backed Rule Violations)
--   5. reviews (Human Review Decisions & Sign-offs)
--   6. passports (Immutable Content Passports & Verification Hashes)
-- ==============================================================================

-- Enable pgcrypto / uuid extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 1. POLICY CARDS & IMMUTABLE VERSIONS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS policy_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_key VARCHAR(100) UNIQUE,
    title VARCHAR(255) NOT NULL,
    card_type VARCHAR(50) NOT NULL CHECK (card_type IN ('terminology', 'offer', 'claim', 'fact', 'tone')),
    rule_text TEXT NOT NULL,
    approved_value TEXT,
    source_quote TEXT NOT NULL,
    valid_from DATE,
    valid_until DATE,
    severity VARCHAR(50) DEFAULT 'blocker' NOT NULL CHECK (severity IN ('blocker', 'warning', 'info')),
    status VARCHAR(50) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'inactive')),
    version INT DEFAULT 1 NOT NULL,
    rules JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Immutable policy version history to ensure historical findings & Passports never lose evidence
CREATE TABLE IF NOT EXISTS policy_card_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_card_id UUID NOT NULL REFERENCES policy_cards(id) ON DELETE CASCADE,
    version INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    card_type VARCHAR(50) NOT NULL,
    rule_text TEXT NOT NULL,
    approved_value TEXT,
    source_quote TEXT NOT NULL,
    valid_from DATE,
    valid_until DATE,
    severity VARCHAR(50) NOT NULL,
    rules JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE (policy_card_id, version)
);

CREATE INDEX IF NOT EXISTS idx_policy_cards_status ON policy_cards(status);
CREATE INDEX IF NOT EXISTS idx_policy_cards_card_type ON policy_cards(card_type);
CREATE INDEX IF NOT EXISTS idx_policy_card_versions_lookup ON policy_card_versions(policy_card_id, version);

-- ==============================================================================
-- 2. CONTENT DRAFTS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS content_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content_text TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' NOT NULL CHECK (status IN ('draft', 'in_review', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON content_drafts(status);

-- ==============================================================================
-- 3. SCANS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    scan_date DATE DEFAULT CURRENT_DATE NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_draft_id ON scans(draft_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);

-- ==============================================================================
-- 4. FINDINGS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    policy_card_id UUID REFERENCES policy_cards(id) ON DELETE SET NULL,
    policy_version VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('terminology', 'expired_offer', 'factual_accuracy', 'unsupported_claim', 'tone')),
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('blocker', 'warning', 'info', 'high', 'medium', 'low')),
    matched_text TEXT NOT NULL,
    source_quote TEXT NOT NULL,
    explanation TEXT NOT NULL,
    suggested_fix TEXT,
    confidence NUMERIC(3, 2) DEFAULT 1.00 NOT NULL,
    status VARCHAR(50) DEFAULT 'open' NOT NULL CHECK (status IN ('open', 'accepted', 'dismissed', 'resolved')),
    is_verified BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_scan_id ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_policy ON findings(policy_card_id, policy_version);

-- ==============================================================================
-- 5. REVIEWS (Human Decision Gate)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE RESTRICT,
    reviewer_id VARCHAR(100) NOT NULL,
    reviewer_name VARCHAR(255) NOT NULL,
    decision VARCHAR(50) NOT NULL CHECK (decision IN ('approved', 'rejected')),
    comment TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_reviews_scan_id UNIQUE (scan_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_draft_id ON reviews(draft_id);

-- ==============================================================================
-- 6. CONTENT PASSPORTS (Immutable Audit Certificate)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS passports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES content_drafts(id) ON DELETE RESTRICT,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE RESTRICT,
    review_id UUID NOT NULL UNIQUE REFERENCES reviews(id) ON DELETE RESTRICT,
    passport_hash VARCHAR(64) NOT NULL,
    status VARCHAR(50) DEFAULT 'valid' NOT NULL CHECK (status IN ('valid', 'revoked')),
    metadata_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_passports_scan_id UNIQUE (scan_id)
);

CREATE INDEX IF NOT EXISTS idx_passports_draft_id ON passports(draft_id);
CREATE INDEX IF NOT EXISTS idx_passports_hash ON passports(passport_hash);
