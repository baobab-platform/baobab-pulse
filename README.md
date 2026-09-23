# Baobab Pulse

Baobab Pulse is the Baobab Platform's **Intelligence, Research and Evidence
Engine** — a headless, API-first, event-driven, multi-tenant service that
turns external data, other Baobab engines' events, and documentary evidence
into traceable, contextualised, time-aware intelligence.

> **Status:** Scaffold — domain model, application services, the Haystack
> anti-corruption layer, a headless API boundary, and a deterministic
> reference research pipeline are implemented and tested. PostgreSQL carries
> a minimal canonical schema for `EvidenceSet` (see `ADR-PULSE-011`), with
> Qdrant as a rebuildable semantic-retrieval projection alongside it — the
> full physical schema for every other aggregate is still pending. No
> production intelligence domain (FX, commodities, trade statistics, ...) is
> implemented. See "Current implementation status" below.

## What Pulse is

Pulse continuously acquires, normalises, preserves, correlates, and
analyses evidence so Baobab-consuming organisations can understand what is
happening, what changed, why it may matter, what evidence supports an
assessment, and which decisions merit human consideration. See
`docs/adr/Baobab Pulse Intelligence Engine.md` (`ARCH-PULSE-001`) for the
full architectural mission.

## What Pulse is not

- **Not an ERP, commerce, or content system.** iDempiere, MedusaJS, and
  Payload CMS remain the systems of record for their domains; Pulse
  consumes their events/APIs, never their databases.
- **Not the Baobab Control Plane.** Tenant, market, context, and canonical
  entity identities are owned by `nabhold/baobab-cp` and referenced, never
  redefined, here.
- **Not an LLM wrapper.** Pulse remains functional for deterministic,
  rule-based and statistical intelligence without an LLM. AI is a
  capability inside Pulse, not its architectural centre.
- **Not a Haystack application with Baobab scripts glued on.** The
  dependency direction is the reverse: Baobab domain and application code
  is the core; Haystack is one embedded, replaceable engine behind a single
  anti-corruption boundary. See "Why Haystack" below.

## Why Haystack, and how it fits behind Pulse's boundaries

Pulse uses [deepset Haystack](https://haystack.deepset.ai) (`haystack-ai==3.1.1`,
verified to officially support Python 3.14) as its embedded AI
orchestration engine — components, pipelines, retrieval, generation, and
(future) agents/tools. Haystack is treated exactly like Baobab treats
MedusaJS, iDempiere, or Payload CMS: a specialist engine embedded behind a
Baobab-owned boundary, never the domain model itself.

```text
BAOBAB PULSE
│
├── Domain Model, Application Services, Canonical Contracts,
│   Provenance, Evidence, Quality, Temporal Semantics, Tenancy,
│   Security, Research, Intelligence Products
│
└── Haystack Integration Boundary (src/baobab_pulse/infrastructure/haystack/)
       │
       ├── Components   (EvidenceContextComponent, ClaimGroundingComponent)
       ├── Pipelines    (the reference research pipeline)
       ├── Tools        (BaobabToolContract -> haystack.tools.Tool)
       ├── Generators   (provider-neutral ModelExecutionPort adapter)
       ├── Document Stores (rebuildable retrieval projections)
       └── Tracing      (OpenTelemetry bridge)
```

Only `infrastructure/haystack/` imports `haystack` — enforced mechanically
by `tests/architecture/test_dependency_boundaries.py`. Full reasoning,
alternatives considered, and the upgrade/exit strategy are in
`docs/adr/ADR-PULSE-010 — Embedding Deepset Haystack as Pulse's Headless AI Orchestration Engine.md`.

**The test that matters:** if Baobab replaced Haystack tomorrow, would
Pulse's domain survive? Yes — `ResearchMission`, `Evidence`, `Observation`,
`Insight`, `Opportunity`, `Risk`, `Recommendation`, `Decision`, tenant
context, the API, and the event contracts are defined without importing
Haystack anywhere. Only the two reference components, one pipeline, and the
adapters in `infrastructure/haystack/` would need rewriting.

## Why Qdrant, and how PostgreSQL stays canonical

Pulse uses [Qdrant](https://qdrant.tech) (`qdrant-client`, `qdrant-haystack`)
as a **derived, rebuildable semantic-retrieval projection** — never as
canonical persistence. PostgreSQL remains the sole source of truth for every
canonical entity (`EvidenceSet`, and every other aggregate as its schema
lands); Qdrant only ever holds a projection of already-canonical PostgreSQL
data, embedded for similarity search:

```text
PostgreSQL (canonical)                Qdrant (derived projection)
─────────────────────                 ───────────────────────────
EvidenceSet, Evidence                 one embedded point per Evidence entry,
  id, version, tenant_id,      ──►     tagged with the SAME canonical_object_id /
  classification, text                evidence_set_id / canonical_version /
                                       tenant_id / classification

EvidenceRetrievalService.search()
  1. require_tenant_context()          — fail closed; never an unrestricted query
  2. SemanticRetrievalPort.retrieve_evidence(query)
       -> Qdrant, tenant + classification filtered structurally, pre-query
  3. compare each hit's canonical_version against PostgreSQL's current
     version (EvidenceSetHydrationPort.current_version) -> flag is_stale
  4. hydrate_for_pipeline() reads TEXT BACK FROM POSTGRESQL, never from
     Qdrant's cached payload
```

A total loss of Qdrant degrades to "semantic retrieval temporarily
unavailable" (`SemanticRetrievalUnavailable`/`VectorStoreUnavailable`,
mapped to a retryable `502`/`503` `application/problem+json` response) —
never lost canonical data, and never a rollback of a PostgreSQL write:
`QdrantEvidenceProjectionStore` is not on the write path of any canonical
transaction. `scripts/rebuild_projection.py` (`make rebuild-projection`)
rebuilds every projection from canonical PostgreSQL data at any time — the
documented recovery path after any Qdrant data loss.

`qdrant_client`/`haystack_integrations` types (`PointStruct`, `Filter`,
`ScoredPoint`, Haystack's Qdrant `Document`/retriever types) never leave
`infrastructure/haystack/document_stores/qdrant_projection_store.py` —
enforced by the same `tests/architecture/test_dependency_boundaries.py`
mechanism that isolates bare Haystack. Application/domain/contracts code
only ever sees `VectorProjectionPort`/`SemanticRetrievalPort`/`EmbeddingPort`
and their plain Pulse types (`ProjectionRecord`, `SemanticCandidate`,
`EmbeddingVector`). Collection identity is entirely configuration-driven
(`Settings.qdrant_collection_prefix`/`qdrant_evidence_collection_version`,
resolved by `resolve_collection_name`) — reindexing into a new physical
collection is a deploy-time configuration change, never a runtime
recreate-in-place code path. Full reasoning, alternatives considered, and
the exit strategy are in
`docs/adr/ADR-PULSE-011 — Qdrant Vector Retrieval and Semantic Projection Architecture.md`.

## Architecture

```text
Domain            (baobab_pulse.domain)           — no external dependencies
   ^
Application       (baobab_pulse.application)      — depends on domain + its own ports
   ^
Ports             (baobab_pulse.application.ports) — Protocol interfaces
                    (..., VectorProjectionPort, SemanticRetrievalPort, EmbeddingPort)
   ^
Infrastructure    (baobab_pulse.infrastructure)    — implements ports
   ^
Haystack Adapter  (baobab_pulse.infrastructure.haystack) — the only Haystack import site
```

See `docs/architecture/overview.md` for Mermaid diagrams of the package
graph, the Haystack boundary, deployment topology, and the canonical
acquire-to-intelligence data flow, and
`docs/architecture/api-framework-decision.md` for why FastAPI.

## Repository structure

```text
src/baobab_pulse/
├── domain/            Canonical intelligence domain (ARCH-PULSE-CIM-001, ADR-PULSE-002)
│   ├── shared/         Value objects, enums, base types
│   ├── sources/ ingestion/ observations/ evidence/ signals/ analysis/
│   │   insights/ opportunities/ risks/ forecasting/ recommendations/
│   │   decisions/ models/ products/ research/
├── application/
│   ├── ports/          Protocol interfaces (PipelinePort, ModelExecutionPort,
│   │                    VectorProjectionPort, SemanticRetrievalPort, EmbeddingPort, ...)
│   └── services/       ConfidenceService, QualityService, ResearchMissionService,
│                        EvidenceRetrievalService
├── contracts/          Wire shapes: CloudEvents envelope, RFC 9457 errors, API schemas
├── infrastructure/
│   ├── haystack/        The anti-corruption layer (see above)
│   │   ├── document_stores/  QdrantEvidenceProjectionStore (the only qdrant_client import site)
│   │   └── embedders/        HaystackEmbeddingAdapter (build_text_embedder/build_document_embedder)
│   ├── persistence/      asyncpg connectivity + PostgresEvidenceSetRepository + in-memory repositories
│   ├── object_storage/   Raw evidence storage (in-memory reference impl)
│   ├── messaging/        Transactional outbox
│   └── observability/    Structured logging + OpenTelemetry
├── ingestion/           SourceAdapter port (ADR-PULSE-003) + reference/normalisation
├── api/                 FastAPI app, routers (incl. /evidence/search), middleware, error handling
├── tenancy/             Structural tenant-context propagation
├── security/            Classification enforcement (incl. allowed_classifications for Qdrant filters)
└── configuration/       Typed, fail-fast settings (incl. Qdrant/embedding configuration)

tests/
├── unit/          domain, application, tenancy, security, infrastructure
├── integration/   real Haystack pipeline execution + embedded-Qdrant projection round trips
│                  (deterministic, no credentials; PostgreSQL-dependent tests skip gracefully
│                  with no live database)
├── api/           HTTP-boundary tests (e.g. fail-closed tenant enforcement)
├── architecture/  dependency-boundary + platform-invariant enforcement
└── contract/      validates PulseEventEnvelope/ProblemDetails against vendored schemas

docs/
├── adr/            ARCH-PULSE-001, ARCH-PULSE-CIM-001, ADR-PULSE-001..011
├── architecture/    diagrams and the API framework decision
└── security/        agent/tool security posture

migrations/        SQL migrations (schema boundaries, outbox table, evidence.evidence_sets)
scripts/           migrate.py, rebuild_projection.py (rebuild Qdrant from canonical PostgreSQL)
examples/          Runnable end-to-end reference pipeline demonstration
```

## Development setup

This repository uses the org's `baobab-dev` devcontainer image
(`.devcontainer/devcontainer.json`, `.nabhold/environment.yaml`) and `uv`
for Python dependency management.

```bash
uv sync --all-groups        # runtime + dev + security dependency groups
cp .env.example .env         # local configuration (no real secrets needed for tests)
make test                    # pytest, excludes the opt-in "provider" marker
make lint                    # ruff check
make typecheck                # mypy --strict
make security                  # bandit + pip-audit
uv run python examples/reference_research_pipeline.py   # runnable end-to-end demo
```

Local API + PostgreSQL + Qdrant: `docker compose up --build`, then
`curl localhost:8000/healthz` (PostgreSQL readiness; a hard gate) and
`curl localhost:8000/readyz` (also reports Qdrant readiness as its own,
non-blocking signal — see "Why Qdrant" above).

```bash
make migrate              # apply migrations/*.sql (creates evidence.evidence_sets, etc.)
make rebuild-projection   # rebuild the Qdrant evidence projection from canonical PostgreSQL
```

The default test suite (`make test`) needs neither a live PostgreSQL nor a
live Qdrant server: Qdrant-dependent tests run against Qdrant's embedded,
in-process mode (`PULSE_QDRANT_LOCATION=:memory:` — see `.env.example`), and
PostgreSQL-dependent integration tests skip gracefully when no reachable,
migrated database is configured.

**Toolchain note:** targets `requires-python = ">=3.14"`, matching
`nabhold/baobab-dev`'s pinned Python 3.14.x. See `ADR-PULSE-010`'s "Version
verification" section for the Haystack/Python 3.14 compatibility check and
a caveat encountered with a pre-release CPython build in one sandboxed
authoring session (not a real gap in Haystack or Python 3.14 support).

## Testing

- **Core suite requires no external services or model-provider
  credentials** (`make test`): domain/application unit tests, a real
  Haystack pipeline run against `MockChatGenerator`, real Qdrant
  upsert/retrieve/tenant/classification/staleness round trips against
  Qdrant's embedded in-process mode, dependency-boundary enforcement, and
  contract validation against vendored `baobab-platform/shared` JSON Schemas.
- **Architecture tests** (`tests/architecture/`) mechanically enforce the
  platform's dependency-boundary invariants — Haystack *and* Qdrant/
  `haystack_integrations` isolation (only
  `infrastructure/haystack/document_stores/qdrant_projection_store.py` may
  import either), no HTTP framework/DB driver in the domain, tenant context
  cannot be silently omitted, provider exceptions don't escape as raw
  exceptions, the reference pipeline is deterministic, canonical contracts
  never expose a Haystack or Qdrant SDK type, and the repository's
  dependency inputs are locked/pinned.
- **PostgreSQL-dependent integration tests**
  (`tests/integration/test_evidence_postgres_qdrant_roundtrip.py`) exercise
  the full canonical-write → project → search → hydrate round trip —
  including the tenant-isolation and stale-projection scenarios — against a
  real PostgreSQL. They skip gracefully (not fail) with no reachable,
  migrated database configured, and run for real in CI, which provisions
  PostgreSQL and Qdrant as service containers (`.github/workflows/ci.yml`).
- **API-boundary tests** (`tests/api/`) prove `/evidence/search` fails
  closed with 400 when no tenant context is bound, never reaching Qdrant
  with an unrestricted query.
- **Provider-specific tests** (opt-in, marked `@pytest.mark.provider`, none
  yet exist) will require real credentials and run separately from `make
  test`.

## Configuration

Twelve-factor, typed, fail-fast (`baobab_pulse.configuration.settings.Settings`,
`pydantic-settings`). See `.env.example` for every recognised
`PULSE_*` environment variable. Invalid configuration raises immediately at
`Settings()` construction with the exact field at fault.

## Security

- **Tenant isolation is structural**, not prompt-based:
  `tenancy.context.require_tenant_context()` and
  `security.classification.may_access`/`allowed_classifications` — see
  `docs/security/agent-and-tool-security.md` for how this extends to
  Haystack retrieval/tools.
- **Qdrant semantic retrieval fails closed**: a missing tenant context never
  reaches Qdrant as an unrestricted query (`EvidenceRetrievalService.search`
  calls `require_tenant_context()` before constructing a query); tenant and
  classification filters are built into the Qdrant/Haystack filter
  structurally, before the query is issued — never applied as a post-filter
  on an unrestricted result set, and never delegated to a model. A Qdrant
  similarity score is never conflated with Pulse confidence or evidence
  quality.
- **No mutating or `EXECUTE`-authority tool can be constructed** — see
  `infrastructure/haystack/tools/tool_adapter.py`.
- **Every Haystack/provider exception is translated** before it can leak a
  framework-specific structure through the public API
  (`infrastructure/haystack/errors.py`, `api/error_handlers.py`).
- Report vulnerabilities per `SECURITY.md` — never via a public issue.

## Tenancy

Every entity that participates in the evidence/intelligence chain carries a
`tenant_scope` (`GLOBAL`/`PLATFORM`/`TENANT`/`CONTEXT`/`PRIVATE`) and, where
required, a `tenant_context` referencing the Control-Plane-minted tenant id
— never a locally-invented one. See `domain/shared/base.GovernedEntity`.

## Integration boundaries

- **`baobab-platform/shared`**: canonical event envelope (CloudEvents profile) and
  RFC 9457 error contract are mirrored field-for-field in
  `contracts/events.py`/`contracts/errors.py`, validated in CI against
  vendored copies of the live schemas.
- **`nabhold/baobab-cp`**: Control Plane owns `CanonicalEntity`,
  `ExternalReference`, `Mapping`, `Market`, `DigitalEstate`, `Engine`,
  `Capability`, `Context`, `IsolationProfile` — Pulse references these by
  id, never redefines them.
- **MedusaJS / iDempiere / Payload CMS**: consumed through approved
  APIs/events only; direct database coupling is prohibited
  (`PULSE-003`).

## Current implementation status

Implemented and tested: the canonical domain model (all fifteen
ADR-PULSE-002 aggregates plus `ResearchMission`/`Claim`), application ports
and services, the Haystack anti-corruption layer with a deterministic
reference pipeline, a minimal headless API including `/evidence/search`,
`SourceAdapter` + reference/normalisation ingestion, PostgreSQL connectivity
plus a minimal canonical schema and repository for `EvidenceSet`, a Qdrant
semantic-retrieval projection (embed → upsert → tenant/classification-
filtered retrieve → canonical hydration → staleness detection) with a
rebuild CLI, the transactional outbox, and CI security/quality gates
(now provisioning PostgreSQL and Qdrant service containers).

Not yet implemented (deliberately, per the platform brief's "no premature
business code/infrastructure"): the full physical PostgreSQL schema for
every aggregate beyond `EvidenceSet`, a real (non-mock) embedding provider,
a real (non-reference) source adapter, a worker/scheduler deployment role,
entity resolution, any production intelligence domain (FX, commodities,
weather, trade statistics, ...), and any Haystack `Agent` instantiation.

## Roadmap

See `docs/adr/Baobab Pulse Intelligence Engine.md` §97-98 for the full ADR
family and derived-contract roadmap this scaffold works toward.

## Contributing

See `CONTRIBUTING.md`.
