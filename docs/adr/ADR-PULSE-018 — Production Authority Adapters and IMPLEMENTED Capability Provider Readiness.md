# ADR-PULSE-018 — Production Authority Adapters and IMPLEMENTED Capability Provider Readiness

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-07  
**Provider:** `baobab-pulse.core`  
**Capabilities:** `intelligence.evidence.search@1`, `intelligence.research-mission.manage@1`  
**Depends on:** ADR-SHARED-017, ADR-SHARED-029, ADR-SHARED-030, ADR-SHARED-031, ADR-PULSE-014, ADR-PULSE-015, ADR-PULSE-016, ADR-PULSE-017

## Context

P-CAP-06 deliberately stopped at `PARTIAL`. Pulse already had canonical routes,
durable PostgreSQL state, caller-bound application ports, semantic retrieval,
canonical evidence hydration, ResearchMission idempotency and mutation audit,
but it still lacked a production-composed trust path.

ADR-SHARED-031 now defines the exact promotion conditions for P-CAP-07.

The repository may claim `IMPLEMENTED` only when the trust path is executable
without relying on test fakes or a caller-selected tenant/classification value.

## Decision

Pulse promotes both first-census Intelligence capabilities from `PARTIAL` to
`IMPLEMENTED`.

This promotion is a **repository implementation statement only**. It does not
certify, activate, bind, grant, health-check or route the provider. Those remain
P-CAP-08 / EA-09 and Control Plane responsibilities.

The production trust path is:

```text
subject workload
  |
  | signed access token
  | aud = baobab-pulse
  v
+---------------------------+
| OIDC/JWKS verifier        |
| - signature               |
| - issuer                  |
| - audience                |
| - subject / jti           |
| - iat / exp / lifetime    |
| - actor_type=workload     |
+-------------+-------------+
              |
              | exact operation scope
              v
+---------------------------+
| Pulse capability service  |
+-------------+-------------+
              |
              | actual subject token
              | (POST body only)
              v
+---------------------------+       client_credentials
| CP context adapter        |<------------------------------+
+-------------+-------------+                               |
              |                                             |
              v                                             |
+---------------------------+                     +---------+----------+
| Baobab Control Plane      |                     | Pulse validator    |
| /platform-context/validate|                     | workload identity  |
+-------------+-------------+                     | context:validate   |
              |                                   +--------------------+
              | trusted tenant/context
              v
       capability execution
```

## 1. Resource-server authentication

`OidcJwksWorkloadAuthenticator` is the concrete production
`WorkloadAuthenticatorPort` adapter.

It is standards-based and provider-neutral. Its configuration is expressed as
OIDC issuer/JWKS/audience/algorithm values rather than Keycloak-, Hydra- or
Kratos-specific objects.

A token is rejected unless Pulse can establish:

| Property | Requirement |
|---|---|
| signature | verified by a configured JWKS signing key |
| issuer | exact configured issuer |
| audience | contains `baobab-pulse` |
| subject | non-empty |
| token identifier | non-empty `jti` |
| issued-at | integer and not unreasonably in the future |
| expiry | verified |
| lifetime | positive and no longer than configured maximum |
| actor | `actor_type=workload` |
| scopes | parsed from the verified token, never request fields |

JWKS connection failures are distinguished from invalid-token failures so the
API can return retryable authority-unavailable semantics without accepting an
unverified caller.

## 2. Exact operation authority

Pulse defines no generic “Intelligence access” shortcut.

The exact operation scopes are:

| Capability | Required scope |
|---|---|
| `intelligence.evidence.search` | `intelligence:evidence:search` |
| `intelligence.research-mission.manage` | `intelligence:research-mission:manage` |

The operation scope is enforced before Control Plane context redemption.

`intelligence:restricted` is supplemental classification authority only. It
cannot invoke either capability on its own.

## 3. Caller-bound Control Plane context validation

`HttpControlPlaneContextAuthority` is the concrete production
`ContextAuthorityPort` adapter.

Pulse authenticates to the Control Plane independently as
`baobab-pulse-workload` using `client_credentials` and
`context:validate`.

The validation request is exactly:

```json
{
  "context_id": "<uuid>",
  "subject_token": "<actual caller token>"
}
```

The subject token:

- is never accepted from a second caller-selected field;
- is never copied into tenant context;
- is never placed in an error message;
- is never logged, persisted, traced or audited by this adapter;
- is transmitted only to the canonical CP validation operation.

The Pulse validator token is cached only in process memory and refreshed before
expiry.

HTTP failure mapping is fail closed:

| CP result | Pulse authority result |
|---|---|
| 401 | context authentication failure |
| 403 | context access denied |
| 404 | context unavailable/not-owned/expired |
| 503 | authority unavailable |
| other/network/invalid response | authority unavailable |

Only CP-returned `tenant_id`, `context_id`, `organisation_id` and
`market_id` are admitted as trusted execution facts.

## 4. Classification authority

P-CAP-07 adopts ADR-SHARED-031's explicit Intelligence ceiling:

```text
no exact operation scope
    -> no invocation

exact operation scope
    -> CONFIDENTIAL maximum

exact operation scope + intelligence:restricted
    -> RESTRICTED maximum
```

Tenant authority remains entirely separate and always comes from the validated
PlatformContext.

### Evidence search

The derived classification is passed into the semantic retrieval query. Qdrant
must filter by tenant/classification before returning candidates, and every
candidate is then checked against canonical PostgreSQL EvidenceSet state.

Qdrant remains a rebuildable projection.

### ResearchMission management

CREATE rejects a classification above the caller's effective ceiling.

GET performs a structural tenant-scoped read and then applies classification
filtering. A mission above the caller's ceiling is returned as the same
non-disclosing `RESEARCH_MISSION_NOT_FOUND` result as an absent/foreign-tenant
mission.

## 5. Production composition root

The default ASGI module now invokes:

```python
app = create_app(build_capability_runtime())
```

Behavior is environment-sensitive but fail closed:

| Environment/configuration | Result |
|---|---|
| non-production, no authority config | canonical runtime omitted; routes remain 503 |
| any environment, partially configured authority | startup fails |
| production, missing authority config | startup fails |
| fully configured | concrete IAM + CP adapters are composed |

This means a production process can no longer start while silently serving a
`None` capability runtime.

Database reachability remains a readiness concern rather than an authority
configuration concern; existing graceful readiness semantics are unchanged.

## 6. Provider declaration

`baobab-pulse.core` now declares:

```text
provider: baobab-pulse.core
simulated: false
production_permitted: true
invocation:
  service_reference: service://baobab-pulse/capabilities
  protocol: http

support:
  intelligence.evidence.search@1
    implementation_status: IMPLEMENTED

  intelligence.research-mission.manage@1
    implementation_status: IMPLEMENTED
```

The logical `service://` reference is not a hostname, deployment record,
EngineInstance or routing decision.

## 7. Evidence required for the claim

Each capability carries repository-local evidence for:

- production OIDC/JWKS authentication;
- production CP context validation;
- exact route scope and classification enforcement;
- canonical Shared v1 contract tests;
- capability HTTP behavior;
- durable PostgreSQL state where applicable;
- live PostgreSQL/Qdrant integration for evidence search;
- concurrent durable mutation-governance integration for ResearchMission.

P-CAP-07 adds direct adapter tests rather than treating fake API adapters as
sufficient production evidence.

## 8. ResearchMission event remains held

The local candidate

`com.baobab-platform.intelligence.research-mission.created.v1`

remains `HELD_UNREGISTERED`.

P-CAP-07 does not activate the reserved Intelligence producer event context.
The capability contract does not require publication, so this does not block
`IMPLEMENTED`.

## 9. Non-goals

P-CAP-07 does not:

- certify the provider under EA-09;
- create or activate a CapabilityProvider record;
- activate ProviderCapabilitySupport;
- create an EngineInstance;
- create a CapabilityBinding or CapabilityGrant;
- assign Intelligence scopes to consumers;
- assert deployment health;
- make the provider resolvable;
- publish the held ResearchMission event;
- make IAM provider implementation details canonical.

Those belong to P-CAP-08 or later consumer-specific integration increments.

## 10. Invariants

**PULSE-READY-001** — Only verified workload tokens for `aud=baobab-pulse`
enter canonical capability execution.

**PULSE-READY-002** — Each route requires its exact Intelligence operation
scope before context redemption.

**PULSE-READY-003** — `intelligence:restricted` never grants an operation.

**PULSE-READY-004** — Tenant authority comes only from caller-bound Control
Plane validation.

**PULSE-READY-005** — Base operation authority is capped at CONFIDENTIAL.

**PULSE-READY-006** — RESTRICTED requires the exact operation scope plus
`intelligence:restricted`.

**PULSE-READY-007** — ResearchMission reads above clearance are
non-disclosing.

**PULSE-READY-008** — Production authority configuration is complete or startup
fails closed.

**PULSE-READY-009** — Subject-token evidence is never logged, persisted,
traced or echoed in errors.

**PULSE-READY-010** — Both first-census capabilities advance together to
`IMPLEMENTED`.

**PULSE-READY-011** — `IMPLEMENTED` does not imply certification,
activation, binding, entitlement, health or routing.

**PULSE-READY-012** — The held Intelligence event remains unpublished.

## Consequences

### Positive

- repository readiness now matches the Shared P-CAP-07 contract;
- canonical routes have real production trust adapters;
- IAM and Control Plane remain the identity/context authorities;
- Pulse no longer relies on caller-selected classification;
- provider support can proceed to P-CAP-08 certification without overstating
  runtime activation.

### Accepted constraints

- consumer workloads still need separate reviewed grants of Intelligence scopes;
- production deployment still needs secrets/endpoints supplied by the
  infrastructure boundary;
- event publication remains a separate governance decision;
- `IMPLEMENTED` alone cannot make the provider routable.

## Final decision

> `baobab-pulse.core` has sufficient repository evidence to declare
> `intelligence.evidence.search@1` and
> `intelligence.research-mission.manage@1` IMPLEMENTED. P-CAP-07 ends at
> repository readiness. Certification and runtime activation remain P-CAP-08.
