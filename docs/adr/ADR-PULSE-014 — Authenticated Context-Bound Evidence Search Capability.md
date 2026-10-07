# ADR-PULSE-014 — Authenticated Context-Bound Evidence Search Capability

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-03  
**Capability:** `intelligence.evidence.search`  
**Depends on:** ADR-PULSE-001, ADR-PULSE-011, ADR-PULSE-013, ADR-SHARED-021, ADR-SHARED-029, Shared context-authority-for-workloads design

## Decision

Pulse implements the canonical Shared v1 `intelligence.evidence.search`
adapter as an authenticated, caller-bound capability route.

The JSON request remains exactly:

```text
query_text
evidence_set_id?
top_k?
```

It does not accept tenant identity, principal identity, capability authority,
or classification clearance as caller-selected business fields.

## Trust flow

```text
Caller
  |
  | Authorization: Bearer <caller token>
  | X-Baobab-Context-Id: <opaque context UUID>
  | body: { query_text, evidence_set_id?, top_k? }
  v
Pulse capability adapter
  |
  +--> WorkloadAuthenticatorPort
  |       verify actual caller
  |
  +--> ContextAuthorityPort
  |       redeem context_id against that caller
  |       via Control Plane authority
  |       -> trusted tenant_id
  |
  +--> bind_tenant_context(trusted tenant)
  |
  +--> EvidenceRetrievalService
          |
          +--> pre-query tenant/classification filter
          |       |
          |       v
          |     Qdrant projection
          |
          +--> PostgreSQL canonical-version hydration
          |
          v
      canonical evidence candidate identities
```

The historical `X-Baobab-Tenant-Id` header is not authority for this route.
The tenancy middleware deliberately does not bind it for
`/evidence/search`.

## Authentication boundary

Pulse owns no identity provider semantics.

`WorkloadAuthenticatorPort` is provider-neutral and receives the bearer token
that reached the Pulse resource server. A runtime implementation must verify
the appropriate issuer, expiry, audience and actor semantics before returning
an `AuthenticatedCaller`.

The verified inbound token is retained only as subject evidence so a Control
Plane context validator can independently bind the context to the actual
caller. It must not be logged or persisted.

Provider selection and production credential wiring remain deployment/runtime
concerns; this ADR does not make Keycloak, Ory, JWT serialization or token
introspection part of the intelligence capability contract.

## Context authority

The canonical route requires `X-Baobab-Context-Id`.

This header is an opaque selector, not tenant authority by itself.

A `ContextAuthorityPort` must redeem it under the Shared
context-authority-for-workloads invariants:

```text
authenticated caller canonical principal
            ==
stored Context.PrincipalID
```

Unknown, expired, unbounded, or another principal's context fails closed.

A caller-supplied tenant header cannot replace this operation.

## Classification policy

The Shared `evidenceSearchRequest` says classification clearance is not a
request field.

At P-CAP-03 time, neither the canonical workload-token claims nor
`PlatformContextValidation` defines a higher classification-clearance fact.

Pulse therefore applies this conservative rule:

```text
validated tenant context
        -> maximum canonical search clearance = TENANT
```

This means the route may structurally retrieve only classifications permitted
up to `TENANT`.

It must not infer or manufacture:

```text
CONFIDENTIAL
RESTRICTED
```

clearance from token scopes, tenant membership, headers, model instructions or
application convention.

If the platform later introduces an explicit classification-authority
contract, that authority can be consumed behind the application boundary in a
separate governed increment.

## Structural retrieval rule

Qdrant remains a rebuildable semantic projection and PostgreSQL remains
canonical EvidenceSet authority.

Before Qdrant receives a semantic query, the adapter chain constrains:

```text
tenant_id == Control-Plane-validated tenant
classification IN allowed(TENANT)
evidence_set_id == requested set, when present
```

The query is never broad and then post-filtered.

The Qdrant score remains retrieval relevance only; it is not intelligence
confidence, evidence strength, regulatory sufficiency, or a decision.

## Failure semantics

| Condition | HTTP |
|---|---:|
| malformed/missing capability metadata | 400 |
| caller authentication failure | 401 |
| caller/context access denied | 403 |
| context unavailable to this principal | 404 |
| IAM/Control Plane authority unavailable | 503 |
| capability runtime not configured | 503 |
| semantic projection unavailable | 503 |

Errors continue to use Shared-compatible RFC 9457 ProblemDetails.

## Provider-support status

P-CAP-03 does **not** promote the provider declaration.

```text
canonical contract          yes
authenticated route         yes
caller-bound context        yes
tenant structural filter    yes
provider support PARTIAL    no
provider support IMPLEMENTED no
EA-09 certification         no
CP activation               no
```

Provider promotion remains P-CAP-06/P-CAP-07 after the other required
implementation evidence exists.

## Consequences

1. The legacy tenant header cannot authorize canonical evidence search.
2. Callers cannot request their own classification clearance.
3. The route fails closed when the capability runtime or platform authority is absent.
4. Higher-classification evidence is intentionally inaccessible through this first canonical adapter.
5. ResearchMission persistence is untouched; that is P-CAP-04.
