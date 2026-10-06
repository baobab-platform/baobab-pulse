# ADR-PULSE-013 — Upstream Intelligence Projection, Cross-Engine Reference and Non-Enforcement Consumer Architecture

**Status:** Accepted — Normative RTD-09 Consumer Architecture  
**Date:** 2026-10-06  
**Decision ID:** ADR-PULSE-013  
**Engine:** Baobab Pulse  
**Repository:** baobab-platform/baobab-pulse  
**Decision Type:** Cross-Engine Event Consumption / Projection / Evidence / Capability Namespace Alignment  
**Implements:** RTD-09 from ADR-SHARED-019  
**Platform Authorities:** ADR-SHARED-019, ADR-SHARED-021, ADR-SHARED-023, ADR-SHARED-024, ADR-SHARED-025  
**Depends On:** ADR-PULSE-001 through ADR-PULSE-012  
**Primary Principle:** **Pulse consumes authoritative upstream facts asynchronously, preserves their owner identity, and derives intelligence without becoming regulatory/documentary authority or an enforcement dependency.**

---

## 1. Executive Decision

Baobab Pulse SHALL consume selected canonical facts from Baobab Regulations and Baobab Trade Docs as **asynchronous analytical inputs**.

Pulse SHALL project those facts into a minimal, rebuildable read model that preserves:

- source event identity;
- source engine;
- tenant;
- occurrence time;
- canonical cross-engine references;
- small analytical state codes where useful;
- a payload digest for idempotency and provenance.

Pulse SHALL NOT create local copies of the upstream canonical aggregates.

The runtime shape is:

~~~text
baobab-regulations                  baobab-trade-docs
        │                                  │
        │ canonical facts                  │ canonical facts
        └──────────────┬───────────────────┘
                       ▼
             Pulse RTD-09 consumer
                       │
        producer / tenant / reference
             validation + digest
                       │
                       ▼
        UpstreamFactProjection
          rebuildable read model
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          Evidence            Observation/
             │                 Analysis
             └─────────┬─────────┘
                       ▼
        Insight / Risk / Opportunity /
        Forecast / Recommendation
~~~

The enforcement path remains:

~~~text
Trade / TMS
    │
    ▼
Regulations
    ↔ Trade Docs
    │
    ▼
Operational PEP
~~~

Pulse is downstream of that path.

---

## 2. Capability Namespace Decision

The canonical capability namespace is:

~~~text
intelligence
~~~

not:

~~~text
pulse
~~~

`baobab-pulse` is the engine/provider identity.

`intelligence` is the reusable business-capability domain.

ADR-SHARED-025 refines the namespace to cover:

- evidence and research;
- observations;
- analysis;
- signals, trends and anomalies;
- risks and opportunities;
- forecasting and scenarios;
- recommendations;
- intelligence products.

RTD-09 does not catalogue any `intelligence.*` capability.

---

## 3. Why No Capability Declaration Yet

Pulse already has real implementation in several areas, but capability promotion requires a separate capability census against the canonical Shared taxonomy.

RTD-09 therefore does not guess that the following are canonical capabilities:

~~~text
intelligence.evidence.search
intelligence.research.execute
intelligence.analysis.run
intelligence.risk.assess
intelligence.opportunity.detect
intelligence.forecast.generate
~~~

These are investigation areas, not approved keys.

The rule is:

~~~text
implemented code
    ↓
capability census
    ↓
stable public ability?
    ↓
canonical Shared contract?
    ↓
catalogue promotion
    ↓
provider declaration
~~~

---

## 4. Event Context Alignment

Shared reserves:

~~~text
intelligence
~~~

as the future event context stewarded by:

~~~text
baobab-pulse
~~~

RTD-09 activates no Pulse-produced event.

This repository's old local scaffold used:

~~~text
com.baobab-platform.pulse.*
~~~

That repository-oriented namespace is replaced locally by:

~~~text
com.baobab-platform.intelligence.*
~~~

for future event construction.

The context is still RESERVED in Shared, so the local helper is not a production event contract.

---

## 5. Supported Upstream Events

RTD-09 initially consumes five already-active facts.

### Regulations

~~~text
com.baobab-platform.regulations.document-requirements.determined.v1

com.baobab-platform.regulations.requirement-satisfaction.evaluated.v1
~~~

### Trade Docs

~~~text
com.baobab-platform.documents.regulatory-evidence.offered.v1

com.baobab-platform.documents.document-version.verification-changed.v2

com.baobab-platform.documents.document-version.validity-changed.v2
~~~

This list is deliberately bounded.

Adding another upstream event is a code/contract change, not a dynamic wildcard subscription.

---

## 6. Producer Validation

Pulse SHALL validate event type and logical producer as a pair.

| Event context | Canonical producer |
|---|---|
| `regulations.*` RTD-08 facts | `baobab-regulations` |
| `documents.*` RTD-07 facts | `baobab-trade-docs` |

Canonical logical sources are:

~~~text
urn:baobab-platform:service:baobab-regulations

urn:baobab-platform:service:baobab-trade-docs
~~~

A valid event type from the wrong producer is rejected.

---

## 7. Why Producer Validation Matters

Without source/type binding an event bus participant could send:

~~~text
type = regulations.requirement-satisfaction.evaluated
source = some-other-engine
~~~

and Pulse could accidentally treat it as authoritative Regulations state.

RTD-09 fails closed instead.

---

## 8. Canonical Cross-Engine Reference

Pulse implements the ADR-SHARED-021 value object:

~~~text
CrossEngineObjectReference
├── owner_engine_id
├── object_type
├── object_id
├── reference_mode
├── object_version?
├── scope
└── tenant_id?
~~~

This type is distinct from Pulse's older local `Reference`.

---

## 9. Local Reference Versus Cross-Engine Reference

~~~text
Reference
    Pulse-local relationship

CrossEngineObjectReference
    portable reference to another engine-owned canonical object
~~~

Pulse SHALL NOT use the local `Reference` type to erase upstream ownership.

---

## 10. Historical Pinning

Consequential upstream objects are historically pinned.

Examples:

~~~text
RegulatoryDecision
    IDENTITY_PINNED or VERSION_PINNED

DocumentRequirement
    IDENTITY_PINNED or VERSION_PINNED

DocumentVersion
    IDENTITY_PINNED
~~~

A `CURRENT` reference is rejected where RTD-06/RTD-09 requires historical evidence.

---

## 11. Evidence Integration

`Evidence.referenced_object` may now contain either:

~~~text
Pulse-local Reference

or

CrossEngineObjectReference
~~~

This is the intended ADR-PULSE-012 evolution.

Example:

~~~text
Evidence
  role = supports
  referenced_object =
      owner_engine_id = baobab-regulations
      object_type = REGULATORY_DECISION
      ...
~~~

Pulse owns the analytical Evidence object.

Pulse does not own the referenced RegulatoryDecision.

---

## 12. UpstreamFactProjection

RTD-09 introduces:

~~~text
UpstreamFactProjection
~~~

as a **value object / read projection**, not a canonical aggregate.

Fields include:

~~~text
source_event_id
source_event_type
source_engine_id
tenant_id
occurred_at
correlation_id
fact_kind
references[]
state_code?
payload_digest
~~~

---

## 13. Projection Is Rebuildable

The projection may be destroyed and rebuilt from upstream events.

Therefore:

~~~text
UpstreamFactProjection
    !=
System of Record
~~~

and:

~~~text
projection loss
    !=
regulatory truth loss
    !=
documentary truth loss
~~~

---

## 14. Minimal Projection Rule

Pulse stores only what is needed for analytical correlation.

For example, a document verification event becomes:

~~~text
fact_kind = DOCUMENT_VERIFICATION_CHANGED
reference = DocumentVersion
state_code = VERIFIED
~~~

It does not become a local copy of:

- TradeDocument;
- DocumentVersion content;
- issuer record;
- verification workflow;
- authority response.

---

## 15. Requirements Projection

For:

~~~text
regulations.document-requirements.determined
~~~

Pulse retains:

- the pinned RegulatoryDecision reference;
- pinned requirement references;
- event provenance.

It does not copy the Regulations rule graph or legal reasoning model.

---

## 16. Satisfaction Projection

For:

~~~text
regulations.requirement-satisfaction.evaluated
~~~

Pulse retains:

- assessment reference;
- RegulatoryDecision reference;
- requirement reference;
- accepted/rejected DocumentVersion references;
- outcome as analytical state code;
- event provenance.

This is suitable for later analytics such as:

- rejection-rate trends;
- corridor friction;
- recurring evidence failures;
- supplier documentation risk.

---

## 17. Documentary Verification Projection

For:

~~~text
documents.document-version.verification-changed
~~~

Pulse records the exact immutable DocumentVersion reference and the new verification state.

The rule remains:

~~~text
VERIFIED
    !=
SATISFIED
~~~

Pulse does not infer regulatory sufficiency from document verification.

---

## 18. Documentary Validity Projection

For:

~~~text
documents.document-version.validity-changed
~~~

Pulse records the exact DocumentVersion reference and documentary validity state.

This may support analytics such as:

- expiry patterns;
- certificate renewal risk;
- supplier documentation health;
- route/corridor delay analysis.

It does not itself alter a RegulatoryDecision.

---

## 19. Regulatory Evidence Offered Projection

For:

~~~text
documents.regulatory-evidence.offered
~~~

Pulse retains:

- Regulations decision reference;
- Regulations requirement reference;
- offered DocumentVersion references;
- event provenance.

The event means evidence was offered.

It does not mean evidence was accepted.

---

## 20. At-Least-Once Delivery

Pulse SHALL assume upstream event delivery is at least once.

The deduplication key is:

~~~text
(source_engine_id, source_event_id)
~~~

A repeated occurrence with the same payload digest is idempotent.

---

## 21. Conflicting Replay

If the same occurrence identity arrives with a different payload digest:

~~~text
same source
same event id
different canonical payload
~~~

Pulse SHALL reject the replay.

It SHALL NOT silently overwrite the projection.

This preserves provenance integrity.

---

## 22. Payload Digest

RTD-09 computes:

~~~text
sha256(canonical-json(data))
~~~

for replay conflict detection.

The digest is a consumer provenance aid.

It is not a substitute for:

- upstream signature verification;
- Trade Docs ContentArtifact digest;
- legal authenticity;
- event transport security.

---

## 23. Tenant Isolation

Every supported RTD-09 event is tenant scoped.

Pulse validates:

~~~text
CloudEvent.tenantid
    =
payload tenant_id
    =
nested tenant-scoped references
    =
projection tenant_id
~~~

Mismatch is rejected.

---

## 24. Cross-Tenant Rule

RTD-09 defines no cross-tenant exception.

A Pulse tenant projection SHALL never aggregate another tenant's regulatory/documentary facts merely because object IDs are known.

Cross-tenant intelligence, if ever needed, requires a separate governed aggregation/privacy contract.

---

## 25. No Synchronous Upstream Call

`UpstreamFactProjectionService` SHALL have no direct dependency on:

- HTTP clients;
- Regulations client SDK;
- Trade Docs client SDK;
- another engine database;
- Haystack;
- Qdrant.

Its job is:

~~~text
validate event
    ↓
extract owner references
    ↓
create minimal projection
    ↓
store idempotently
~~~

---

## 26. Why No Hydration in the Consumer

Automatic synchronous hydration would make event consumption depend on upstream API availability.

RTD-09 deliberately avoids:

~~~text
event received
    ↓
must call Regulations
    ↓
must call Trade Docs
    ↓
only then can Pulse ingest
~~~

If a later analytical workflow needs more detail, it may request it separately under explicit authorization.

---

## 27. Critical-Path Isolation

Pulse SHALL NOT be required for:

- regulatory applicability;
- classification;
- obligation determination;
- document requirement determination;
- documentary evidence satisfaction;
- customs submission;
- authority response processing;
- shipment hold/release.

This repeats and operationalises ADR-PULSE-012 §21.

---

## 28. Failure Isolation

~~~text
Pulse consumer down
    → intelligence may lag
    → regulatory execution continues

Pulse projection store down
    → event can be retried/replayed
    → upstream authority unchanged

Qdrant down
    → semantic retrieval degraded
    → upstream facts unchanged
~~~

---

## 29. Projection Store Port

RTD-09 defines:

~~~text
UpstreamFactProjectionPort
~~~

The application depends on the port.

Infrastructure supplies the adapter.

The reference adapter is:

~~~text
InMemoryUpstreamFactProjectionStore
~~~

A future PostgreSQL implementation may replace it without changing the application service.

---

## 30. Projection Storage Is Not Foreign Persistence

A future PostgreSQL table for `UpstreamFactProjection` remains Pulse-owned derived storage.

It SHALL NOT be named or treated as a foreign canonical table such as:

~~~text
regulatory_decisions
trade_documents
document_versions
~~~

The source owner remains explicit in every row/value.

---

## 31. Source Event Identity

Pulse stores the canonical upstream event occurrence ID.

It does not mint a replacement ID and claim that it is the authoritative event identity.

---

## 32. Correlation

The upstream event's correlation ID is retained.

This allows analytical traces to connect:

~~~text
requirement determined
    ↓
evidence offered
    ↓
satisfaction evaluated
    ↓
later Pulse analysis
~~~

without collapsing the three authorities.

---

## 33. Future Intelligence Events

Pulse may eventually publish facts such as:

~~~text
intelligence.insight.published
intelligence.risk.identified
intelligence.opportunity.detected
intelligence.forecast.published
~~~

RTD-09 does not register them.

Future activation requires Shared review and canonical payloads.

---

## 34. Existing Outbox

Pulse's local transactional-outbox scaffold remains valid as an implementation pattern.

Its future event type helper now constructs:

~~~text
com.baobab-platform.intelligence.*
~~~

rather than:

~~~text
com.baobab-platform.pulse.*
~~~

This prevents an avoidable namespace migration.

---

## 35. No Runtime Producer Claim

Changing the local helper does not mean:

~~~text
intelligence context ACTIVE
or
Pulse events registered
~~~

Shared still marks the context RESERVED.

No RTD-09 code should publish unregistered production events.

---

## 36. Haystack Boundary

The upstream projector imports no Haystack types.

Haystack may consume Pulse evidence/projections later through existing application ports/pipelines.

It does not validate regulatory truth.

---

## 37. Qdrant Boundary

Upstream facts SHALL NOT be written directly to Qdrant as canonical truth.

If embedded for retrieval later:

~~~text
upstream event
    ↓
Pulse projection / Evidence in canonical Pulse store
    ↓
derived semantic projection
    ↓
Qdrant
~~~

Qdrant remains rebuildable.

---

## 38. Regulatory Contradictions

Pulse may observe contradictory upstream facts over time.

It may analyse:

- change;
- uncertainty;
- operational impact;
- data-quality anomalies.

It SHALL NOT rewrite the Regulations history or choose a legal interpretation by model confidence.

---

## 39. Documentary Contradictions

Pulse may observe:

~~~text
DocumentVersion A VERIFIED
DocumentVersion B FAILED
~~~

and derive risk.

It SHALL NOT alter either verification state.

---

## 40. Capability Provider Declaration

RTD-09 intentionally does not add a `.baobab/capability-provider.yaml` declaration with guessed capability keys.

After the capability census:

- canonical keys may be added to Shared;
- Pulse may declare provider support;
- implementation evidence will point to real services/tests.

---

## 41. Architecture Tests

RTD-09 SHALL mechanically test:

1. cross-engine reference scope/pinning;
2. tenant consistency;
3. producer/type binding;
4. duplicate delivery idempotency;
5. conflicting replay failure;
6. verification does not become satisfaction;
7. projection is not a canonical aggregate;
8. projector imports no HTTP/database/provider SDK;
9. foreign canonical aggregate classes are absent;
10. future local event types use `intelligence`, not `pulse`.

---

## 42. Example — Document Verification

~~~text
Trade Docs
DocumentVersion DV-3
verification = VERIFIED
        │
        ▼ event
Pulse
UpstreamFactProjection
  ref = DV-3
  state = VERIFIED
        │
        ▼
Evidence / Analysis
        │
        ▼
Supplier documentation reliability insight
~~~

No regulatory result is invented.

---

## 43. Example — Requirement Satisfaction

~~~text
Regulations
Requirement R-1
Assessment A-4
Outcome = UNSATISFIED
        │
        ▼
Pulse projection
        │
        ├── ref A-4
        ├── ref R-1
        ├── ref RegulatoryDecision
        └── ref rejected DocumentVersion
                │
                ▼
        corridor / supplier / product analysis
~~~

---

## 44. Example — Pulse Outage

~~~text
Trade Docs ───► Regulations ───► PEP
                    │
                    └── event ──X── Pulse unavailable
~~~

The operational path still completes.

Once Pulse recovers, events can be replayed.

---

## 45. Rejected Alternatives

### A. Copy Regulations and Trade Docs aggregates into Pulse

Rejected. It creates shadow canonicals and stale authority.

### B. Make Pulse query upstream synchronously for every event

Rejected. It creates availability coupling and puts intelligence on the enforcement path.

### C. Let Pulse infer satisfaction from VERIFIED

Rejected. Document verification and regulatory sufficiency are distinct.

### D. Keep `com.baobab-platform.pulse.*`

Rejected. Event contexts are business domains, not repository names.

### E. Activate intelligence events in RTD-09

Rejected. RTD-09 is a consumer increment.

### F. Catalogue intelligence capabilities now

Rejected. Capability names and implementation evidence require a separate census.

### G. Store arbitrary full upstream payloads as the projection

Rejected. Minimal reference-first projections better preserve bounded contexts.

---

## 46. Invariants

~~~text
INV-PULSE-RTD09-001
Pulse consumes RTD-09 upstream events asynchronously.

INV-PULSE-RTD09-002
Pulse is not a regulatory/documentary enforcement dependency.

INV-PULSE-RTD09-003
Every upstream projection retains canonical source event identity.

INV-PULSE-RTD09-004
Every cross-engine reference retains owner_engine_id.

INV-PULSE-RTD09-005
Tenant-scoped references match the event tenant.

INV-PULSE-RTD09-006
Wrong producer/type combinations are rejected.

INV-PULSE-RTD09-007
DocumentVersion references used as evidence are IDENTITY_PINNED.

INV-PULSE-RTD09-008
CURRENT references are rejected for consequential regulatory/documentary evidence.

INV-PULSE-RTD09-009
UpstreamFactProjection is a derived value/read model, not a canonical aggregate.

INV-PULSE-RTD09-010
Pulse does not define RegulatoryDecision, DocumentRequirement, TradeDocument or DocumentVersion aggregates.

INV-PULSE-RTD09-011
Document verification does not imply requirement satisfaction.

INV-PULSE-RTD09-012
Evidence offered does not imply evidence accepted.

INV-PULSE-RTD09-013
Duplicate event delivery is idempotent.

INV-PULSE-RTD09-014
Same occurrence identity with conflicting payload fails closed.

INV-PULSE-RTD09-015
The projector performs no synchronous upstream hydration.

INV-PULSE-RTD09-016
Haystack and Qdrant are absent from the event-ingestion authority boundary.

INV-PULSE-RTD09-017
Evidence may reference foreign objects without transferring ownership.

INV-PULSE-RTD09-018
The canonical capability domain is intelligence, not pulse.

INV-PULSE-RTD09-019
RTD-09 promotes no intelligence capability.

INV-PULSE-RTD09-020
RTD-09 activates no Pulse-produced event.

INV-PULSE-RTD09-021
Future Pulse event naming uses the reserved intelligence context.

INV-PULSE-RTD09-022
Projection failure does not alter upstream canonical truth.
~~~

---

## 47. Consequences

### Positive

- Pulse can analyse real regulatory/documentary facts without duplicating domain truth.
- Cross-engine ownership becomes executable, not merely architectural prose.
- Event ingestion is idempotent and tenant-safe.
- Producer spoofing is rejected.
- Regulations/Trade Docs remain operationally independent of Pulse.
- Future intelligence capabilities/events have a clean namespace.
- RTD-10 can now write cross-repository conformance tests against executable Pulse behavior.

### Costs

- Pulse now carries a second, explicit reference type for cross-engine identity.
- Consumer mappings must be updated when upstream canonical contracts change.
- A production projection store and event subscription runtime are still required.
- Capability census remains additional work.
- Future intelligence event activation remains additional governance.

---

## 48. Final Decision

~~~text
Shared
  capability domain = intelligence
  event context = intelligence (RESERVED)
           │
           │ steward intent
           ▼
      baobab-pulse
           ▲
           │ async facts
     ┌─────┴─────┐
     │           │
Regulations   Trade Docs
     │           │
     └─────┬─────┘
           ▼
   owner-preserving
   minimal projections
           ▼
 Evidence / Analysis
           ▼
Intelligence products
~~~

> **Pulse consumes authority; it does not absorb authority. The platform namespace is intelligence, and RTD-09 makes that boundary executable without inventing capabilities or putting Pulse on the enforcement path.**
