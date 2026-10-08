-- Minimal canonical persistence for EvidenceSet (Qdrant refactor item 28-29,
-- 105, 108) — proves real PostgreSQL -> Qdrant -> hydration, without
-- inventing the full physical intelligence schema (still ADR-PULSE-011's
-- job). One JSONB payload column rather than a normalised Evidence/
-- EvidenceSet table pair: EvidenceSet is already a single frozen aggregate
-- (ADR-PULSE-002 AGG-PULSE-005/006), so a normalised join buys nothing here
-- that Postgres's own JSONB indexing doesn't already give us, and it keeps
-- the migration honestly scoped to "prove hydration works."
--
-- `canonical_version` and `classification` are pulled out into real columns
-- (not left buried in JSONB) because they are exactly what
-- application.services.evidence_retrieval_service needs to compare against
-- a Qdrant projection's recorded version (item 31: stale-projection
-- detection) and enforce classification without deserialising the payload
-- first.

CREATE TABLE IF NOT EXISTS evidence.evidence_sets (
    id TEXT PRIMARY KEY,
    tenant_id TEXT,
    classification TEXT NOT NULL,
    canonical_version INTEGER NOT NULL,
    payload JSONB NOT NULL,
    evidence_text JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS evidence_sets_tenant_idx ON evidence.evidence_sets (tenant_id);
