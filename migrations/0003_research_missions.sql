-- P-CAP-04: durable canonical persistence for ResearchMission.
--
-- ResearchMission is a governed Pulse aggregate. Store the complete canonical
-- payload as JSONB while extracting tenant/status/classification for structural
-- tenant filtering and operational inspection. The repository always queries
-- tenant-scoped reads by (id, tenant_id); a caller never hydrates a foreign
-- tenant's mission and filters it afterwards.

CREATE TABLE IF NOT EXISTS intelligence.research_missions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    classification TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS research_missions_tenant_idx
    ON intelligence.research_missions (tenant_id);

CREATE INDEX IF NOT EXISTS research_missions_tenant_status_idx
    ON intelligence.research_missions (tenant_id, status);
