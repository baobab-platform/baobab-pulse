# P-CAP-08 staging release and EngineRelease handoff

This runbook covers the Pulse-owned release step required before an immutable
Pulse artifact can participate in Control Plane release governance.

It does **not** certify or activate `baobab-pulse.core`.

## Trigger

The staging publisher runs only for tags matching:

```text
vMAJOR.MINOR.PATCH-staging
```

For example, `v0.2.0-staging`.

Do not use a moving `staging-latest` tag as release identity.

## Preconditions

The tagged commit must:

1. be an ancestor of `main`;
2. already have a successful **Pulse CI** push run for the exact SHA;
3. already satisfy the successful Foundation gate required by the Shared
   reusable staging publisher.

The workflow fails closed if any precondition cannot be established.

## What the workflow publishes

The repository delegates image publication to the pinned Shared
`reusable-staging-image.yml` workflow.

For `ghcr.io/baobab-platform/baobab-pulse`, that workflow:

1. builds the Linux/amd64 runtime image once from the tagged source;
2. scans that exact image for HIGH/CRITICAL vulnerabilities;
3. emits an SPDX JSON SBOM;
4. refuses to overwrite an existing staging version;
5. pushes the tested bytes to GHCR;
6. records the exact `sha256` image digest;
7. creates a GitHub artifact containing `staging-image.json` and the SBOM;
8. publishes a provenance attestation for the exact image digest.

The image tag is a locator. The digest is the immutable artifact identity.

## What Pulse does not do

The staging workflow does not:

- call a privileged Control Plane release-recording API;
- create an `EngineRelease`;
- approve an `EngineRelease`;
- create an `EngineInstance`;
- report health or deployment observations;
- certify a provider capability;
- activate `baobab-pulse.core`;
- create tenant bindings or grants.

An engine must not become the authority that certifies or activates itself.

## Control Plane handoff

After a successful staging publication, authorised release tooling may use the
published evidence to record the immutable release in Control Plane.

The handoff facts include:

```text
engine              baobab-pulse
source revision     <tagged Git SHA>
release version     <tag without leading v, policy-normalised by release tooling>
image               ghcr.io/baobab-platform/baobab-pulse@sha256:<digest>
provenance           GitHub attestation for the same digest
provider             baobab-pulse.core
capability support   intelligence.evidence.search@1
                     intelligence.research-mission.manage@1
```

Control Plane remains responsible for validating those facts against the
registered provider declaration and canonical Shared capability contracts.

## Relationship to EA-09 certification

Shared release policy currently requires EA-09 certification for **production**
release approval/provider activation, not for staging.

Therefore a staging image can be used to prove deployment and operational
behavior without pretending that production certification has already occurred.

For production P-CAP-08 closure, the exact production-bound EngineRelease still
requires a current certification for each capability major under:

```text
ea-09/pulse-intelligence-v1
```

Certification evidence must remain immutable and content-addressed.

## Relationship to infrastructure

The staging image artifact is an input to deployment tooling, not a deployment
command from Pulse.

Infrastructure decides how the approved/desired EngineRelease is deployed and
reports observed runtime state back to Control Plane. Pulse never fabricates its
own deployment or health evidence.

## Failure behavior

A release must stop if:

- the tag format is invalid;
- the tagged commit is not on `main`;
- exact-source Pulse CI is not green;
- Foundation acceptance for that source is absent;
- image scanning fails;
- the target version already exists;
- the registry cannot prove the version is absent before publication;
- an immutable digest cannot be established;
- provenance attestation or artifact upload fails.

The remedy is to correct the cause and rerun where safe, or cut a new version.
Never overwrite a published staging version.

## P-CAP-08 effect

This closes the Pulse-owned **artifact production** gap in P-CAP-08.

It still leaves the following cross-platform runtime facts outstanding:

1. immutable EngineRelease registration in Control Plane;
2. EA-09 certifications for the production-bound release;
3. governed release approval;
4. EngineInstance deployment and observations;
5. governed provider activation.

Consumer-specific CapabilityBinding, CapabilityGrant, tenant Intelligence scope
allocation and tenant routing are outside P-CAP-08. The research-mission-created
event remains `HELD_UNREGISTERED`.


## Verified coordinated selection (7 October 2026)

The published Pulse identity is:

```text
tag      v0.1.0-staging
source   b355bfa1139efb5e72ac0895a36b49fb1f2e4bc2
digest   sha256:1f57b26d017a98dd14dc9b589ef40cfd2431c1241fd928c13027f7f353ea9b80
run      https://github.com/baobab-platform/baobab-pulse/actions/runs/37627757084
```

The first five-component Infrastructure selection proposes
`v0.1.0-staging.coordination.json` under `deploy/releases/staging/`, selecting
Shared v2.4.1-staging, CP v1.1.1-staging, IAM federation authority and Keycloak
v0.1.1-staging, and Pulse v0.1.0-staging. Infrastructure retains the matching
publisher receipts, SPDX SBOMs and a dated verification snapshot. The selection
is account-independent; it does not imply that an Infrastructure tag or a real
AWS manifest exists. Consult Infrastructure's
`docs/runbooks/p-cap-08-first-coordinated-release.md` for account inputs, live
verification, observation and governance handoff.

The 7 October audit independently ran Python 3.14.7 tests: 163 passed and four
live PostgreSQL tests skipped because no migrated database was reachable. Ruff
and strict mypy passed. These local results are not staging qualification.

Pulse's `/healthz` establishes process liveness only. The infrastructure ECS
health observation therefore must be supplemented by `/readyz` dependency
evidence and authenticated capability checks against the actual IAM and CP
authorities. Evidence-search qualification requires working semantic retrieval;
`/readyz` may otherwise report overall readiness with semantic search degraded.
Do not promote liveness or image publication to EA-09 certification.
