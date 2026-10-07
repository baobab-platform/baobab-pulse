# ADR-PULSE-017 — Evidence-Backed PARTIAL Capability Provider Support

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-06  
**Provider:** `baobab-pulse.core`  
**Capabilities:** `intelligence.evidence.search`, `intelligence.research-mission.manage`  
**Depends on:** ADR-SHARED-017, ADR-SHARED-025, ADR-SHARED-029, ADR-PULSE-014, ADR-PULSE-015, ADR-PULSE-016

## Context

ADR-SHARED-029 established the first canonical Intelligence capability tranche and
required Pulse to begin from contract-only `CONTRACTED` intent rather than
claim provider implementation before executable evidence existed.

P-CAP-03 through P-CAP-05 have now created that evidence.

The question for P-CAP-06 is narrow:

> Does baobab-pulse now have enough repository evidence to declare provider
> support for the two canonical Intelligence capabilities, and if so at what
> implementation status?

This ADR does not certify, activate, bind, grant, route or health-check a
provider. Those remain separate EA-09 / Control Plane concerns.

## Decision

Pulse declares one first-party provider:

`baobab-pulse.core`

with `PARTIAL` support for:

1. `intelligence.evidence.search` contract major 1
2. `intelligence.research-mission.manage` contract major 1

The previous `planned_capabilities` CONTRACTED entries are removed because a
canonical capability must not simultaneously appear as planned intent and
provider support.

No capability is declared `IMPLEMENTED` in P-CAP-06.

## Why PARTIAL is now justified

### intelligence.evidence.search

The repository now contains executable evidence for the canonical path:

```text
Bearer caller
    |
    v
WorkloadAuthenticatorPort
    |
    v
caller-bound ContextAuthorityPort
    |
    v
TrustedPlatformContext
    |
    v
EvidenceSearchCapabilityService
    |
    +--> tenant context binding
    |
    +--> Qdrant semantic projection
    |
    v
PostgreSQL canonical hydration
    |
    +--> stale/orphan filtering
    +--> classification enforcement
    |
    v
Shared-v1 response
```

Evidence includes:

- exact Shared-v1 request/response contract tests;
- authenticated canonical HTTP route;
- malicious tenant-header rejection;
- Control Plane context as the only tenant authority;
- fail-closed behavior when IAM/Control Plane authority is unavailable;
- canonical PostgreSQL EvidenceSet hydration;
- Qdrant treated as rebuildable semantic projection rather than truth;
- live PostgreSQL + Qdrant integration proof.

This is substantially beyond contract-only intent.

### intelligence.research-mission.manage

The repository now contains executable evidence for the canonical path:

```text
Bearer caller
    |
    v
caller-bound trusted context
    |
    v
CREATE or GET
    |
    +--> GET: structurally tenant-scoped PostgreSQL read
    |
    +--> CREATE:
            Idempotency-Key
                |
                v
            atomic transaction
              ├─ ResearchMission
              ├─ idempotency record
              ├─ mutation audit
              └─ HELD event candidate
```

Evidence includes:

- exact Shared-v1 CREATE/GET contract tests;
- authenticated/context-bound canonical route;
- durable PostgreSQL ResearchMission persistence;
- cross-tenant invisibility;
- idempotent replay;
- semantic key-conflict protection;
- durable mutation audit provenance;
- correlation propagation;
- concurrent duplicate convergence;
- one mission + one idempotency row + one audit row + one held outbox candidate.

This is also substantially beyond contract-only intent.

## Why IMPLEMENTED is still an overclaim

The repository still has explicit production-readiness gaps.

### 1. No production composition root for canonical capabilities

The module-level ASGI app is currently:

```python
app = create_app()
```

and therefore starts with:

```text
app.state.capability_runtime = None
```

unless an external caller explicitly injects a `CapabilityApiRuntime`.

The canonical routes correctly fail closed with 503 when that runtime is absent,
but this also means the repository has not yet demonstrated the actual production
composition root required to serve the capabilities.

### 2. Authentication is still only a provider-neutral port

`WorkloadAuthenticatorPort` defines the correct provider-neutral boundary, but
P-CAP-06 does not yet include the concrete production adapter that validates the
canonical IAM workload-token contract in the deployed Pulse runtime.

This is deliberate: Pulse must remain neutral to whether IAM internally uses
Hydra, Kratos, Keycloak federation, or another provider.

### 3. Control Plane context authority is still only a port

`ContextAuthorityPort` correctly requires caller-bound context redemption, but
the production HTTP/gRPC adapter and deployment configuration are not yet wired
into the module-level runtime.

### 4. Evidence-search clearance ceiling is deliberately conservative

The Shared capability classification is `TENANT_CONFIDENTIAL`, while the
current canonical authority contracts do not yet provide Pulse with an explicit
higher-classification clearance grant.

Pulse therefore caps canonical search at:

`Classification.TENANT`

and refuses to infer CONFIDENTIAL/RESTRICTED authority from scopes, headers,
membership, model instructions or provider-specific claims.

This is correct fail-closed behavior, but it means the provider does not yet
exercise the entire future classification surface implied by the canonical
capability definition.

### 5. Intelligence producer-event activation remains absent

The ResearchMission CREATE transaction persists:

`com.baobab-platform.intelligence.research-mission.created.v1`

only as:

`publication_status = HELD_UNREGISTERED`

because ADR-SHARED-025 keeps the Intelligence producer event context RESERVED.

P-CAP-06 does not turn that candidate into an activated Shared event.

### 6. No EA-09 certification or Control Plane activation

PARTIAL support is repository implementation evidence only.

It is not proof of:

- EA-09 certification;
- EngineInstance registration;
- provider activation;
- CapabilityBinding;
- tenant grants;
- health;
- routing;
- production traffic eligibility.

## Provider declaration

The declaration moves from:

```text
planned_capabilities
  ├─ intelligence.evidence.search       CONTRACTED
  └─ intelligence.research-mission.manage CONTRACTED
```

to:

```text
providers
  └─ baobab-pulse.core
       ├─ intelligence.evidence.search
       │    status = PARTIAL
       │    contract_versions = [1]
       │
       └─ intelligence.research-mission.manage
            status = PARTIAL
            contract_versions = [1]
```

The provider is:

- `provider_type: BAOBAB_ENGINE`
- `implementation_key: core`
- `simulated: false`
- `production_permitted: true`

`production_permitted: true` means only that this implementation family may
eventually be promoted for production use. It does not mean the current PARTIAL
support is production-ready or active.

## Evidence requirements

Each support claim must include repository-local implementation evidence.

At minimum:

### Evidence search

| Evidence type | Requirement |
|---|---|
| source | authenticated/context-bound application adapter |
| source | canonical PostgreSQL hydration path |
| source | Qdrant semantic projection adapter |
| contract-test | exact Shared-v1 request/response proof |
| test | HTTP authority/fail-closed proof |
| integration-test | live PostgreSQL + Qdrant roundtrip |

### ResearchMission manage

| Evidence type | Requirement |
|---|---|
| source | canonical application adapter |
| source | durable tenant-scoped repository |
| source | atomic mutation/idempotency/audit store |
| source | migration constraints |
| contract-test | exact Shared-v1 CREATE/GET proof |
| test | HTTP idempotency/access proof |
| integration-test | durable PostgreSQL roundtrip |
| integration-test | concurrent mutation-governance proof |

Shared's declaration validator must resolve every evidence path.

## Promotion ceiling test

P-CAP-06 adds a repository test that makes the current ceiling explicit:

- both canonical capabilities must be declared `PARTIAL`;
- no matching `planned_capabilities` entry may remain;
- neither capability may be `IMPLEMENTED`;
- the module-level canonical runtime must remain unconfigured until the
  production composition root is deliberately introduced.

The test is intentionally expected to change in P-CAP-07 when the readiness
decision is revisited.

## Relationship to future work

```text
P-CAP-06
PARTIAL support
     |
     v
P-CAP-07
full provider-readiness decision
     |
     +--> production IAM adapter
     +--> production CP context adapter
     +--> runtime composition root
     +--> classification-authority decision
     +--> event-publication decision if justified
     |
     v
IMPLEMENTED?   (only if evidence supports it)
     |
     v
P-CAP-08
EA-09 certification + CP registration/activation
```

P-CAP-07 must make a fresh evidence-based decision. It must not assume that
PARTIAL automatically promotes to IMPLEMENTED.

## Consequences

### Positive

- the provider declaration now matches executable repository reality;
- Shared canonical vocabulary remains authoritative;
- provider support is traceable to exact implementation evidence;
- PARTIAL prevents premature registration because Shared registration generation
  includes only IMPLEMENTED support;
- production-readiness gaps remain visible rather than hidden behind a binary
  "implemented" label.

### Negative

- Control Plane cannot yet generate/register these capabilities as implemented
  provider support;
- canonical routes remain unavailable in the default ASGI composition;
- higher-classification evidence retrieval remains intentionally unavailable;
- ResearchMission event candidates remain non-publishable.

These limitations are accepted and are the reason PARTIAL is the correct
P-CAP-06 state.
