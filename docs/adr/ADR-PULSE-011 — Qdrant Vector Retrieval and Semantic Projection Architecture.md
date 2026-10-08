# ADR-PULSE-011: Qdrant Vector Retrieval and Semantic Projection Architecture

**Status:** Accepted
**Classification:** Baobab Pulse Architecture — Implementation Decision
**Repository:** `nabhold/baobab-pulse`

## Numbering note

`ADR-PULSE-010`'s own numbering note reserved `ADR-PULSE-011` for "Tenant
Isolation and Data Classification." This ADR takes that number instead
because the Qdrant integration decision became necessary first — semantic
retrieval could not be added without deciding, concretely, how tenant and
classification isolation apply to a vector store (they turn out to be the
same structural mechanisms `ADR-PULSE-010` already used for Haystack,
applied one layer further out — see "Tenant and classification isolation"
below) — and `ARCH-PULSE-001` §97 allows additional ADRs as implementation
discovers genuine architectural decisions. A standalone Tenant Isolation and
Data Classification ADR, if the platform brief still wants one written up
independently of this decision, should be filed as `ADR-PULSE-012` (or
later).

## Context

Pulse's reference research pipeline (`ADR-PULSE-010`) retrieves evidence
from an in-memory projection sized for one synthetic demonstration corpus.
That is fine for proving the pipeline architecture but does not scale to a
real evidence corpus, and the platform brief requires semantic (embedding-
based) retrieval over governed evidence once workload evidence justifies it
(`ADR-PULSE-010`'s "RAG over governed evidence" section, item 31/114).

Baobab Pulse's persistence model is deliberately split by responsibility
(`ARCH-PULSE-001`, `ADR-PULSE-002`): PostgreSQL is canonical operational
persistence for every intelligence aggregate (`ResearchMission`, `Source`,
`Dataset`, `Observation`, `Evidence`, `Provenance`, `Lineage`, `Signal`,
`Insight`, `Opportunity`, `Risk`, `Forecast`, `Recommendation`, `Decision`,
`Outcome`, `Model`, `Tenant`, `Classification`). A vector database sits
outside that list — it is not one of ADR-PULSE-002's aggregates and SHALL
NOT become one. This ADR decides how semantic retrieval is added without
violating that.

## Decision

Use **Qdrant** (`qdrant-client==1.19.0`, `qdrant-haystack==10.6.0`, via
Haystack's own `QdrantDocumentStore`/`QdrantEmbeddingRetriever`) as a
**derived, rebuildable semantic-retrieval projection** of canonical
PostgreSQL data — never as canonical persistence for anything. PostgreSQL
remains the sole source of truth; a total loss of Qdrant is "semantic
retrieval temporarily unavailable," never "canonical intelligence lost."

## Version verification

Verified directly against PyPI's JSON API (not training-data recall),
matching `ADR-PULSE-010`'s verification discipline:

```text
$ curl -s https://pypi.org/pypi/qdrant-client/json | jq '.info.version, .info.requires_python'
"1.19.0"
">=3.10"

$ curl -s https://pypi.org/pypi/qdrant-haystack/json | jq '.info.version'
"10.6.0"
$ curl -s https://pypi.org/pypi/qdrant-haystack/json | jq '.info.requires_dist' | grep -i -E "haystack|qdrant"
"haystack-ai>=2.29.0"
"qdrant-client>=1.17.0"
```

`qdrant-client` 1.19.0 supports Python 3.10-3.14 — no gap against Pulse's
`requires-python = ">=3.14"`. `qdrant-haystack` 10.6.0 requires
`haystack-ai>=2.29.0` and `qdrant-client>=1.17.0`, both satisfied by the
versions already pinned (`haystack-ai==3.1.1`, `qdrant-client>=1.19,<2`).
No Haystack version change was needed to add Qdrant.

Confirmed by downloading and inspecting the actual installed wheels
(`haystack_integrations.document_stores.qdrant.QdrantDocumentStore`,
`haystack_integrations.components.retrievers.qdrant.QdrantEmbeddingRetriever`)
rather than assumed from memory, since Haystack's own document-store/
retriever contract (not just Qdrant's) is what this integration depends on.

## Why Qdrant does not become canonical

`ARCH-PULSE-001`/`ADR-PULSE-002`'s aggregate list is exhaustive and
Control-Plane-anchored; a vector database is architecturally a *retrieval
index*, not a system of record, for the same reason `InMemoryDocumentStore`
in `ADR-PULSE-010` was never canonical. Concretely, in this codebase:

- `PostgresEvidenceSetRepository` (`infrastructure/persistence/evidence_repository.py`)
  is the only place an `EvidenceSet`/`Evidence` is durably written or read
  as *the* record — `migrations/0002_evidence.sql`'s
  `evidence.evidence_sets` table.
- `QdrantEvidenceProjectionStore` never receives a write that did not
  already succeed in PostgreSQL first — projection always happens *after*
  a canonical write, never instead of one, and Qdrant unavailability never
  blocks or rolls back that canonical write (see "Eventual consistency and
  failure isolation" below).
- Every Qdrant point carries `canonical_object_id`, `evidence_set_id`, and
  `canonical_version` — a reference back to the canonical row, never a
  copy that could silently diverge and be mistaken for the original.

## Ports: keeping Qdrant behind Pulse's own vocabulary

Mirroring `ADR-PULSE-010`'s `PipelinePort`/`ModelExecutionPort` pattern,
three new `application.ports` Protocols exist so application/domain code
never depends on Qdrant or Haystack's Qdrant integration directly:

- **`EmbeddingPort`** (`application/ports/embedding_port.py`) —
  `embed_text`/`embed_batch`/`model_identity`/`dimension`, returning a
  plain `EmbeddingVector` (never a `numpy` array or provider tensor type).
- **`VectorProjectionPort`** (`application/ports/vector_projection_port.py`)
  — the write side: `upsert_projection`/`upsert_batch`/`delete_projection`/
  `delete_by_source`/`replace_projection`/`rebuild_projection`, operating
  on a plain `ProjectionRecord`.
- **`SemanticRetrievalPort`** (`application/ports/semantic_retrieval_port.py`)
  — the read side: `retrieve_evidence(EvidenceRetrievalQuery) ->
  tuple[SemanticCandidate, ...]`.

`QdrantEvidenceProjectionStore`
(`infrastructure/haystack/document_stores/qdrant_projection_store.py`)
implements all three. It is the **only** module in the codebase that
imports `qdrant_client` or `haystack_integrations` — enforced mechanically
by the same AST-scanning mechanism `ADR-PULSE-010` uses for bare
`haystack` (`tests/architecture/test_dependency_boundaries.py`'s
`test_only_the_haystack_infrastructure_package_imports_qdrant` and its
domain/application/contracts-specific companions). `qdrant_client.PointStruct`,
`Filter`, `FieldCondition`, and `ScoredPoint` — and Haystack's own Qdrant
`Document`/retriever types — never cross back out of that one module.

`HaystackEmbeddingAdapter` (`infrastructure/haystack/embedders/embedding_adapter.py`)
implements `EmbeddingPort` by wrapping Haystack's own deterministic,
credential-free `MockTextEmbedder`/`MockDocumentEmbedder` — the same
principle `ADR-PULSE-010` already applied to `ModelExecutionPort`/
`MockChatGenerator`: the core test suite and the projection rebuild path
never require a model-provider API key or a downloaded embedding model.
`build_text_embedder`/`build_document_embedder` are the only place an
embedding provider name resolves to a concrete class — a real embedding
provider is a future, separately-reviewed addition there, not a redesign
of the port.

## Haystack integration specifics

`QdrantEvidenceProjectionStore` wraps Haystack's own
`QdrantDocumentStore`/`QdrantEmbeddingRetriever` — the same "specialist
engine behind a Baobab-owned boundary" relationship `ADR-PULSE-010`
establishes for the rest of Haystack, one layer further in:

- **Filter construction uses Haystack's own dict-based filter DSL**
  (`{"operator": "AND", "conditions": [...]}`), not a raw
  `qdrant_client.models.Filter`. This is what keeps a Qdrant SDK filter
  type from ever needing to be constructed outside this one module.
- **Collection naming is configuration-driven, never hard-coded**:
  `resolve_collection_name(ProjectionCollection.EVIDENCE, prefix=...,
  version=...)` maps a logical collection role (`ProjectionCollection`, a
  `StrEnum` with one member today — only what current code justifies) to a
  physical name, e.g. `baobab-pulse-evidence-v1`, driven by
  `Settings.qdrant_collection_prefix`/`qdrant_evidence_collection_version`.
- **Embedded, in-process mode (`location=":memory:"`) is a genuine Qdrant
  engine**, not a hand-rolled fake — verified empirically that a fresh
  `QdrantDocumentStore(location=":memory:")` instance never sees another
  instance's points even under the same collection name, so the test suite
  gets real tenant/classification-filtered retrieval behaviour with no
  live server and no shared state between tests.

## Projection model

`ProjectionRecord` (write side) / `SemanticCandidate` (read side) are the
only shapes that cross the port boundary:

```text
ProjectionRecord:
    canonical_object_id      -- the canonical Evidence.id
    evidence_set_id          -- the owning EvidenceSet.id (hydration key)
    canonical_version        -- EvidenceSet.version AT PROJECTION TIME
    tenant_id, classification, valid_from/valid_to
    content, content_hash    -- the resolved text this projection embeds
    embedding_model_id, embedding_model_version
    projection_version       -- schema/mapping version of the projection itself
```

`canonical_version` records the *owning `EvidenceSet`'s* `.version` — bare
`Evidence` carries no independent version in this domain model
(`AGG-PULSE-005/006`; only `EvidenceSet` is the versioned aggregate root).
This is a deliberate, documented interpretation, not an invented domain
field: the alternative (versioning bare `Evidence`) would require an
`ADR-PULSE-002` amendment this refactor does not make.

## Tenant and classification isolation

Structural, not prompt-based — the same principle `security/classification.py`
and `tenancy/context.py` already state for Haystack retrieval, extended to
Qdrant:

1. `EvidenceRetrievalService.search()` calls
   `tenancy.context.require_tenant_context()` **before** constructing a
   query. An unbound tenant context raises `TenantContextMissingError`
   (mapped to HTTP 400) — a semantic query is never issued without one.
2. `EvidenceRetrievalQuery.tenant_context` is a required (non-`Optional`)
   field — there is no code path that constructs a query with no tenant.
3. `QdrantEvidenceProjectionStore.retrieve_evidence` builds the tenant
   (`meta.tenant_id == tenant_id`) and classification
   (`meta.classification in allowed_classifications(requester_clearance)`)
   filter **before** issuing the query to Qdrant — never as a post-filter
   on an unrestricted result set, and never left to a model to "ignore."
   `security.classification.allowed_classifications` (new in this
   refactor) returns every classification level a clearance may access,
   used directly as the Qdrant `in` filter's value list.
4. A degenerate empty `tenant_id` (should never occur given (1)-(2), but
   defended against anyway) raises `SemanticRetrievalUnavailable` rather
   than silently querying without a tenant filter.

Qdrant's similarity `score` is carried through `SemanticCandidate`/
`HydratedEvidenceCandidate` as exactly that — a retrieval-ranking signal —
and is never written into, or conflated with, a Pulse `Confidence`/
`ConfidenceBand`/evidence-quality field (`ADR-PULSE-009`'s
`QUAL-PULSE-021`/`QUAL-PULSE-007` distinctions apply here unchanged).

## Canonical hydration and staleness detection

A Qdrant point is never treated as authoritative on its own:

1. `EvidenceRetrievalService.search()` compares each candidate's recorded
   `canonical_version` against PostgreSQL's *current* version
   (`EvidenceSetHydrationPort.current_version`, backed by
   `PostgresEvidenceSetRepository.current_version` — one integer column,
   not a full payload deserialisation) and flags `is_stale` accordingly.
2. If the canonical source has been deleted entirely (`current_version`
   returns `None`), the candidate is dropped outright — an orphaned Qdrant
   point is never evidence of anything.
3. `hydrate_for_pipeline()` reads text back from PostgreSQL
   (`EvidenceSetHydrationPort.get_with_text`), never from Qdrant's cached
   payload, and raises `InvariantViolation` if every candidate is stale or
   if candidates span more than one `EvidenceSet` (a deliberate scope
   limit — composing several `EvidenceSet`s into one synthetic aggregate
   would cross `AGG-PULSE` aggregate boundaries and needs its own
   ADR-governed design, not an implicit merge here).

This is the concrete mechanism behind the platform brief's verification
scenario: Evidence `E123` (tenant `T1`, `CONFIDENTIAL`,
`canonical_version=7`) projected into Qdrant is retrievable and hydratable
by `T1` cleared for `CONFIDENTIAL`; invisible to tenant `T2` regardless of
clearance; and, once PostgreSQL advances to `canonical_version=8` while
Qdrant still reports 7, flagged stale and excluded from pipeline hydration
— proven end-to-end by
`tests/integration/test_evidence_postgres_qdrant_roundtrip.py`.

## Eventual consistency and failure isolation

Qdrant is never on the write path of a canonical PostgreSQL transaction:

- `VectorStoreUnavailable` (base) / `SemanticRetrievalUnavailable` /
  `ProjectionWriteFailed` / `ProjectionRebuildFailed` are Pulse's own typed
  errors (`domain/shared/errors.py`) — every `qdrant_client`/`httpx`
  exception is translated into one of these at the
  `QdrantEvidenceProjectionStore` boundary and mapped to a retryable
  `502`/`503` `application/problem+json` response
  (`api/error_handlers.py`). They SHALL NOT be raised from, or cause a
  rollback of, a canonical PostgreSQL transaction.
- `api.routers.health.readiness` (`/readyz`) reports PostgreSQL readiness
  as the sole hard gate and Qdrant readiness as its own, non-blocking
  signal (`dependencies.semantic_retrieval` in the response body) — a
  PostgreSQL-up/Qdrant-down deployment is "ready" with semantic search
  degraded, never "not ready" outright.
- Projection writes happen *after* a canonical write already succeeded —
  today, synchronously in the same request/script for simplicity (the
  reference `scripts/rebuild_projection.py` path and any future write-time
  projection hook), but never gating the canonical write's own success.
  Pulse's existing transactional-outbox pattern
  (`infrastructure/messaging/outbox`) is the documented mechanism a future
  write-time projection hook should reuse for asynchronous, at-least-once
  projection dispatch, rather than inventing a second one — no second
  job/event mechanism is introduced by this refactor.
- Proven directly: `tests/unit/infrastructure/test_qdrant_projection_store_unavailable.py`
  (an unreachable Qdrant endpoint) and
  `tests/integration/test_evidence_postgres_qdrant_roundtrip.py::test_qdrant_unavailability_never_blocks_or_corrupts_canonical_postgresql_writes`
  (a canonical write/read succeeds independently of a simultaneously
  broken Qdrant store).

## Embedding lifecycle

`ProjectionRecord.embedding_model_id`/`embedding_model_version` travel with
every projection so a future embedding-model change is detectable and
re-embeddable, not silently mixed with stale vectors. Today's only
implementation (`"mock"`, via `HaystackEmbeddingAdapter`) is deterministic
and requires no credentials — adopting a real embedding provider is a
separate, later, controlled change scoped entirely to
`build_text_embedder`/`build_document_embedder`
(`infrastructure/haystack/embedders/embedding_adapter.py`); it does not
require any change to `EmbeddingPort`, `VectorProjectionPort`,
`SemanticRetrievalPort`, or any application/domain code.

## Reindex and rebuild strategy

Collection identity is entirely configuration-driven
(`Settings.qdrant_collection_prefix`/`qdrant_evidence_collection_version`,
resolved by `resolve_collection_name` — the only place a logical
collection role becomes a physical name). Safe reindexing is a
**configuration change, not a runtime code path**: bump
`qdrant_evidence_collection_version`, backfill the new physical collection
via `scripts/rebuild_projection.py` (`make rebuild-projection`), validate
it, then deploy with the new version to cut traffic over. No method on
`QdrantEvidenceProjectionStore` recreates or drops a collection in place —
`rebuild_projection`/`replace_projection` only ever populate the
collection an instance is already configured for.

`scripts/rebuild_projection.py` is the documented, always-safe-to-re-run
recovery path after any Qdrant data loss: it reads every (or one named)
`EvidenceSet` from canonical PostgreSQL, re-resolves text, re-embeds, and
re-projects — proving item 8's guarantee that a total loss of Qdrant is
recoverable from PostgreSQL alone, never a data-loss event.

## Operational ownership

Qdrant runs as its own service in local development
(`docker-compose.yml`'s `qdrant` service, image `qdrant/qdrant:v1.19.1`,
its own named volume and health check) — never embedded in the `pulse-api`
application image or the `.devcontainer` image, matching
`ADR-PULSE-010`'s "headless operation" principle that no auxiliary engine
gets bundled into Pulse's own deployable artifact. Production
orchestration of the Qdrant service itself belongs to
`nabhold/infrastructure`, the same boundary `docker-compose.yml` already
states for PostgreSQL.

## Alternatives considered

- **pgvector (PostgreSQL extension).** Would keep everything in one
  database, but the platform brief specifically directs introducing Qdrant
  as a dedicated vector engine, and a dedicated engine keeps the "PostgreSQL
  = canonical, vector store = derived/rebuildable" boundary explicit and
  mechanically enforceable (a `pgvector` column living in the same table as
  canonical data invites exactly the "is this canonical or projection?"
  ambiguity this ADR exists to avoid) rather than implicit-by-convention.
- **A different vector database (Weaviate, Milvus, pgvector-as-a-service,
  ...).** Rejected on the same grounds `ADR-PULSE-010` rejected LangChain/
  LlamaIndex: the governing decision is keeping *any* vector engine behind
  a port, not a preference between engines. Qdrant was selected because
  the refactor brief names it explicitly, has an official, actively
  maintained Haystack integration (`qdrant-haystack`), and supports a
  genuine embedded/in-process mode that keeps the default test suite
  credential- and server-free.
- **No dedicated vector store — keep the in-memory reference projection.**
  Sufficient for `ADR-PULSE-010`'s one synthetic demonstration corpus, not
  for a real evidence corpus at any meaningful scale; this ADR is exactly
  the "once workload evidence justifies it" trigger `ADR-PULSE-010` named.

## Risks

- **Qdrant SDK/Haystack integration churn.** Mitigated the same way
  `ADR-PULSE-010` mitigates Haystack churn itself: the anti-corruption
  boundary scopes a rewrite to one module
  (`qdrant_projection_store.py`) and its architecture-test enforcement.
- **Mock embeddings do not reflect real semantic similarity.** The
  deterministic hash-based mock embedder proves the *plumbing* (tenant/
  classification filtering, staleness detection, canonical hydration)
  correctly but says nothing about real retrieval quality — a real
  embedding provider integration needs its own evaluation before
  production traffic, mirroring `ADR-PULSE-010`'s "`MockChatGenerator`
  divergence from real providers" risk.
- **Write-time projection is currently synchronous with the caller**
  (`scripts/rebuild_projection.py`, or any future write-time hook) rather
  than dispatched through the outbox. Acceptable for this refactor's scope
  (no such hook exists on the request path yet); a future write-time
  projection trigger MUST reuse the existing outbox pattern rather than
  block a canonical write on Qdrant's availability.

## Upgrade strategy

Before adopting a new `qdrant-client`/`qdrant-haystack` version:

1. Re-run `tests/integration/test_qdrant_evidence_projection_store.py`,
   `tests/integration/test_evidence_postgres_qdrant_roundtrip.py`, and
   `tests/architecture/*` unchanged — a passing suite is the regression
   gate, matching `ADR-PULSE-010`'s upgrade discipline.
2. Re-verify the pinned versions against PyPI's JSON API the same way this
   ADR did, not from memory or a web-search summary.
3. Re-inspect `QdrantDocumentStore`/`QdrantEmbeddingRetriever`'s
   constructor and filter-DSL contract against the new version.
4. Bump `ProjectionRecord.projection_version` only if the upgrade changes
   the actual projection mapping (fields written into `meta`) — a
   dependency bump alone does not require a new version if the mapping is
   provably unchanged.

## Exit strategy

Per the platform brief's "Final Architectural Test": replacing Qdrant
entirely requires rewriting one module
(`infrastructure/haystack/document_stores/qdrant_projection_store.py`) and
`scripts/rebuild_projection.py`'s store construction — nothing else.
`VectorProjectionPort`, `SemanticRetrievalPort`, `EmbeddingPort`,
`ProjectionRecord`, `SemanticCandidate`, `EmbeddingVector`,
`EvidenceRetrievalService`, and every canonical domain concept
(`EvidenceSet`, `Evidence`, tenant context, classification) are defined
without importing `qdrant_client` or `haystack_integrations` anywhere.
Because every projection is rebuildable from canonical PostgreSQL data by
construction (`scripts/rebuild_projection.py`), migrating to a replacement
vector engine is a rebuild against the new engine, not a data-migration
project — `tests/architecture/test_dependency_boundaries.py` is the
standing proof of the isolation this depends on, re-run on every CI build.
