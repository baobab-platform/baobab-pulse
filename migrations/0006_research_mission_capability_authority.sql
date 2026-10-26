-- Legacy rows retain NULL provenance; new writes always supply current CP authority.
ALTER TABLE intelligence.research_mission_mutation_audit
 ADD COLUMN IF NOT EXISTS resolution_id text,
 ADD COLUMN IF NOT EXISTS grant_id text,
 ADD COLUMN IF NOT EXISTS binding_id text,
 ADD COLUMN IF NOT EXISTS provider_id text,
 ADD COLUMN IF NOT EXISTS engine_instance_id text,
 ADD COLUMN IF NOT EXISTS authority_expires_at timestamptz;
