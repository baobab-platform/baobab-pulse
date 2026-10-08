# ADR-PULSE-015 — Durable Context-Bound ResearchMission Capability

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-04  
**Capability:** `intelligence.research-mission.manage`  
**Depends on:** ADR-PULSE-003, ADR-PULSE-014, ADR-SHARED-029

## Decision

Pulse implements the canonical Shared v1
`intelligence.research-mission.manage` capability as a durable,
authenticated, caller-bound PostgreSQL service.

The canonical HTTP surface is:

```text
POST /research-missions/manage
```

with a discriminated Shared request:

```text
CREATE
  title
  research_question
  tenant_scope
  classification
  confidence_requirement

GET
  research_mission_id
```

Tenant identity is deliberately absent from both request forms.

## Authority flow

```text
Bearer-authenticated caller
        |
        v
X-Baobab-Context-Id
        |
        v
Control Plane caller/context validation
        |
        v
trusted tenant_id
        |
        +------ CREATE ------> ResearchMission aggregate
        |                        |
        |                        v
        |                  PostgreSQL durable row
        |
        +------ GET --------> SELECT ...
                              WHERE id = ?
                                AND tenant_id = trusted tenant
```

The database read is tenant-scoped before hydration. Pulse never loads a
foreign tenant's ResearchMission and filters it after deserialisation.

## Durability

P-CAP-04 introduces:

```text
intelligence.research_missions
```

with:

- canonical mission id;
- trusted tenant id;
- status;
- classification;
- full JSONB aggregate payload;
- created/updated timestamps.

The JSONB payload is the canonical aggregate representation. The extracted
tenant/status/classification columns exist for structural isolation and
operational inspection; they do not replace the domain model.

## Retirement of the scaffold bypass

The earlier routes:

```text
POST /research-missions
GET  /research-missions/{id}
```

were an in-memory architectural verification slice.

They are removed from the public router in P-CAP-04.

Keeping them while adding durable canonical persistence would create a second,
unauthenticated route around P-CAP-03's trusted context boundary. That is
rejected.

The only canonical management surface in this increment is
`POST /research-missions/manage`.

## Tenant scope

This first canonical implementation is invoked through a tenant-bound Control
Plane context.

Therefore P-CAP-04 accepts:

```text
TENANT
CONTEXT
PRIVATE
```

mission scope and rejects creation of:

```text
GLOBAL
PLATFORM
```

from a tenant invocation.

A future platform-level administration/research flow may introduce explicit
authority for broader scopes. This capability does not infer it.

## Classification

P-CAP-03 established that the current canonical workload-token and
PlatformContextValidation contracts do not supply a higher classification
clearance.

P-CAP-04 consequently allows mission creation only through:

```text
PUBLIC
BAOBAB_INTERNAL
TENANT
```

and rejects:

```text
CONFIDENTIAL
RESTRICTED
```

until an explicit higher-clearance authority contract exists.

The request's `classification` is the classification assigned to the new
Pulse object; it is not itself proof that the caller is cleared to use that
classification.

## GET non-disclosure

A mission that does not exist and a mission belonging to another tenant both
result in:

```text
404 RESEARCH_MISSION_NOT_FOUND
```

The capability does not expose cross-tenant existence.

## Lifecycle boundary

P-CAP-04 contracts only the existing first-tranche Shared acts:

```text
CREATE
GET
```

It does not add:

- lifecycle transition commands;
- pipeline-run commands;
- publication;
- cancellation;
- idempotency semantics;
- canonical intelligence events.

Those mutation-governance concerns belong to P-CAP-05 and later increments.

## Provider support

The provider declaration remains:

```text
planned_capabilities
  intelligence.research-mission.manage = CONTRACTED
```

P-CAP-04 creates strong implementation evidence but does not yet add
`providers[].support`.

Promotion remains P-CAP-06/P-CAP-07 after mutation governance and the planned
readiness review.

## Verification

P-CAP-04 is accepted only when tests prove:

1. exact Shared CREATE request shape;
2. exact Shared GET request shape;
3. exact Shared response including `confidence_requirement`;
4. no caller-supplied `tenant_id`;
5. tenant header cannot override CP authority;
6. cross-tenant GET returns 404;
7. GLOBAL/PLATFORM creation fails closed;
8. unsupported higher classification fails closed;
9. legacy unauthenticated scaffold route is absent;
10. a real PostgreSQL write survives and can be read back under the same tenant;
11. the same persisted id is invisible to another tenant.
