# ADR-PULSE-019 — EA-09 Certification Handoff and P-CAP-08 Activation Boundary

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-08  
**Provider:** `baobab-pulse.core`  
**Capabilities:** `intelligence.evidence.search@1`, `intelligence.research-mission.manage@1`  
**Depends on:** ADR-PULSE-018, ADR-SHARED-032, ADR-BCP-025

## Context

P-CAP-07 established that the first two Pulse capability implementations are
`IMPLEMENTED` and production-permitted at the repository boundary. It
deliberately did not certify or activate the provider.

Shared ADR-SHARED-032 now supplies the missing EA-09 certification contract and
admits both canonical Intelligence capabilities to lifecycle `ACTIVE` while
retaining `EXPERIMENTAL` maturity.

These are different statements:

```text
canonical capability ACTIVE
        !=
Pulse implementation IMPLEMENTED
        !=
provider/capability/release CERTIFIED
        !=
CapabilityProvider ACTIVE
        !=
EngineInstance healthy
        !=
tenant binding + grant
        !=
runtime resolution
```

P-CAP-08 must preserve every boundary above.

## Decision

Pulse adopts ADR-SHARED-032 as the certification and activation authority, but
does not implement certification state locally and does not activate itself.

The repository consumes Shared at:

```text
f61de9c5141e432b32cc3b585aafa7d1b6727716
```

and pins the P-CAP-08 governance contracts needed to prove that boundary:

- `capability/v1/certification.schema.json`;
- `capability/v1/registration-bundles.yaml`;
- `intelligence/v1/pulse-registration.json`;
- `topology/v1/release-policy.yaml`;
- the updated canonical Intelligence capability, scope, workload and context
  contracts already consumed by Pulse.

## Canonical lifecycle versus provider lifecycle

Shared now declares:

| Capability | Canonical lifecycle | Maturity |
|---|---|---|
| `intelligence.evidence.search@1` | ACTIVE | EXPERIMENTAL |
| `intelligence.research-mission.manage@1` | ACTIVE | EXPERIMENTAL |

The Shared transitional registration bundle still creates
`baobab-pulse.core` as `DRAFT`.

Pulse's repository declaration remains an implementation-evidence declaration
with both supports at `IMPLEMENTED`. It carries no provider lifecycle,
certification, binding, grant, instance or health state.

Only the Control Plane may move the registered provider from DRAFT to ACTIVE.

## Certification authority

EA-09 certification is a Control Plane-owned record bound to:

```text
provider
  + canonical capability
  + contract major
  + immutable EngineRelease
  = ProviderCapabilityCertification
```

Pulse MUST NOT:

- mint a certification identifier;
- persist certification as Pulse domain state;
- hold or use the privileged human `provider:certify` scope;
- treat repository CI as an implicit Control Plane certification;
- inherit certification from an older EngineRelease;
- mark a provider ACTIVE because a certification exists.

The certifier is an authenticated privileged human at the Control Plane
boundary, subject to the canonical maker/checker and admission rules.

## Qualification profile

P-CAP-08 uses the Shared qualification profile:

```text
ea-09/pulse-intelligence-v1
```

Each capability contract major is certified independently against the exact
immutable Pulse EngineRelease proposed for activation.

A certification request must use immutable evidence references carrying both a
URI and SHA-256 digest. Pulse source code must not commit fabricated run URLs or
placeholder digests as if they were qualification evidence.

## Repository evidence available for qualification

The following evidence classes already exist and are suitable inputs to an
immutable qualification bundle produced for a concrete release.

### Contract conformance

- `tests/contract/test_evidence_search_capability_contract.py`
- `tests/contract/test_research_mission_capability_contract.py`
- `tests/contract/test_p_cap_08_activation_governance.py`
- provider-declaration validation against the pinned Shared authority

### Live integration

- `tests/integration/test_evidence_postgres_qdrant_roundtrip.py`
- `tests/integration/test_research_mission_postgres_roundtrip.py`
- `tests/integration/test_research_mission_mutation_governance.py`

### Security

- `tests/infrastructure/test_p_cap_07_authority_adapters.py`
- canonical API negative tests for scope, context, tenant-header bypass and
  classification non-disclosure
- repository security/Foundation workflows

### Operability/readiness

- production composition fails closed when authority configuration is missing
  or partial;
- PostgreSQL and Qdrant are exercised as live CI services;
- canonical health/readiness behavior remains separate from certification.

The immutable qualification artifact may summarize these results, but the
Control Plane certification record stores only content-addressed evidence
references, never credentials or raw secrets.

## Activation sequence

P-CAP-08 follows this order:

```text
Pulse main
  |
  | build immutable artifact
  v
EngineRelease CANDIDATE
  |
  | EA-09 qualification for EACH capability major
  v
ProviderCapabilityCertification
  |
  | governed ENGINE_RELEASE_APPROVAL
  v
EngineRelease APPROVED
  |
  | infrastructure deploys / observes
  v
EngineInstance + fresh health/deployment evidence
  |
  | governed PROVIDER_ACTIVATION changeset
  v
baobab-pulse.core ACTIVE
```

Production release approval and provider activation require current
certification under Shared release policy. Non-production environments remain
permissive unless Shared policy is separately tightened.

## Runtime activation is not tenant entitlement

P-CAP-08 does not create:

- `CapabilityBinding`;
- `CapabilityGrant`;
- consumer IAM Intelligence scope allocations;
- tenant provisioning;
- tenant routing;
- a synthetic `EngineInstance`;
- synthetic health or deployment observations.

An ACTIVE provider with no eligible binding/grant remains non-resolvable for a
tenant. That is the intended architecture.

## Event boundary

`com.baobab-platform.intelligence.research-mission.created.v1` remains
`HELD_UNREGISTERED`.

Provider certification and activation do not authorize event publication.
Producer-event governance remains a separate increment.

## Control Plane dependency

At the time of this decision, Control Plane PR #265 is the implementation path
for ADR-SHARED-032 certification persistence, API admission and integration with
release approval/provider activation.

Pulse may complete its repository-side P-CAP-08 contract and evidence handoff
without pretending that the Control Plane operational steps have already
occurred.

## P-CAP-08 exit criteria

### Pulse repository slice

Complete when:

1. Pulse pins ADR-SHARED-032 authority;
2. canonical capability fixtures are current;
3. certification, registration and release-policy contracts are pinned;
4. the provider declaration remains IMPLEMENTED-only;
5. executable tests enforce the certification/activation separation;
6. qualification evidence sources are explicitly identified.

### Cross-platform runtime slice

Complete only when, for one exact Pulse EngineRelease:

1. Control Plane certification support is merged and deployed;
2. the release is recorded immutably;
3. both capability majors have current EA-09 certifications under
   `ea-09/pulse-intelligence-v1`;
4. the release passes governed approval;
5. an EngineInstance and required fresh observations exist;
6. the PROVIDER_ACTIVATION changeset passes every plan check and is approved by
   the required distinct principal;
7. Control Plane reports `baobab-pulse.core` ACTIVE.

Bindings, grants and consumer scopes remain later consumer-specific work.

## Invariants

**PULSE-CERT-001** — Pulse never self-certifies.

**PULSE-CERT-002** — Pulse never self-activates its CapabilityProvider.

**PULSE-CERT-003** — Certification is release-specific and capability-major
specific.

**PULSE-CERT-004** — Canonical capability ACTIVE does not imply provider ACTIVE.

**PULSE-CERT-005** — `IMPLEMENTED` remains a repository evidence statement.

**PULSE-CERT-006** — Production release approval and provider activation fail
closed when required certification is absent, expired or revoked.

**PULSE-CERT-007** — Certification creates no binding, grant, entitlement,
tenant authority or routing.

**PULSE-CERT-008** — Synthetic instance, health or deployment evidence is
forbidden.

**PULSE-CERT-009** — The held ResearchMission event remains unpublished.

## Consequences

P-CAP-08 now has a clean repository-to-platform handoff. Pulse can prove what it
implements and produce qualification evidence; Shared defines the canonical
rules; Control Plane decides certification and activation; Infrastructure
supplies deployment truth.

This deliberately leaves operational activation outstanding until real release,
certification, instance and health facts exist.
