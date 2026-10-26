-- A completed resource read names the actual fresh CP grant and binding.
-- No bearer credentials, query text or evidence contents are persisted.
CREATE TABLE intelligence.evidence_read_audit (
    audit_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    context_id UUID NOT NULL,
    actor_subject TEXT NOT NULL,
    actor_client_id TEXT,
    resolution_id TEXT NOT NULL,
    grant_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    engine_instance_id TEXT NOT NULL,
    evidence_set_id TEXT,
    result_count INTEGER NOT NULL CHECK (result_count >= 0),
    occurred_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX evidence_read_audit_tenant_idx ON intelligence.evidence_read_audit(tenant_id,occurred_at);
CREATE FUNCTION intelligence.evidence_read_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'resource-read audit is append-only'; END $$;
CREATE TRIGGER evidence_read_audit_immutable BEFORE UPDATE OR DELETE ON intelligence.evidence_read_audit
FOR EACH ROW EXECUTE FUNCTION intelligence.evidence_read_audit_immutable();
