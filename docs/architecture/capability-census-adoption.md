# Pulse capability census adoption

**Programme:** P-CAP-02  
**Authority:** ADR-SHARED-017, ADR-SHARED-025, ADR-SHARED-029  
**Pinned Shared revision:** `2d14087727682d454f7140ba65aa97625454991b`

Pulse adopts the first canonical `intelligence` capability tranche as
**CONTRACTED planned capabilities only**:

```text
intelligence.evidence.search
intelligence.research-mission.manage
```

## What this means

```text
Shared contract exists
        │
        ▼
Pulse intends to implement exact contract
        │
        ▼
NO provider support claim yet
```

The declaration in `.baobab/capability-provider.yaml` contains no
`providers[].support` entry.

That is deliberate.

## Evidence-search gap

The repository already has:

- `POST /evidence/search`;
- `EvidenceRetrievalService`;
- a semantic retrieval port;
- PostgreSQL canonical EvidenceSet hydration;
- Qdrant as a rebuildable projection;
- stale/orphan projection checks.

However the current HTTP scaffold still derives tenant context from
`X-Baobab-Tenant-Id` and accepts caller-selected `requester_clearance`.

The canonical Shared contract does not permit those fields to establish
authority. P-CAP-03 must bind evidence search to authenticated IAM workload/user
identity plus trusted Control Plane context before provider support can be
promoted.

## Research-mission gap

The repository already has:

- a first-class ResearchMission aggregate and lifecycle;
- `POST /research-missions`;
- `GET /research-missions/{id}`;
- provider-neutral local request/response models;
- a ResearchMissionService behind PipelinePort.

But the repository itself describes the route as a minimal verification slice,
and the mission repository is in-memory.

P-CAP-04 must implement the canonical contract against durable mission
persistence and trusted context before provider support can be promoted.

## What is not a capability

The census intentionally does not declare:

- RTD-09 Regulations/Trade Docs fact projection;
- Haystack pipeline execution;
- Qdrant vector projection;
- model/embedding execution;
- one capability per Signal, Trend, Risk, Opportunity, Forecast or Recommendation
  class.

Those are either integration plumbing, implementation details or domain concepts
without a proven external contract.

## Promotion sequence

```text
P-CAP-02  CONTRACTED declaration
    ↓
P-CAP-03  canonical/authenticated evidence.search adapter
    ↓
P-CAP-04  durable canonical research-mission adapter
    ↓
P-CAP-05  idempotency/audit/event semantics
    ↓
P-CAP-06  PARTIAL provider-support decision
    ↓
P-CAP-07  IMPLEMENTED/readiness decision
    ↓
P-CAP-08  EA-09 certification + Control Plane activation
```
