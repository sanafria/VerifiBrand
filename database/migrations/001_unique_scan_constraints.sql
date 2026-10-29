-- ==============================================================================
-- Migration: 001_unique_scan_constraints.sql
-- Description: Enforce database-level uniqueness for reviews and Content Passports
-- Target Tables: reviews, passports
-- Author: Zoya (Backend Lead)
--
-- Background:
--   - Each scan represents an immutable compliance scan attempt.
--   - Business rule 1: At most one human review decision per scan.
--   - Business rule 2: At most one Content Passport certificate per scan.
--   - Existing constraint on passports.review_id ensures 1 passport per review,
--     but passports.scan_id requires an explicit UNIQUE constraint to prevent
--     multiple passports for the same scan via separate reviews.
--
-- Safety & Data Integrity Guarantees:
--   - Strictly non-destructive: Never deletes, truncates, or silently merges rows.
--   - Validates preconditions: Fails with a clear EXCEPTION if duplicate records
--     exist, aborting without modifying the schema or existing data.
--   - Idempotent: Uses PostgreSQL system catalog checks (pg_constraint) to safely
--     skip already-applied constraints on repeated executions.
--   - Removes redundant non-unique index idx_reviews_scan_id because PostgreSQL
--     automatically creates an underlying unique index for uq_reviews_scan_id.
--
-- How to Apply:
--   Direct via psql:
--     psql -h <host> -p <port> -U <user> -d brandledger -f database/migrations/001_unique_scan_constraints.sql
--
--   Via Docker Compose:
--     docker exec -i brandledger_postgres psql -U brandledger_user -d brandledger < database/migrations/001_unique_scan_constraints.sql
-- ==============================================================================

BEGIN;

DO $$
DECLARE
    dup_reviews_count INTEGER;
    dup_passports_count INTEGER;
BEGIN
    -- --------------------------------------------------------------------------
    -- 1. Precondition Check: Detect duplicate scan_ids in reviews
    -- --------------------------------------------------------------------------
    SELECT COUNT(*) INTO dup_reviews_count
    FROM (
        SELECT scan_id
        FROM reviews
        GROUP BY scan_id
        HAVING COUNT(*) > 1
    ) dups;

    IF dup_reviews_count > 0 THEN
        RAISE EXCEPTION 'Migration 001 aborted: Found % duplicate scan_id group(s) in reviews table. Clean up duplicates manually before applying uniqueness constraint.', dup_reviews_count;
    END IF;

    -- --------------------------------------------------------------------------
    -- 2. Add named UNIQUE constraint to reviews(scan_id)
    -- --------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_reviews_scan_id'
          AND conrelid = 'reviews'::regclass
    ) THEN
        ALTER TABLE reviews ADD CONSTRAINT uq_reviews_scan_id UNIQUE (scan_id);
        RAISE NOTICE 'Added UNIQUE constraint uq_reviews_scan_id on reviews(scan_id).';
    ELSE
        RAISE NOTICE 'Constraint uq_reviews_scan_id already exists on reviews table. Skipping.';
    END IF;

    -- --------------------------------------------------------------------------
    -- 3. Remove redundant non-unique index idx_reviews_scan_id if present
    -- --------------------------------------------------------------------------
    IF EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE tablename = 'reviews'
          AND indexname = 'idx_reviews_scan_id'
    ) THEN
        DROP INDEX idx_reviews_scan_id;
        RAISE NOTICE 'Dropped redundant non-unique index idx_reviews_scan_id.';
    END IF;

    -- --------------------------------------------------------------------------
    -- 4. Precondition Check: Detect duplicate scan_ids in passports
    -- --------------------------------------------------------------------------
    SELECT COUNT(*) INTO dup_passports_count
    FROM (
        SELECT scan_id
        FROM passports
        GROUP BY scan_id
        HAVING COUNT(*) > 1
    ) dups;

    IF dup_passports_count > 0 THEN
        RAISE EXCEPTION 'Migration 001 aborted: Found % duplicate scan_id group(s) in passports table. Clean up duplicates manually before applying uniqueness constraint.', dup_passports_count;
    END IF;

    -- --------------------------------------------------------------------------
    -- 5. Add named UNIQUE constraint to passports(scan_id)
    -- --------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_passports_scan_id'
          AND conrelid = 'passports'::regclass
    ) THEN
        ALTER TABLE passports ADD CONSTRAINT uq_passports_scan_id UNIQUE (scan_id);
        RAISE NOTICE 'Added UNIQUE constraint uq_passports_scan_id on passports(scan_id).';
    ELSE
        RAISE NOTICE 'Constraint uq_passports_scan_id already exists on passports table. Skipping.';
    END IF;

END $$;

COMMIT;
