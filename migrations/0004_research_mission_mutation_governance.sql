-- P-CAP-05: durable idempotency, audit provenance and HELD event candidates
-- for intelligence.research-mission.manage CREATE.
--
-- The Intelligence event context is still RESERVED in Shared. New outbox rows
-- are therefore HELD_UNREGISTERED and are not eligible for publication.

CREATE TABLE IF NOT EXISTS intelligence.research_mission_idempotency (
    tenant_id TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    capability_key TEXT NOT NULL DEFAULT 'intelligence.research-mission.manage',
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    request_payload JSONB NOT NULL,
    mission_id TEXT NOT NULL REFERENCES intelligence.research_missions(id) DEFERRABLE INITIALLY DEFERRED,
    result_fingerprint TEXT NOT NULL,
    context_id UUID NOT NULL,
    correlation_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, actor_subject, capability_key, idempotency_key),
    UNIQUE (mission_id),
    CHECK (char_length(idempotency_key) BETWEEN 16 AND 128)
);

CREATE TABLE IF NOT EXISTS intelligence.research_mission_mutation_audit (
    audit_id UUID PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES intelligence.research_missions(id),
    tenant_id TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    actor_client_id TEXT,
    context_id UUID NOT NULL,
    capability_key TEXT NOT NULL DEFAULT 'intelligence.research-mission.manage',
    operation TEXT NOT NULL CHECK (operation = 'CREATE'),
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    result_fingerprint TEXT NOT NULL,
    correlation_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, actor_subject, capability_key, idempotency_key)
);

ALTER TABLE intelligence.outbox
    ADD COLUMN IF NOT EXISTS tenant_id TEXT,
    ADD COLUMN IF NOT EXISTS actor_subject TEXT,
    ADD COLUMN IF NOT EXISTS subject_id TEXT,
    ADD COLUMN IF NOT EXISTS correlation_id UUID,
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
    ADD COLUMN IF NOT EXISTS envelope_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS publication_status TEXT NOT NULL DEFAULT 'LEGACY';

ALTER TABLE intelligence.outbox
    ADD CONSTRAINT outbox_publication_status_check
    CHECK (publication_status IN ('LEGACY', 'HELD_UNREGISTERED', 'PUBLISHABLE', 'PUBLISHED', 'DEAD_LETTER'));

CREATE INDEX IF NOT EXISTS outbox_publication_status_idx
    ON intelligence.outbox (publication_status, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS research_mission_outbox_idempotency_idx
    ON intelligence.outbox (tenant_id, actor_subject, idempotency_key, event_type)
    WHERE event_type = 'com.baobab-platform.intelligence.research-mission.created.v1'
      AND idempotency_key IS NOT NULL;
