# DEV-06 bound evidence-resource enforcement

Every evidence search requires authenticated Intelligence operation scope,
caller-bound CP context, a fresh normal CP capability resolution selecting this
provider/instance, and a durable PostgreSQL read audit before any data returns.
The request/response business contract is unchanged. Tenant headers, invented
estates, cached resolution IDs and caller-supplied provider or binding IDs cannot
replace authority. Canonical tenant/classification filters and hydration remain
in force. ResearchMission enforcement is a separate scope of work.

Configure all existing IAM/context settings and these deployment-owned values:

- `PULSE_CONTROL_PLANE_CAPABILITY_RESOLUTION_URL`: CP's HTTPS
  `/v1/capabilities/resolve` endpoint.
- `PULSE_CAPABILITY_PROVIDER_ID`: the actual CP-minted `provider_…` identifier.
- `PULSE_ENGINE_INSTANCE_ID`: the actual CP-minted `ei_…` identifier.

The actual inbound caller token must be registered/requested for both CP and
Pulse audiences and carry `context:resolve` plus `intelligence:evidence:search`.
The independent context validator token never becomes the external caller and
cannot grant entitlement. Missing authority or audit configuration fails closed;
production composition refuses an incomplete configuration. There is no bypass
switch for the old direct-component path. Existing deployments must obtain their
normal CP subscription/grant, registered provider, governed activation, current
health and binding before sending resource traffic through this implementation.

CP resolves every call using its current source/projection, grant, binding,
provider/support, topology/health and residency checks and records the decision.
Pulse requires matching context, nonce/correlation, contract major, logical service,
provider and instance, canonical authority IDs, recent resolution and future expiry.
Transport is TLS verified, no redirects/cache, bounded to 16 KiB and three seconds.
A denial is 403, an unavailable authority/audit 503, a context not owned 404;
authentication remains 401. No credentials or query/evidence contents enter audit.

The append-only `intelligence.evidence_read_audit` records the trusted tenant,
caller, context, actual resolution/grant/binding/provider/instance, selected
EvidenceSet and result count. Audit failure or expiry before delivery returns no
candidates. Reads are not an atomic CP/provider transaction; CP can change between
its decision and delivery. Every subsequent invocation revalidates, and this
bounded decision does not claim a distributed fencing guarantee.

Run `uv sync --locked --all-groups`, migrations, ruff, strict mypy and the full
non-provider suite. Owner PG17/Qdrant CI must execute the native audit/persistence
checks; local skipped database tests are not native evidence. Infrastructure must
rerun the unchanged INT-07 inventory against final merged source pins, verify
original report hashes and prove owned cleanup. Source mocks are never acceptance.
Development activation is not EA-09 certification, protected acceptance, production
permission, independent legal eligibility or commercial financial authority.
Rollback disables this capability route and restores reviewed source/configuration
as a unit; do not restore access by bypassing CP or the audit. DEV-10 stays paused.
