# Baobab Pulse — Architecture Overview

This document orients a reader across the repository's actual package
layout, dependency direction, and deployment shape. It is a map, not a
decision record — decisions live in `docs/adr/`.

## What Pulse is (and is not)

See the root `README.md` and `docs/adr/Baobab Pulse Intelligence Engine.md`
(`ARCH-PULSE-001`) for the full statement. In one line: Pulse turns
heterogeneous internal and external evidence into traceable, contextualised,
time-aware intelligence, without becoming the system of record for the
operational domains that evidence describes.

## Package layout and dependency direction

```mermaid
graph TD
    subgraph "src/baobab_pulse"
        domain["domain/<br/>(no external deps)"]
        application["application/<br/>(ports + services)"]
        contracts["contracts/<br/>(wire shapes)"]
        infrastructure["infrastructure/<br/>(adapters)"]
        haystack_acl["infrastructure/haystack/<br/>(the ONLY package<br/>that imports haystack)"]
        api["api/ (FastAPI)"]
        ingestion["ingestion/<br/>(SourceAdapter)"]
        tenancy["tenancy/"]
        security["security/"]
        configuration["configuration/"]
    end

    api --> application
    api --> contracts
    ingestion --> domain
    application --> domain
    application --> tenancy
    infrastructure --> application
    haystack_acl --> application
    haystack_acl --> domain
    contracts --> domain
    api --> infrastructure
    api --> haystack_acl

    domain -.->|"forbidden"| haystack_acl
    application -.->|"forbidden"| haystack_acl
    contracts -.->|"forbidden"| haystack_acl
```

`tests/architecture/test_dependency_boundaries.py` enforces the solid
arrows' absence in the wrong direction mechanically (AST import scanning),
not by convention alone.

## The Haystack anti-corruption boundary

```mermaid
graph LR
    RM["ResearchMission<br/>(domain)"] --> Service["ResearchMissionService<br/>(application)"]
    Service --> Port["PipelinePort<br/>(application.ports, a Protocol)"]
    Port --> Adapter["HaystackPipelineAdapter<br/>(infrastructure.haystack)"]
    Adapter --> Pipeline["haystack.Pipeline<br/>(EvidenceContextComponent -&gt;<br/>ChatGenerator -&gt; ClaimGroundingComponent)"]
    Pipeline --> Adapter
    Adapter --> Candidate["ClaimCandidate<br/>(plain pydantic DTO,<br/>status=CANDIDATE)"]
    Candidate --> Validation["Baobab Validation Boundary<br/>(ResearchMissionService._ground_candidate)"]
    Validation --> Claim["domain.Claim<br/>(status=EVIDENCED or dropped)"]
```

Every arrow crossing from `Adapter` back out is a plain Python/pydantic
type — never a `haystack.*` class. See
`docs/adr/ADR-PULSE-010 — Embedding Deepset Haystack as Pulse's Headless AI Orchestration Engine.md`
for the full reasoning, and
`tests/integration/test_haystack_reference_pipeline.py` for this exact flow
executing deterministically.

## Qdrant semantic-retrieval projection

PostgreSQL remains canonical; Qdrant is a rebuildable projection, never the
other way around. The same anti-corruption discipline as the Haystack
boundary above applies — `qdrant_client`/`haystack_integrations` types stay
inside one adapter module:

```mermaid
graph TD
    PG[("PostgreSQL<br/>(canonical: EvidenceSet, Evidence)")]
    Rebuild["scripts/rebuild_projection.py<br/>(make rebuild-projection)"]
    EmbedPort["EmbeddingPort<br/>(application.ports, a Protocol)"]
    VecPort["VectorProjectionPort<br/>(application.ports, a Protocol)"]
    Adapter["QdrantEvidenceProjectionStore<br/>(infrastructure.haystack.document_stores —<br/>the ONLY module that imports qdrant_client)"]
    Qdrant[("Qdrant<br/>(derived projection, versioned collection)")]

    PG -->|"resolve text"| Rebuild
    Rebuild --> EmbedPort
    Rebuild --> VecPort
    VecPort --> Adapter
    EmbedPort --> Adapter
    Adapter --> Qdrant

    Query["EvidenceRetrievalService.search()<br/>(application)"] -->|"1. require_tenant_context()<br/>fail closed if unbound"| Query
    Query -->|"2. SemanticRetrievalPort.retrieve_evidence()"| SemPort["SemanticRetrievalPort<br/>(application.ports, a Protocol)"]
    SemPort --> Adapter
    Adapter -->|"tenant + classification filter,<br/>built BEFORE the query is issued"| Qdrant
    Qdrant -->|"SemanticCandidate<br/>(canonical_object_id, canonical_version, score)"| Query
    Query -->|"3. compare canonical_version<br/>against PostgreSQL's current version"| PG
    Query -->|"4. hydrate_for_pipeline():<br/>text read back from PostgreSQL,<br/>never from Qdrant's cached payload"| PG
```

A missing tenant context, a stale projection (`canonical_version` behind
PostgreSQL's current version), or an unreachable Qdrant never produce an
unrestricted/unverified result — they fail closed, flag staleness, or
degrade to a typed, retryable error (`SemanticRetrievalUnavailable`/
`VectorStoreUnavailable`) respectively. See
`docs/adr/ADR-PULSE-011 — Qdrant Vector Retrieval and Semantic Projection Architecture.md`
for the full reasoning, and
`tests/integration/test_qdrant_evidence_projection_store.py` /
`tests/integration/test_evidence_postgres_qdrant_roundtrip.py` for this flow
executing against real (embedded/live) Qdrant and PostgreSQL.

## Deployment topology

```mermaid
graph TD
    subgraph "pulse-api (this repo's Dockerfile)"
        API["FastAPI app<br/>(headless HTTP boundary)"]
    end
    subgraph "pulse-worker (future — item 67; not yet built)"
        Worker["Async job execution<br/>(ingestion, analysis, pipeline runs)"]
    end
    subgraph "pulse-scheduler (future — item 69; not yet built)"
        Scheduler["Acquisition scheduling"]
    end

    API --> PG[("PostgreSQL 17<br/>(canonical)")]
    API --> Qdrant[("Qdrant<br/>(derived projection —<br/>own service, never embedded<br/>in the pulse-api image)")]
    API --> OS[("Object Storage<br/>(raw evidence)")]
    API --> Queue[("Job Queue<br/>(not yet selected)")]
    Worker --> PG
    Worker --> Qdrant
    Worker --> OS
    Worker --> Haystack["Haystack Engine<br/>(models, tools, retrieval)"]
    Scheduler --> Queue
```

Only `pulse-api` exists as a runnable deployment role today (this
repository's `Dockerfile`/`docker-compose.yml`, which also runs PostgreSQL
and Qdrant as separate local-development services). `pulse-worker` and
`pulse-scheduler` are reserved roles (item 67-69) — introduced once there is
a real asynchronous workload to run, not speculatively.

## Data flow (the canonical pipeline)

```mermaid
graph LR
    A[ACQUIRE] --> B[PRESERVE] --> C[NORMALISE] --> D[VALIDATE] --> E[ENRICH]
    E --> F[RESOLVE] --> G[CORRELATE] --> H[DERIVE] --> I[ANALYSE]
    I --> J[SCORE] --> K[EXPLAIN] --> L[PUBLISH] --> M[OBSERVE OUTCOME] --> N[LEARN]
```

This scaffold implements a thin, verifiable slice of this chain (Acquire
via `ReferenceSourceAdapter`, Normalise via `ingestion.pipelines.normalisation`,
and Analyse/Explain via the reference Haystack research pipeline) — the
full chain is not built out (item 113: no premature business code).

## Research / RAG flow

See `docs/adr/ADR-PULSE-010 — Embedding Deepset Haystack as Pulse's Headless AI Orchestration Engine.md`
§"RAG over governed evidence" for the flow diagram and why it is not naive
vector-search RAG.

## Agent/tool security

See `docs/security/agent-and-tool-security.md`.

## API framework decision

See `docs/architecture/api-framework-decision.md`.
