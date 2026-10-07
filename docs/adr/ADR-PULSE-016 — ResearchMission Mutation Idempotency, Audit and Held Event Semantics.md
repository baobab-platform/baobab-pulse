# ADR-PULSE-016 — ResearchMission Mutation Idempotency, Audit and Held Event Semantics

**Status:** Accepted  
**Date:** 2026-10-07  
**Programme:** P-CAP-05  
**Capability:** `intelligence.research-mission.manage`  
**Depends on:** ADR-PULSE-014, ADR-PULSE-015, ADR-SHARED-025, ADR-SHARED-029

## Decision

The canonical `CREATE` operation for `intelligence.research-mission.manage`
is governed as one atomic PostgreSQL mutation consisting of:

```text
ResearchMission row
        +
idempotency record
        +
mutation audit record
        +
HELD event candidate
```

All four durable effects commit or roll back together.

`GET` remains a non-mutating read and does not require an idempotency key.

## Idempotency contract

Canonical CREATE requires:

```text
Idempotency-Key: <16..128 chars>
```

using the same lexical constraints already present in the Shared CloudEvents
envelope profile.

The durable key scope is:

```text
(tenant_id, actor_subject, capability_key, idempotency_key)
```

not merely the raw header value.

This prevents unrelated tenants or authenticated principals from sharing one
idempotency namespace.

The request fingerprint is SHA-256 over the canonical JSON form of the exact
Shared v1 CREATE body. Transient authority metadata such as bearer token and
Control Plane context handle is not mixed into the semantic request
fingerprint.

### Replay

```text
same scope + same key + same request fingerprint
        -> return the originally committed ResearchMission
        -> create no second mission
        -> create no second audit record
        -> create no second event candidate
```

### Conflict

```text
same scope + same key + different request fingerprint
        -> 409 IDEMPOTENCY_CONFLICT
        -> no mutation
```

Concurrent duplicates converge through the PostgreSQL unique key and one
transactional commit.

## Audit provenance

Every successful new CREATE records immutable mutation provenance:

```text
audit_id
mission_id
tenant_id
actor_subject
actor_client_id?
context_id
capability_key
operation = CREATE
idempotency_key
request_fingerprint
result_fingerprint
correlation_id
occurred_at
```

The bearer token is never persisted.

The audit record describes the mutation that actually happened. An
idempotent replay is not a second mutation and therefore does not create a
second mutation-audit row.

## Transaction boundary

```text
BEGIN
  claim idempotency key
  insert ResearchMission
  insert mutation audit
  insert HELD event candidate
COMMIT
```

If any step fails, none of the four effects becomes durable.

The idempotency foreign key is deferrable so the key claim can be won before
the candidate mission row is inserted. This allows concurrent callers to
converge without creating orphan candidate missions.

## Event governance

ADR-SHARED-025 keeps the Shared `intelligence` event context:

```text
status = RESERVED
events = none
```

and requires a real consumer plus Shared registration before an Intelligence
event may be activated.

P-CAP-05 does **not** override that rule.

The atomic mutation stores a local event candidate with the prospective type:

```text
com.baobab-platform.intelligence.research-mission.created.v1
```

but the outbox row is forcibly marked:

```text
publication_status = HELD_UNREGISTERED
```

and its data schema URI is deliberately:

```text
urn:baobab-platform:unregistered-schema:intelligence:research-mission.created:v1
```

This makes the governance state machine explicit:

```text
durable mutation
      |
      v
HELD_UNREGISTERED candidate
      |
      |  future: stable payload + real consumer + Shared registration
      v
PUBLISHABLE
      |
      v
published by a governed relay
```

P-CAP-05 implements only the first two states.

No runtime publisher claim, AsyncAPI activation or provider-support promotion
is made by this ADR.

## Held candidate payload

The candidate deliberately contains only bounded fact identity/state:

```text
research_mission_id
status
tenant_scope
classification
```

It does not copy the research question/title into the event candidate and
does not include the authenticated bearer token or other credentials.

The envelope still conforms structurally to the Shared CloudEvents profile so
future activation does not require inventing a different delivery envelope.

## Correlation

The request correlation UUID is persisted in both audit and candidate event
envelope. The originating `Idempotency-Key` is also carried in the held
envelope, consistent with the Shared envelope rule for events caused by an
idempotent command.

## Integrity checks

On replay, Pulse fails closed if any persisted invariant diverges:

- request payload does not match its fingerprint;
- ResearchMission payload does not match its result fingerprint;
- mission identity diverges from the idempotency record;
- audit record is missing;
- held event candidate is missing;
- candidate envelope fingerprint is invalid;
- candidate tenant/subject/idempotency key diverges;
- candidate has escaped `HELD_UNREGISTERED` before Shared activation.

These are integrity failures, not reasons to silently manufacture replacement
state.

## Provider-support status

P-CAP-05 completes the mutation-governance prerequisite from ADR-SHARED-029,
but provider support is still not declared in this increment.

```text
canonical contract                 yes
authenticated/context-bound route  yes
durable ResearchMission            yes
idempotent CREATE                  yes
durable mutation audit             yes
atomic held event candidate        yes
Shared Intelligence event active   no
provider support PARTIAL           no
provider support IMPLEMENTED       no
```

The next governed step is P-CAP-06: assess accumulated implementation
evidence and, if justified, declare evidence-backed PARTIAL provider support.

## Verification

P-CAP-05 is accepted only when automated tests prove:

1. missing/invalid `Idempotency-Key` rejects CREATE;
2. identical replay returns the same mission identity;
3. key reuse with a different request returns 409;
4. concurrent duplicate CREATE converges to one durable mutation;
5. exactly one audit record exists;
6. exactly one held outbox candidate exists;
7. held candidate conforms to the Shared envelope shape;
8. held candidate cannot masquerade as an activated event;
9. trusted tenant/context/caller provenance is persisted;
10. bearer tokens are not persisted;
11. GET remains non-mutating and requires no idempotency key.
