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

## P-CAP-03 implementation

P-CAP-03 is implemented by ADR-PULSE-014.

The canonical evidence-search route now requires an authenticated caller and a
caller-bound Control Plane context. `X-Baobab-Tenant-Id` is not authority for
that route, and the Shared request body no longer exposes
`requester_clearance`.

Because the current canonical IAM/Control Plane contracts do not define higher
classification clearance, the first adapter is intentionally capped at
`Classification.TENANT`. This is a fail-closed boundary, not a permanent
classification model.

Provider support is still not declared; P-CAP-06 remains the first
evidence-backed support-promotion decision.

## P-CAP-04 implementation

ADR-PULSE-015 implements the durable canonical
`intelligence.research-mission.manage` CREATE/GET slice.

Research missions are now persisted in PostgreSQL and retrieved with tenant
isolation in the SQL predicate itself. The former unauthenticated in-memory
scaffold routes are retired so they cannot bypass the P-CAP-03 authentication
and Control Plane context boundary.

The first canonical adapter remains tenant-bound and therefore rejects
GLOBAL/PLATFORM creation. It also rejects CONFIDENTIAL/RESTRICTED mission
creation until a canonical higher-clearance authority exists.

Provider support remains undeclared. P-CAP-05 governs mutation idempotency,
audit and event semantics before any P-CAP-06 support promotion.

## P-CAP-05 implementation

ADR-PULSE-016 governs mutation semantics for the canonical ResearchMission
CREATE operation.

CREATE now requires a valid `Idempotency-Key`. The durable key is scoped by
trusted tenant, authenticated subject, capability and key. Identical retries
return the originally committed ResearchMission; reuse with a different request
fails with `409 IDEMPOTENCY_CONFLICT`.

One PostgreSQL transaction commits the ResearchMission, idempotency record,
mutation-audit provenance and one event-envelope candidate.

The event candidate is deliberately `HELD_UNREGISTERED`. ADR-SHARED-025 still
keeps the Intelligence event context RESERVED with no activated producer event,
so P-CAP-05 adds no publisher claim and no runtime relay permission.

Provider support remains undeclared. P-CAP-06 is the first support-promotion
decision.

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
