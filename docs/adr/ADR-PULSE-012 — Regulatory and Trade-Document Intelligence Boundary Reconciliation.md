# ADR-PULSE-012 — Regulatory and Trade-Document Intelligence Boundary Reconciliation

**Status:** Accepted — Normative Boundary Reconciliation  
**Date:** 2026-10-05  
**Decision ID:** ADR-PULSE-012  
**Engine:** Baobab Pulse  
**Repository:** baobab-platform/baobab-pulse  
**Decision Type:** Cross-Engine Boundary Reconciliation / Intelligence Authority / Evidence Semantics  
**Platform Authority:** ADR-SHARED-019 — Regulatory Intelligence, Trade Documents and Evidence Cross-Engine Boundary  
**Depends On:** ADR-PULSE-001 through ADR-PULSE-011  
**Amends / Supersedes in Part:** ADR-PULSE-001, ADR-PULSE-003, ADR-PULSE-004, ADR-PULSE-005, ADR-PULSE-006, ADR-PULSE-009  
**Related Engines:** baobab-regulations, baobab-trade-docs, baobab-trade, baobab-tms, baobab-cp  
**Primary Principle:** **Pulse observes, analyses and recommends; Regulations determines regulatory meaning; Trade Docs owns documentary lifecycle.**

---

## 1. Executive Decision

Baobab Pulse SHALL remain the Baobab Platform **System of Intelligence, Research and Analytical Evidence**.

The introduction of Baobab Regulations and Baobab Trade Docs does **not** remove regulatory, customs or trade-document information from Pulse's intelligence scope.

It changes what those concepts mean inside Pulse.

The reconciled boundary is:

~~~text
Regulatory / customs / documentary facts
                 │
       ┌─────────┴─────────┐
       │                   │
       ▼                   ▼
Baobab Regulations   Baobab Trade Docs
normative meaning    documentary lifecycle
       │                   │
       └─────────┬─────────┘
                 │ references / events
                 ▼
           Baobab Pulse
     observation / evidence /
     analysis / intelligence
~~~

Pulse MAY:

- discover regulatory publications;
- observe regulatory and customs events;
- ingest trade statistics containing HS classifications;
- preserve analytical source artefacts;
- analyse regulatory change;
- detect commercial consequences;
- produce risks, opportunities, forecasts and recommendations;
- cite Regulations and Trade Docs objects as evidence;
- maintain research reproducibility and analytical lineage.

Pulse SHALL NOT:

- become the canonical regulatory source registry;
- mint canonical RegulatoryInstrument, Provision, RegulatoryRule, RegulatoryRequirement, RegulatoryAssessment or RegulatoryDecision objects;
- decide legal applicability for an operational transaction;
- decide whether a trade document satisfies a legal requirement;
- become the canonical TradeDocument or DocumentVersion owner;
- own customs-document submission workflow;
- infer that document verification equals regulatory satisfaction;
- place itself synchronously on the regulatory or customs enforcement critical path.

The governing rule is:

> **Regulation and customs remain first-class Pulse intelligence domains, but not Pulse authority domains.**

---

## 2. Why This Reconciliation Exists

The original Pulse architecture was written before the platform had specialised regulatory and trade-document engines.

At that time Pulse had to model several concerns generically:

| Original Pulse concern | Why it existed | New specialist authority |
|---|---|---|
| Regulatory lifecycle | Pulse needed to reason about regulatory change | Regulations |
| Government gazettes / regulatory publications | Needed as research evidence | Regulations for canonical regulatory state; Pulse may retain analytical evidence |
| Regulatory source authority | Needed for research credibility | Regulations for regulatory authority; Pulse retains research-quality assessment |
| Regulatory profile | Needed to analyse regulations by jurisdiction, product and time | Regulations for canonical legal semantics |
| Customs profile | Needed to analyse declarations, duties and clearance | Split among Trade Docs, Regulations and operational owners |
| Tariff / preferential eligibility | Needed for landed-cost intelligence | Regulations for transaction-specific regulatory meaning |
| Regulatory delta | Needed for alerts and opportunities | Regulations owns canonical regulatory change; Pulse owns commercial analysis |
| SourceDocument / Raw Evidence Vault | Needed for reproducible research | Remains valid in Pulse for Pulse-acquired evidence; not universal platform ownership |
| Regulatory lineage | Needed to explain analytical conclusions | Pulse lineage references Regulations canonical nodes |

The architecture therefore evolved from:

~~~text
EARLY MODEL

Pulse
├── research
├── evidence
├── regulatory observations
├── regulatory documents
├── regulatory lifecycle
├── regulatory change
├── customs observations
└── commercial consequences
~~~

to:

~~~text
TARGET MODEL

Baobab Regulations
├── regulatory source authority
├── instrument / provision
├── interpretation / rule
├── applicability
├── obligation / requirement
└── regulatory decision

Baobab Trade Docs
├── TradeDocument
├── DocumentVersion
├── documentary provenance
├── verification facts
├── submission workflow
└── authority response

Baobab Pulse
├── observation
├── analytical evidence
├── signal
├── analysis
├── insight
├── risk / opportunity
├── forecast
└── recommendation
~~~

This ADR preserves the useful Pulse architecture while removing authority overlap.

---

## 3. Decision Hierarchy

ADR-SHARED-019 is the platform-level authority for this relationship.

Where earlier Pulse ADR wording conflicts with ADR-SHARED-019 or this reconciliation:

~~~text
ADR-SHARED-019
      ↓
ADR-PULSE-012
      ↓
earlier Pulse ADR wording
~~~

The earlier ADR remains authoritative for unaffected sections.

This ADR is deliberately **surgical**, not a wholesale replacement of the Pulse architecture programme.

---

## 4. Canonical Authority Matrix

| Question | Pulse | Regulations | Trade Docs | External / operational authority |
|---|---:|---:|---:|---:|
| What did a source publish? | Observe / cite | Canonical regulatory acquisition when regulatory | Preserve document/authority artefact when documentary | Original publisher remains source authority |
| What regulation exists? | Analyse | **Owns canonical regulatory representation** | No | Competent legal authority is sovereign source |
| What does the rule require? | May discuss analytically | **Owns** | No | Courts/regulators may ultimately determine legal meaning |
| Does the rule apply to transaction T? | No canonical decision | **Owns** | Supplies documentary facts | Operational context comes from domain engines |
| Which document is required? | Analyse | **Owns requirement** | Executes workflow | — |
| Does document D exist / which version? | Reference | Reference | **Owns** | Issuer remains external authority |
| Is issuer claim verified? | Consume/reference | Consume/reference | **Owns documentary verification fact** | Issuer/credential authority remains external |
| Does D satisfy requirement R? | No | **Owns regulatory satisfaction decision** | Supplies facts | — |
| What customs response was received? | Observe | Interpret regulatory consequence where needed | **Owns Baobab documentary/workflow record** | Customs authority owns the external decision |
| What commercial risk follows? | **Owns derived intelligence** | Supplies regulatory facts | Supplies documentary facts | — |
| What opportunity follows? | **Owns derived intelligence** | Supplies regulatory facts | Supplies documentary facts | — |
| Should business take action? | Recommend | May recommend disposition within regulatory decision | May recommend workflow action | Authorised human/policy + owning PEP |
| Who mutates shipment/order state? | Never by default | Never directly | Only document/customs workflow it owns | Trade/TMS/other owning PEP |

---

## 5. Before and After

### 5.1 Before specialist engines

~~~mermaid
flowchart LR
    EXT[External Sources] --> P[Baobab Pulse]
    P --> SO[Source / DataSource]
    P --> SD[SourceDocument]
    P --> RV[Raw Evidence Vault]
    P --> RO[Regulatory Observation]
    P --> RD[Regulatory Delta]
    P --> CI[Commercial Intelligence]
~~~

This was reasonable when Pulse was the only engine capable of representing the information.

### 5.2 Reconciled topology

~~~mermaid
flowchart LR
    EXT[External Authorities and Sources]

    EXT --> REG[Baobab Regulations]
    EXT --> TD[Baobab Trade Docs]
    EXT --> P[Baobab Pulse Source Fabric]

    REG -->|RegulatoryDecision / RegulatoryChange refs| P
    TD -->|TradeDocument / authority-response refs| P

    P --> OBS[Observation]
    P --> EV[EvidenceSet]
    P --> AN[Analysis]
    P --> RI[Risk / Opportunity]
    P --> FC[Forecast]
    P --> REC[Recommendation]

    REG -->|DocumentRequirement| TD
    TD -->|Document facts / evidence refs| REG

    REG -. no direct ownership .-> OBS
    TD -. no direct ownership .-> EV
~~~

The dashed relationships indicate consumption or analytical projection, not ownership transfer.

---

## 6. Pulse Remains a Regulatory Intelligence Engine

Pulse SHALL continue to support regulatory intelligence products.

Examples remain valid:

- regulatory alerting;
- regulation-to-opportunity analysis;
- import restriction monitoring;
- tariff-change impact analysis;
- corridor risk;
- regulatory-change commercial impact;
- compliance-cost trend analysis;
- regulatory scenario analysis;
- strategic market-entry analysis.

The product concept originally described as **REGULATORY PULSE** remains valid.

Its question is:

> What changed, who may be affected, what commercial consequence may follow, and what should decision-makers investigate or consider?

Its question is **not**:

> What is the legally binding answer for this operational transaction?

That second question belongs to Regulations.

---

## 7. Regulatory Observation Modes

Pulse SHALL recognise two semantically different regulatory observation modes.

### 7.1 Mode A — Candidate source observation

Pulse may discover a regulatory-looking publication before Regulations has processed it.

~~~text
External publication
       ↓
Pulse acquisition
       ↓
SourceArtefact
       ↓
Candidate RegulatoryObservation
       ↓
NOT canonical regulatory truth
~~~

Such an observation SHALL be treated as:

- candidate;
- source-attributed;
- analytically useful;
- not promoted to canonical regulatory state;
- unsuitable as the sole basis for an operational legal decision.

It SHOULD carry enough metadata to permit governed hand-off to Regulations.

### 7.2 Mode B — Regulations-backed observation

Pulse may consume a canonical Regulations object or event.

~~~text
Baobab Regulations
       ↓
RegulatoryChange / RegulatoryDecision
       ↓
Cross-engine reference
       ↓
Pulse RegulatoryObservation
       ↓
Analysis / Insight / Risk / Opportunity
~~~

Here Pulse may state the regulatory state **as reported by Regulations**.

The Pulse object remains an intelligence projection.

---

## 8. Regulatory Observation Decision Tree

~~~mermaid
flowchart TD
    A[Pulse receives regulatory-looking information] --> B{Canonical Regulations reference available?}

    B -->|Yes| C[Resolve authorised Regulations object]
    C --> D[Create or update Pulse observation / evidence reference]
    D --> E[Analyse commercial or strategic consequence]

    B -->|No| F{Source discovered directly by Pulse?}
    F -->|No| G[Record evidence gap / insufficient evidence]
    F -->|Yes| H[Preserve Pulse source artefact where lawful]
    H --> I[Classify as candidate regulatory observation]
    I --> J[Offer governed hand-off to Regulations]
    J --> K{Regulations promotes canonical state?}
    K -->|Yes| C
    K -->|No / pending| L[Keep candidate status; do not treat as operational obligation]
~~~

This flow is mandatory in spirit even before the exact cross-engine contract is implemented.

---

## 9. Reconciliation of ADR-PULSE-001

### 9.1 Regulatory Boundary — amended

ADR-PULSE-001 currently states that Pulse distinguishes states such as:

~~~text
PROPOSED
PUBLISHED
ADOPTED
EFFECTIVE
SUSPENDED
REPEALED
~~~

That remains useful **as intelligence semantics**.

This ADR amends the section as follows:

1. Pulse MAY represent or project regulatory lifecycle states.
2. When canonical Regulations state exists, Pulse SHALL treat Regulations as authoritative for the Baobab representation of that state.
3. Pulse SHALL NOT independently promote PROPOSED or PUBLISHED material into EFFECTIVE obligation for operational use.
4. A directly observed state without Regulations confirmation SHALL be labelled as source-observed/candidate, not canonical.
5. Legal-time applicability belongs to Regulations.

### 9.2 External Data Authority — retained and strengthened

The original rule remains correct:

> Pulse does not become authoritative for an external fact merely because it stores a canonicalised representation.

For regulatory information, add:

~~~text
external legal authority
       ↓
Regulations canonical regulatory meaning
       ↓
Pulse analytical observation
~~~

Pulse owns the analytical observation, not the upstream regulatory authority.

### 9.3 Derived Authority — retained

Pulse remains authoritative for:

- Insight;
- Risk;
- Opportunity;
- Forecast;
- Recommendation;
- analytical Claim;
- intelligence product;
- analytical EvidenceSet.

These may derive from Regulations or Trade Docs facts.

### 9.4 Evidence Boundary — retained

Consequential Pulse intelligence still requires traceable evidence.

However, a Pulse Evidence entry referencing a RegulatoryDecision or TradeDocumentVersion does not make Pulse the canonical owner of the referenced object.

---

## 10. Reconciliation of ADR-PULSE-003

ADR-PULSE-003 remains foundational for the Pulse Source Fabric.

Its general architecture is retained.

### 10.1 Source Registry — retained with domain limit

Pulse Source Registry owns **Pulse acquisition semantics**:

- how Pulse reaches a source;
- licensing;
- refresh policy;
- commercial-use rights;
- research reliability;
- adapter configuration;
- source health;
- research provenance.

It does not replace the Regulations Regulatory Source Registry.

~~~text
Pulse Source Registry
    = research / intelligence acquisition

Regulations Source Registry
    = regulatory authority / legal-source governance
~~~

The same external publisher MAY appear in both registries for different purposes.

### 10.2 SourceDocument — retained as analytical artefact

Pulse SourceDocument remains valid for:

- reports;
- publications;
- web pages;
- PDFs;
- market studies;
- public datasets;
- candidate regulatory publications.

It SHALL NOT become a substitute for:

- RegulatoryInstrument;
- Provision;
- TradeDocument;
- DocumentVersion.

### 10.3 Raw Evidence Vault — retained

Pulse's Raw Evidence Vault remains part of research reproducibility.

Its meaning is now:

> raw evidence acquired by Pulse for Pulse purposes.

It is not:

> the platform-wide universal document or regulatory artefact store.

### 10.4 Physical reuse does not imply domain reuse

Infrastructure MAY deduplicate identical bytes or use common storage technology.

But:

~~~text
same bytes
   ≠
same logical aggregate
   ≠
same authority
   ≠
same retention purpose
~~~

### 10.5 Trade Classification — retained as observation semantics

The original requirement to preserve:

- classification system;
- classification revision;
- commodity code;
- reporter;
- partner;
- flow;
- period;

remains correct for trade datasets.

Example:

~~~text
UN Comtrade observation:
HS 2022 / 0901.11
trade value = X

        ≠

Regulations:
For shipment S under legal context C,
classification = 0901.11
~~~

Pulse records what a source dataset says.

Regulations decides applicable regulatory classification for a governed context.

### 10.6 Regulation-to-Opportunity Pipeline — retained and redirected

The pipeline becomes:

~~~mermaid
flowchart LR
    REG[Regulations RegulatoryChange] --> POBS[Pulse Observation]
    POBS --> X1[Market Data]
    POBS --> X2[Trade Data]
    POBS --> X3[Internal Commercial Data]
    X1 --> A[Pulse Analysis]
    X2 --> A
    X3 --> A
    POBS --> A
    A --> O[Opportunity / Risk]
    O --> R[Recommendation]
~~~

Pulse SHOULD prefer canonical RegulatoryChange references where available.

### 10.7 Regulatory Delta — amended

The old form:

~~~text
OLD RULE
   ↓
CHANGE
   ↓
NEW RULE
~~~

remains a useful analytical model.

But the canonical legal/regulatory delta belongs to Regulations.

Pulse's RegulatoryDelta becomes an analytical projection or analysis of a Regulations change.

### 10.8 Regulatory Impact Mapping — retained

Mapping a regulatory change to:

- countries;
- markets;
- sectors;
- commodities;
- products;
- companies;
- supply chains;

is quintessential Pulse work.

Regulations owns whether the rule applies.

Pulse owns analysis of likely commercial consequence beyond that normative determination.

---

## 11. Reconciliation of ADR-PULSE-004

### 11.1 General evidence architecture — retained

The five evidence layers remain valid for Pulse research:

~~~text
L0 Source Artefact
L1 Raw Record
L2 Normalised Record
L3 Canonical Observation
L4 Derived Evidence
~~~

They describe Pulse's analytical transformation chain.

They do not redefine Regulations or Trade Docs objects.

### 11.2 Regulatory Evidence — amended

The original requirement to distinguish:

- publication time;
- adoption time;
- effective time;
- supersession / repeal;

remains mandatory for Pulse research involving regulation.

But Pulse SHOULD obtain canonical regulatory temporal semantics from Regulations when available.

If only a directly observed external source exists, Pulse SHALL identify those dates as source-observed values rather than authoritative Baobab regulatory state.

### 11.3 Regulatory Reproducibility — retained

The principle remains fully valid:

> A report produced before a regulation became effective must not later appear to have known it was already effective.

The authoritative replay chain SHOULD be:

~~~text
Pulse publication snapshot
       │
       ├── Regulations object version/reference used at publication time
       ├── source artefacts used independently by Pulse
       ├── analytical method version
       └── Pulse EvidenceSet version
~~~

### 11.4 Historical freeze

If Pulse published intelligence based on Regulations decision version R1:

~~~text
R1 at publication time
        ↓
Pulse report v1
~~~

and Regulations later produces R2:

~~~text
R2 current state
~~~

Pulse SHALL NOT rewrite report v1 to pretend R2 was known originally.

---

## 12. Reconciliation of ADR-PULSE-005

ADR-PULSE-005 remains the canonical Pulse observation architecture.

The following domain profiles are narrowed.

### 12.1 Customs Profile

Pulse may observe:

- declaration references;
- clearance events;
- duty amounts;
- customs office;
- procedure;
- origin/destination;
- transport mode;
- source-reported HS classification;
- authority-response timing.

But ownership depends on the fact:

| Fact | Pulse treatment | Canonical owner |
|---|---|---|
| Dataset says HS code X | Observation | Source remains origin; Pulse owns observation |
| Transaction classification is X | Reference / analysis input | Regulations |
| Declaration submitted | Observation | Trade Docs / customs workflow owner |
| Customs authority released shipment | Observation | External customs authority; Trade Docs preserves Baobab record |
| Shipment held operationally | Observation | Trade/TMS/other PEP |
| Delay risk is increasing | Pulse Insight/Risk | Pulse |

### 12.2 Tariff Profile

Pulse MAY preserve tariff observations for intelligence and historical analysis.

For transaction-specific tariff applicability:

~~~text
Pulse tariff observation
        ≠
Regulatory tariff decision
~~~

Operationally consequential tariff applicability SHALL come from Regulations or another explicitly authoritative regulatory capability.

### 12.3 Preferential Eligibility — amended

Pulse may analyse the economic effect of preferential regimes.

Pulse SHALL NOT determine canonical preferential eligibility for a transaction.

Rules of origin, documentary requirements, quota status and legal-time applicability belong to Regulations.

### 12.4 Regulatory Profile — retained as intelligence projection

The Regulatory Profile may continue to include fields such as:

- jurisdiction;
- authority;
- instrument reference;
- subject;
- affected sectors/products;
- publication date;
- effective date;
- expiry/repeal;
- legal status.

When the observation is Regulations-backed, these SHOULD be projections from canonical references.

When source-observed only, the object SHALL remain candidate/non-canonical.

### 12.5 Regulatory Lifecycle — amended

Pulse may query and display lifecycle concepts.

It SHALL NOT maintain an independent canonical state machine that can contradict Regulations.

### 12.6 Regulatory Delta — amended

Pulse MAY maintain a derived analytical RegulatoryDelta if it:

- references the canonical Regulations change where available;
- clearly identifies analytical derivation;
- does not duplicate canonical legal rule versions.

### 12.7 Regulatory Applicability — superseded in part

The old statement that applicability may depend on jurisdiction, product, company type, transaction, origin, destination and threshold remains factually useful.

But the authority changes:

~~~text
Pulse may know applicability factors.

Pulse does not decide canonical applicability.
~~~

Canonical applicability belongs to Regulations.

Pulse MAY ask:

> What commercial effect follows if Regulations says this rule applies?

---

## 13. Reconciliation of ADR-PULSE-006

### 13.1 Provenance graph remains central

Pulse's Evidence Graph remains a core differentiator.

Cross-engine references now appear as external canonical nodes.

~~~mermaid
flowchart LR
    RD[Regulations RegulatoryDecision] --> E[Pulse Evidence]
    TD[Trade Docs DocumentVersion] --> E
    SO[Pulse SourceArtefact] --> E
    E --> ES[EvidenceSet]
    ES --> A[Analysis]
    A --> I[Insight]
    I --> R[Risk / Opportunity]
    R --> REC[Recommendation]
~~~

### 13.2 Regulatory Lineage — amended

The original Pulse lineage:

~~~text
prior instrument
new instrument
amendment
affected provisions
~~~

SHALL NOT require Pulse to mint canonical instrument/provision objects.

Preferred form:

~~~text
Regulations InstrumentReference
        ↓
Regulations ChangeReference
        ↓
Pulse ExternalNode / EvidenceReference
        ↓
Pulse Analysis
~~~

### 13.3 External nodes

Pulse's provenance graph MAY include references to:

- Regulations objects;
- Trade Docs objects;
- Trade objects;
- ERP facts;
- CMS content;
- Control Plane entities.

An external node is not copied domain ownership.

### 13.4 Broken reference handling

If an owner engine becomes unavailable, Pulse SHOULD preserve:

- canonical object identifier;
- owner engine;
- version/revision if known;
- event payload or bounded snapshot used;
- time resolved;
- integrity metadata where available.

It SHALL NOT silently replace the missing canonical object with a locally invented equivalent.

---

## 14. Reconciliation of ADR-PULSE-009

### 14.1 Source Authority — retained for research quality

Pulse may assess source authority as one dimension of research quality.

But:

~~~text
Pulse source-authority score
        ≠
Regulations legal-authority determination
~~~

Pulse quality models SHALL NOT override a Regulations source classification.

### 14.2 Legal Authority — retained with ownership clarification

The existing distinction between legal authority and empirical accuracy remains excellent.

Example:

~~~text
Government gazette:
high legal authority for promulgation

Business survey:
possibly better evidence of compliance behaviour
~~~

Pulse may use both.

Regulations governs the canonical legal-source relationship.

Pulse governs fitness of evidence for an analytical claim.

### 14.3 Confidence cannot alter law

A Pulse confidence score SHALL NOT:

- make a proposed rule effective;
- make an unauthoritative source legally authoritative;
- override a RegulatoryDecision;
- convert INDETERMINATE into SATISFIED;
- validate a TradeDocument.

Likewise, low Pulse confidence does not revoke legal authority.

---

## 15. Trade Documents as Pulse Evidence

Pulse MAY reference a TradeDocument or DocumentVersion as analytical evidence.

Hard invariant:

~~~text
TradeDocument
    !=
Pulse Evidence
~~~

The relationship is:

~~~text
TradeDocumentVersion
        ↓ referenced by
Pulse Evidence
        ↓ contextualised in
EvidenceSet
        ↓ supports
Analysis / Claim / Insight
~~~

Pulse Evidence adds analytical context such as:

- why the document matters to the research question;
- relevance;
- direction;
- quality;
- temporal validity;
- claim relationship.

It does not replace the document.

---

## 16. Documentary Content Access

Pulse SHOULD prefer metadata/reference consumption when content is not required.

If research requires document content:

1. authorisation SHALL be checked at the owner boundary;
2. source rights and data classification SHALL be preserved;
3. Pulse MAY create a lawful analytical snapshot or extracted representation;
4. the snapshot SHALL retain the Trade Docs reference and version;
5. Pulse SHALL NOT silently turn the snapshot into a canonical TradeDocument.

~~~mermaid
flowchart TD
    T[Trade Docs DocumentVersion] --> A{Pulse authorised to access content?}
    A -->|No| M[Use permitted metadata/reference only]
    A -->|Yes| R{Research needs content?}
    R -->|No| M
    R -->|Yes| S[Create rights-aware analytical snapshot]
    S --> P[Preserve owner + version + provenance]
    P --> E[Use in Pulse EvidenceSet]
~~~

---

## 17. Regulations as Pulse Evidence

A RegulatoryDecision, RegulatoryChange or canonical Regulations object MAY support Pulse analysis.

Example:

~~~text
Regulations:
Import restriction effective 2027-01-01
        ↓
Pulse Evidence
        +
Trade statistics
        +
supplier data
        ↓
Pulse Analysis
        ↓
Opportunity:
domestic substitution may become commercially attractive
~~~

The Opportunity is Pulse-owned.

The restriction remains Regulations-owned.

---

## 18. Source Discovery Handoff to Regulations

Pulse has broad source-discovery capabilities and may discover relevant regulatory material first.

The target handoff is:

~~~mermaid
sequenceDiagram
    participant S as External Source
    participant P as Baobab Pulse
    participant R as Baobab Regulations

    S->>P: publication / notice / gazette discovered
    P->>P: preserve source artefact where lawful
    P->>P: classify as candidate regulatory observation
    P-->>R: governed candidate-source reference
    R->>R: verify authority, rights, temporal status
    R->>R: interpret / govern / promote
    R-->>P: canonical RegulatoryChange / reference
    P->>P: reconcile analytical observation
    P->>P: analyse commercial consequences
~~~

Until Regulations returns canonical state, Pulse SHALL not treat the candidate as an operational obligation.

---

## 19. Regulations-First Change Flow

Where Regulations discovers and governs the change first:

~~~mermaid
sequenceDiagram
    participant A as Legal Authority
    participant R as Baobab Regulations
    participant P as Baobab Pulse
    participant B as Business Decision Authority

    A->>R: authoritative publication
    R->>R: acquire, verify, interpret, promote
    R-->>P: RegulatoryChange fact/reference
    P->>P: correlate market + trade + internal evidence
    P->>P: create Risk / Opportunity / Forecast
    P-->>B: Recommendation
    B->>B: authorised decision
~~~

Pulse is downstream of canonical regulatory meaning, not a competing interpreter.

---

## 20. Document-Dependent Regulatory Flow

~~~mermaid
sequenceDiagram
    participant T as Trade / TMS
    participant R as Regulations
    participant D as Trade Docs
    participant P as Pulse

    T->>R: regulatory assessment request
    R-->>D: DocumentRequirement reference
    D->>D: obtain / verify / version document
    D-->>R: documentary facts / evidence references
    R->>R: evaluate requirement satisfaction
    R-->>T: RegulatoryDecision
    R-->>P: decision/change fact
    D-->>P: document/customs lifecycle fact
    P->>P: analyse delay, risk, opportunity
~~~

Pulse SHALL NOT sit between D and R on this critical path.

---

## 21. Critical-Path Rule

Pulse SHALL NOT be a mandatory synchronous dependency for:

- regulatory applicability;
- regulatory classification;
- obligation determination;
- document requirement determination;
- regulatory evidence satisfaction;
- customs submission;
- customs authority response processing;
- shipment compliance enforcement.

~~~text
CORRECT

Trade / TMS
    ↓
Regulations
    ↔ Trade Docs
    ↓
PEP

Pulse observes asynchronously.


INCORRECT

Trade / TMS
    ↓
Pulse AI / vector retrieval
    ↓
Regulations
    ↓
Trade Docs
~~~

Research infrastructure failure must not become compliance infrastructure failure.

---

## 22. Data Model Consequences

### 22.1 Keep DataDomain.REGULATORY

Pulse SHALL keep REGULATORY as a valid intelligence domain.

### 22.2 Keep DataDomain.CUSTOMS

Pulse SHALL keep CUSTOMS as a valid intelligence domain.

### 22.3 Do not add Regulations aggregates to Pulse

Pulse SHALL NOT introduce canonical models named or semantically equivalent to:

- RegulatoryInstrument;
- Provision;
- RegulatoryRule;
- Obligation;
- RegulatoryRequirement;
- RegulatoryAssessment;
- RegulatoryDecision;
- TradeDocument;
- DocumentVersion;
- CustomsCase.

### 22.4 Cross-engine reference fields

Future implementation SHOULD allow Pulse Evidence / Observation lineage to reference owner-engine canonical objects without copying them.

The exact schema follows the Shared RTD cross-engine reference contract.

### 22.5 Existing Evidence.referenced_object direction is correct

Pulse's current Evidence model already follows the intended pattern:

~~~text
Evidence
   └── referenced_object
~~~

The implementation SHOULD evolve that reference to the Shared cross-engine reference contract when RTD-05 lands.

---

## 23. Source and Artefact Ownership Table

| Object / concept | Pulse may own? | Conditions |
|---|---:|---|
| Pulse Source | Yes | Represents intelligence/research acquisition source |
| Pulse DataSource | Yes | Pulse acquisition configuration |
| Pulse SourceArtefact | Yes | Artefact acquired for Pulse analytical purposes |
| Pulse SourceDocument | Yes | Analytical publication representation |
| Pulse Raw Evidence Vault entry | Yes | Pulse research copy; rights-aware |
| Regulations AuthoritativeSource | No | Reference only |
| Regulations SourceArtefact | No | Reference; optional Pulse analytical snapshot if lawful |
| RegulatoryInstrument | No | Reference only |
| RegulatoryDecision | No | Reference only |
| TradeDocument | No | Reference only |
| DocumentVersion | No | Reference only |
| AuthorityResponse | No | Reference / event projection |
| Pulse Observation | Yes | Must preserve upstream authority |
| Pulse Evidence | Yes | Analytical contextualisation |
| Pulse EvidenceSet | Yes | Analytical argument boundary |
| Pulse Insight / Risk / Opportunity | Yes | Derived intelligence |
| Pulse Recommendation | Yes | Non-operational recommendation unless separately authorised |

---

## 24. Regulatory Data Product Semantics

Pulse may continue to commercialise regulatory intelligence.

A regulatory intelligence product SHOULD distinguish:

| Layer | Example | Authority |
|---|---|---|
| Source citation | Gazette notice | External authority |
| Canonical regulatory state | Rule effective from date T | Regulations |
| Pulse observation | RegulatoryChange observed | Pulse projection |
| Pulse analysis | Import costs likely rise | Pulse |
| Pulse risk | Margin compression risk | Pulse |
| Pulse opportunity | Local supplier substitution opportunity | Pulse |
| Pulse recommendation | Investigate domestic sourcing | Pulse |
| Business decision | Change sourcing strategy | Authorised business authority |

A commercial report SHALL not blur these layers.

---

## 25. Regulatory Alert Product

The previously proposed REGULATORY PULSE product remains supported.

A target report structure is:

~~~text
REGULATORY PULSE ALERT

1. What changed?
   → canonical Regulations reference

2. Source and legal status
   → authority / instrument / effective-time references

3. Who or what may be affected?
   → Pulse impact analysis

4. Commercial consequence
   → Pulse Insight / Risk / Opportunity

5. Evidence
   → Regulations refs + Pulse evidence + market evidence

6. Unknowns / uncertainties
   → explicit gaps

7. Recommended next investigation
   → Pulse Recommendation
~~~

This separation increases commercial credibility rather than reducing Pulse's role.

---

## 26. Customs Intelligence Boundary

Customs is a cross-engine concern and SHALL be decomposed by fact type.

~~~mermaid
flowchart TD
    C[Customs-related fact] --> Q{What kind of fact?}

    Q -->|Legal classification / tariff / applicability| R[Regulations]
    Q -->|Document / declaration / authority-response workflow| D[Trade Docs]
    Q -->|Shipment enforcement / operational state| T[Trade / TMS / PEP]
    Q -->|Trend / delay / risk / corridor intelligence| P[Pulse]
    Q -->|Sovereign ruling / release| A[Customs Authority]
~~~

Pulse may correlate all five layers, but owns only its analytical derivatives.

---

## 27. HS Classification Rule

The phrase “HS classification” SHALL always be interpreted in context.

### 27.1 Source-observed classification

Example:

~~~text
Dataset:
HS revision 2022
code 0901.11
reported trade value X
~~~

Pulse may store this as a TradeObservation.

### 27.2 Regulatory classification

Example:

~~~text
Transaction:
product P
origin UG
destination ZA
legal time T
classification decision 0901.11
~~~

This is Regulations territory.

### 27.3 Analytical mapping

Pulse may compare classifications, revisions and concordances for research.

It SHALL not promote an analytical concordance into an operational customs decision.

---

## 28. Tariff and Landed-Cost Intelligence

Pulse may calculate landed-cost scenarios.

For high-consequence or transaction-specific calculations:

~~~text
Regulations
  tariff / preference / eligibility decision
            +
Trade / ERP
  price / quantity / commercial facts
            +
TMS / logistics
  freight facts
            ↓
Pulse
  scenario / forecast / commercial analysis
~~~

Where canonical Regulations coverage is unavailable, Pulse MAY produce an explicitly non-authoritative scenario based on source observations.

It SHALL label the output accordingly.

---

## 29. Evidence Semantics

Pulse Evidence remains analytical evidence.

It may reference:

- a Pulse Observation;
- a Pulse SourceArtefact;
- a Regulations object;
- a Trade Docs object;
- an operational event;
- another authorised canonical object.

The relationship means:

~~~text
this object supports / contradicts / contextualises this analytical claim
~~~

It does not mean:

~~~text
Pulse owns this object
~~~

---

## 30. Evidence Quality Versus Regulatory Authority

Pulse quality dimensions and Regulations authority dimensions are related but distinct.

~~~text
PULSE QUESTION:
Is this evidence fit for this analytical claim?

REGULATIONS QUESTION:
Is this source authoritative for this regulatory purpose?
~~~

An official source can have:

- high legal authority;
- poor timeliness;
- incomplete coverage;
- methodological limitations.

A commercial source can have:

- excellent timeliness;
- strong empirical coverage;
- no legal authority.

Pulse may represent both facts.

---

## 31. Regulatory Contradictions

If Pulse observes contradictory regulatory claims:

~~~text
Source A says X
Source B says Y
~~~

Pulse MAY preserve the contradiction as research evidence.

It SHALL NOT resolve the legal conflict merely by:

- source popularity;
- model confidence;
- vector similarity;
- majority vote;
- generic trust score.

For canonical regulatory resolution, Pulse SHOULD defer to Regulations governance.

---

## 32. Trade Document Contradictions

If Pulse receives conflicting document versions or issuer claims, it SHALL NOT choose a canonical version independently.

~~~text
Pulse detects conflict
       ↓
reference Trade Docs
       ↓
Trade Docs resolves documentary lifecycle / verification state
       ↓
Pulse updates analytical view
~~~

Pulse may still analyse the existence and consequence of the conflict.

---

## 33. Event Directionality

### 33.1 Regulations → Pulse

Pulse may consume:

- RegulatoryChange;
- RegulatoryDecision;
- classification decision;
- assessment result;
- requirement change;
- regulatory coverage update.

### 33.2 Trade Docs → Pulse

Pulse may consume:

- document issued;
- document superseded;
- verification changed;
- submission completed;
- authority response received;
- rejection;
- expiry / revocation;
- customs case state changed.

### 33.3 Pulse → Regulations

Pulse may emit or invoke:

- candidate source discovery;
- research evidence reference;
- assessment request through capability/API;
- analytical context;
- suspected change requiring regulatory review.

It SHALL NOT emit a canonical regulatory decision.

### 33.4 Pulse → Trade Docs

Pulse may emit recommendations or invoke authorised commands.

Default path:

~~~text
Pulse Recommendation
        ↓
authorised human / policy
        ↓
Trade Docs command
~~~

Pulse SHALL not mutate document state merely because an AI agent recommends doing so.

---

## 34. Events Are Facts, Not Commands

Pulse SHALL follow ADR-SHARED-018.

Correct:

~~~text
regulatory change observed
risk identified
opportunity identified
forecast revised
~~~

Incorrect as cross-engine events:

~~~text
trade-docs.create-document
regulations.approve-rule
customs.release-shipment
~~~

Commands belong to governed capability/API boundaries.

---

## 35. Temporal Semantics

Pulse SHALL distinguish at least:

| Time concept | Typical authority |
|---|---|
| source publication time | External source |
| regulatory legal/effective time | Regulations |
| regulatory knowledge/system time | Regulations |
| document issue time | Trade Docs / issuer |
| document version time | Trade Docs |
| submission/response time | Trade Docs / external authority |
| observation time | Pulse |
| acquisition time | Pulse |
| analysis time | Pulse |
| publication time | Pulse |

No one timestamp substitutes for another.

---

## 36. Historical Research Replay

A historically reproducible Pulse product SHOULD capture:

~~~text
ResearchSnapshot
├── Pulse EvidenceSet version
├── Pulse source artefact versions
├── Regulations object ids + versions/revisions
├── Trade Docs document ids + versions
├── method version
├── model version where applicable
├── mapping versions
└── publication timestamp
~~~

Recomputation with current owner state is a different operation from reproducing the historical publication.

---

## 37. Security and Classification

Cross-engine consumption SHALL preserve:

- tenant scope;
- market/context scope;
- data classification;
- source rights;
- retention constraints;
- purpose limitations;
- provenance;
- caller authorisation.

Hard invariant:

~~~text
Pulse knows canonical object id
        ≠
Pulse may access canonical object
~~~

Vector retrieval SHALL not become an authorisation bypass.

---

## 38. AI Boundary

Pulse's Haystack boundary remains unchanged.

Pulse AI MAY:

- discover candidate sources;
- summarise authorised evidence;
- identify possible regulatory impact;
- generate hypotheses;
- assist research;
- draft explanations and recommendations.

Pulse AI SHALL NOT:

- promote a candidate publication to canonical law;
- create a canonical RegulatoryRule;
- decide operational legal applicability;
- certify a TradeDocument;
- claim a customs authority released a shipment without authoritative evidence.

~~~text
AI may reason over references.

AI does not inherit the authority of the referenced object.
~~~

---

## 39. Qdrant Boundary

Qdrant remains a rebuildable Pulse semantic projection.

Cross-engine content placed into Pulse retrieval SHALL be:

- authorised;
- appropriately classified;
- derived from a permitted canonical/snapshot source;
- traceable to owner and version;
- removable/rebuildable.

Qdrant SHALL NOT become a canonical Regulations or Trade Docs store.

---

## 40. No Shared Database Shortcut

This reconciliation explicitly rejects:

~~~text
Pulse querying Regulations PostgreSQL
Pulse querying Trade Docs PostgreSQL
Regulations querying Pulse PostgreSQL
Trade Docs querying Pulse PostgreSQL
~~~

Integration uses:

- capability resolution;
- APIs;
- events;
- approved projections;
- cross-engine references.

---

## 41. Operational Failure Model

### 41.1 Regulations unavailable

Pulse MAY continue unrelated intelligence work.

For an analysis requiring current regulatory truth, Pulse SHALL:

- use an explicitly valid cached/versioned reference if policy permits; or
- mark the regulatory component unavailable/stale; or
- produce a scenario with a clear non-authoritative caveat.

It SHALL NOT invent a replacement decision.

### 41.2 Trade Docs unavailable

Pulse MAY analyse previously captured documentary events/references.

It SHALL NOT claim current document state if freshness cannot be established.

### 41.3 Pulse unavailable

Regulations and Trade Docs SHALL continue their critical regulatory/documentary functions.

This is a core architectural success condition.

---

## 42. Staleness Model

A cross-engine reference may become stale because:

- Regulations superseded a decision;
- a rule changed;
- a legal effective date passed;
- Trade Docs superseded a document version;
- issuer verification changed;
- a document expired or was revoked;
- material transaction context changed.

Pulse SHALL distinguish:

~~~text
historically valid reference
        ≠
currently applicable reference
~~~

---

## 43. Reconciliation Matrix for Existing ADR Sections

| Existing ADR section | Disposition | Reconciled meaning |
|---|---|---|
| PULSE-001 Regulatory Boundary | **Amended** | Pulse represents regulatory states; Regulations owns canonical state/applicability |
| PULSE-001 External Data Authority | Retained | Strengthened by explicit Regulations/Trade Docs ownership |
| PULSE-001 Derived Authority | Retained | Pulse still owns intelligence derivatives |
| PULSE-001 Evidence Boundary | Retained | Evidence may reference foreign canonical objects |
| PULSE-003 Source Registry | **Narrowed** | Pulse research acquisition registry only |
| PULSE-003 SourceDocument | **Narrowed** | Analytical source document, not RegulatoryInstrument/TradeDocument |
| PULSE-003 Raw Evidence Vault | Retained | Pulse research vault, not universal platform store |
| PULSE-003 Trade Classification | Retained | Source-observed trade classification |
| PULSE-003 Regulation-to-Opportunity | Retained | Prefer Regulations-backed change |
| PULSE-003 Regulatory Delta | **Amended** | Analytical projection; canonical change belongs to Regulations |
| PULSE-003 Regulatory Impact | Retained | Core Pulse analysis |
| PULSE-004 Regulatory Evidence | **Amended** | Canonical legal-time semantics preferably from Regulations |
| PULSE-004 Regulatory Reproducibility | Retained | Versioned Regulations refs used in historical replay |
| PULSE-005 Customs Profile | **Amended** | Observational; ownership split by fact type |
| PULSE-005 Tariff Profile | **Amended** | Observational; transaction applicability belongs to Regulations |
| PULSE-005 Preferential Eligibility | **Superseded in part** | Pulse analyses effect; Regulations decides eligibility |
| PULSE-005 Regulatory Profile | **Amended** | Projection/candidate observation, not canonical regulatory model |
| PULSE-005 Regulatory Lifecycle | **Amended** | Regulations-backed or candidate-labelled |
| PULSE-005 Regulatory Delta | **Amended** | Derived intelligence referencing canonical change |
| PULSE-005 Regulatory Applicability | **Superseded in part** | Pulse knows factors; Regulations decides applicability |
| PULSE-006 Regulatory Lineage | **Amended** | Use external canonical Regulations nodes |
| PULSE-009 Source Authority | Retained | Research authority dimension |
| PULSE-009 Legal Authority | Retained | Does not replace Regulations authority model |

---

## 44. What This ADR Does Not Change

This ADR does **not** weaken:

- Pulse's research mission;
- Source / DataSource bounded context;
- generic ingestion adapters;
- Raw Evidence Vault;
- evidence immutability;
- EvidenceSet;
- provenance graph;
- claim/citation architecture;
- research reproducibility;
- opportunity/risk/forecast/recommendation models;
- Haystack anti-corruption boundary;
- Qdrant projection architecture;
- tenancy;
- classification;
- model replaceability.

Those remain core Pulse architecture.

---

## 45. What This ADR Explicitly Removes from Pulse Authority

Pulse no longer claims canonical authority over:

~~~text
RegulatoryInstrument
Provision
RegulatoryRule
RegulatoryRequirement
RegulatoryApplicability
RegulatoryAssessment
RegulatoryDecision

TradeDocument
DocumentVersion
DocumentVerification authoritative workflow state
Customs document submission workflow
AuthorityResponse canonical record
~~~

Pulse may reference and analyse these objects.

---

## 46. Implementation Implications

RTD-02 is primarily an architecture change.

Runtime implementation SHOULD follow later contract work.

### 46.1 Immediate repository requirements

- Add this ADR.
- Update repository documentation to list ADR-PULSE-012.
- Do not remove REGULATORY or CUSTOMS enums.
- Do not add premature local copies of future Shared cross-engine contracts.

### 46.2 After Shared RTD-05 / RTD-06

Pulse SHOULD:

- adopt canonical cross-engine object references;
- extend Evidence/research lineage to use them;
- consume Regulations event/API contracts;
- consume Trade Docs event/API contracts;
- add candidate regulatory source handoff;
- add staleness/reconciliation semantics;
- add conformance tests.

### 46.3 Architecture tests

Future tests SHOULD mechanically prevent imports or domain models that imply Pulse owns Regulations or Trade Docs aggregates.

---

## 47. Target Package Boundary

~~~text
baobab_pulse.domain
├── observations
├── evidence
├── analysis
├── insights
├── risks
├── opportunities
├── forecasting
├── recommendations
└── research

allowed:
    cross-engine reference value objects / ports

forbidden:
    baobab_regulations domain imports
    baobab_trade_docs domain imports
    vendor SDK types
    direct database adapters to foreign engines
~~~

The anti-corruption principle applies to Baobab engines just as it applies to vendors.

---

## 48. Candidate Future Ports

Conceptually, Pulse may later expose application ports such as:

~~~text
RegulatoryContextPort
    resolve_change(reference)
    resolve_decision(reference)
    submit_candidate_source(...)

TradeDocumentEvidencePort
    resolve_document_version(reference)
    resolve_document_metadata(reference)

CrossEngineReferenceResolver
    resolve(reference, context)
~~~

These are conceptual examples.

They SHALL be implemented only after Shared contracts define the canonical wire shapes.

---

## 49. Example — Coffee Import Regulation

~~~mermaid
flowchart TD
    L[Regulator publishes new coffee import requirement] --> R[Regulations]
    R --> RC[Canonical RegulatoryChange]
    RC --> PR[Pulse reference]
    PR --> M[Market / trade / supplier evidence]
    M --> A[Pulse Analysis]
    PR --> A
    A --> K[Risk: import delay]
    A --> O[Opportunity: local processing]
    K --> REC[Recommendation]
    O --> REC
~~~

Pulse's commercial value increases because it can build on governed regulatory meaning rather than reproduce legal interpretation itself.

---

## 50. Example — Source-Observed Gazette Before Regulations Promotion

~~~text
10:00 Pulse crawler discovers gazette PDF
10:01 Pulse hashes and preserves lawful source artefact
10:02 Pulse creates candidate regulatory observation
10:03 Pulse alerts Regulations source-acquisition boundary
10:10 Regulations verifies issuer/publication mechanism
10:30 Regulations promotes RegulatoryChange
10:31 Pulse links candidate observation to canonical reference
10:32 Pulse runs impact analysis
~~~

At 10:05 Pulse may say:

> A publication appears to announce change X.

It may not say:

> Change X is canonically effective and transaction T is legally bound.

---

## 51. Example — Trade Document Rejection Intelligence

~~~text
Trade Docs:
phytosanitary certificate rejected
        ↓
Pulse:
observe rejection event
        +
corridor history
        +
supplier history
        ↓
Analysis:
supplier S has elevated documentary rejection rate
        ↓
Risk:
shipment delay risk HIGH
~~~

Pulse owns the risk.

Trade Docs owns the document/rejection record.

Regulations owns whether the missing/invalid certificate makes the regulatory requirement unsatisfied.

---

## 52. Example — HS Code Analytics

~~~text
Pulse:
2019 dataset uses HS 2017 code A
2024 dataset uses HS 2022 code B
        ↓
classification concordance
        ↓
comparable historical series
~~~

This is legitimate analytical mapping.

It does not authorise:

~~~text
Shipment 123 must be declared under code B.
~~~

That decision belongs to Regulations.

---

## 53. Example — Regulatory Scenario Without Coverage

Where Regulations does not yet support a jurisdiction:

Pulse MAY produce:

~~~text
SCENARIO / RESEARCH ONLY

Based on source S,
if tariff rate R applies,
estimated landed cost becomes X.
~~~

The output MUST remain distinguishable from:

~~~text
REGULATORY DECISION

For transaction T,
rate R applies.
~~~

---

## 54. Platform Invariants

The following invariants SHALL guide implementation and later automated tests.

~~~text
INV-PULSE-RTD-001
REGULATORY and CUSTOMS remain valid Pulse intelligence domains.

INV-PULSE-RTD-002
Pulse does not mint canonical RegulatoryDecision objects.

INV-PULSE-RTD-003
Pulse does not mint canonical TradeDocument or DocumentVersion objects.

INV-PULSE-RTD-004
A Pulse RegulatoryObservation is either candidate/source-observed
or backed by a canonical Regulations reference.

INV-PULSE-RTD-005
Pulse never converts a candidate regulatory observation into an
operational obligation without the Regulations boundary.

INV-PULSE-RTD-006
Source-observed HS classification is distinct from a governed
transaction classification.

INV-PULSE-RTD-007
Pulse regulatory deltas do not replace canonical Regulations changes.

INV-PULSE-RTD-008
Pulse Evidence may reference foreign canonical objects without
copying their ownership.

INV-PULSE-RTD-009
Pulse's Raw Evidence Vault is a Pulse research boundary, not the
universal Baobab evidence/document store.

INV-PULSE-RTD-010
Pulse source-quality or confidence scores do not alter legal authority.

INV-PULSE-RTD-011
Pulse is not a synchronous dependency of regulatory/customs enforcement.

INV-PULSE-RTD-012
No direct database access to Regulations or Trade Docs is permitted.

INV-PULSE-RTD-013
Historical Pulse publications retain the cross-engine versions/references
used when published.

INV-PULSE-RTD-014
Document verification does not imply regulatory requirement satisfaction.

INV-PULSE-RTD-015
Cross-engine references retain owner identity and version/revision
where required for replay.

INV-PULSE-RTD-016
Qdrant contains only rebuildable Pulse projections, never canonical
Regulations or Trade Docs state.

INV-PULSE-RTD-017
Pulse AI may propose, discover and analyse; it does not manufacture
regulatory or documentary authority.

INV-PULSE-RTD-018
Regulatory intelligence products explicitly separate canonical regulatory
facts from Pulse analytical conclusions.
~~~

---

## 55. Migration Strategy

No destructive data migration is required by this ADR because no production regulatory intelligence domain has yet been implemented in Pulse.

The migration is primarily semantic and architectural.

~~~mermaid
flowchart LR
    A[Existing Pulse ADR semantics] --> B[ADR-PULSE-012 reconciliation]
    B --> C[Shared cross-engine reference contract]
    C --> D[Regulations / Trade Docs event contracts]
    D --> E[Pulse adapters and projections]
    E --> F[Architecture + contract tests]
    F --> G[Production regulatory intelligence]
~~~

This timing is advantageous: the boundary can be corrected before production data makes ambiguity expensive.

---

## 56. Follow-Up Work

| Step | Work | Dependency |
|---|---|---|
| PRTD-01 | Add ADR-PULSE-012 | This decision |
| PRTD-02 | Update README / architecture documentation | PRTD-01 |
| PRTD-03 | Consume Shared cross-engine object reference | RTD-05 |
| PRTD-04 | Add Regulations adapter/port | RTD-06/08 |
| PRTD-05 | Add Trade Docs adapter/port | RTD-04/06/07 |
| PRTD-06 | Implement candidate regulatory-source handoff | Regulations contract available |
| PRTD-07 | Add owner/version-aware Evidence lineage | RTD-05 |
| PRTD-08 | Add staleness and reconciliation tests | PRTD-03..07 |
| PRTD-09 | Add cross-repo conformance tests | Shared contracts active |
| PRTD-10 | Activate first regulatory intelligence product | All relevant gates green |

---

## 57. Rejected Alternatives

### A. Remove REGULATORY and CUSTOMS from Pulse

Rejected.

Pulse still needs to analyse regulatory and customs facts. Removing the domains would confuse authority separation with analytical blindness.

### B. Keep the original Pulse regulatory model unchanged

Rejected.

It would create competing regulatory state, applicability and classification semantics beside Baobab Regulations.

### C. Make Pulse the shared evidence platform for Regulations and Trade Docs

Rejected.

Pulse evidence is analytical evidence. Shared infrastructure patterns do not imply centralised domain ownership.

### D. Make Regulations the only engine allowed to read regulatory sources

Rejected.

Pulse may legitimately research public regulatory material, detect signals and preserve research artefacts. The restriction is on **canonical regulatory authority**, not source visibility.

### E. Force all regulatory source discovery through Regulations

Rejected.

Pulse's broad research fabric may discover material first. The correct pattern is governed handoff, not architectural censorship.

### F. Make Trade Docs verification equal regulatory compliance

Rejected.

Documentary authenticity/verification and legal requirement satisfaction are distinct questions.

### G. Put Pulse in the synchronous compliance path because it has Haystack

Rejected.

AI/research infrastructure availability must not govern compliance availability.

### H. Share canonical databases to avoid duplicated references

Rejected.

It would erase ownership boundaries and create multi-master semantics.

---

## 58. Consequences

### Positive

- Preserves the substantial existing Pulse ADR investment.
- Clarifies authority without shrinking Pulse's commercial intelligence scope.
- Makes Regulatory Pulse products safer and more defensible.
- Avoids duplicate regulatory/domain models.
- Avoids duplicate TradeDocument models.
- Reuses Pulse's strong EvidenceSet and provenance architecture correctly.
- Creates a clean path for Regulations and Trade Docs integration.
- Keeps Haystack/Qdrant replaceable and off the regulatory critical path.
- Improves auditability and historical replay.
- Establishes concrete future architecture tests.

### Costs

- Some earlier Pulse wording is now explicitly qualified.
- Future adapters must resolve foreign canonical references.
- Regulatory intelligence depends on coverage/freshness signals from Regulations for authoritative claims.
- Some research may need dual provenance: original source plus canonical Regulations reference.
- Cross-repository conformance tests become important.

These are desirable costs of a mature polyrepo platform.

---

## 59. Final Mental Model

~~~text
PULSE DOES NOT BECOME SMALLER.

It becomes more precise.

Before:
Pulse had to model regulation because nobody else did.

After:
Regulations provides governed regulatory meaning.
Trade Docs provides governed documentary state.
Pulse combines those with wider evidence to produce intelligence.
~~~

The enduring architecture is:

~~~mermaid
flowchart TB
    AUTH[External Legal / Customs / Issuer Authority]

    AUTH --> REG[Baobab Regulations
Normative meaning]
    AUTH --> DOC[Baobab Trade Docs
Documentary workflow]

    REG <--> DOC

    REG --> PULSE[Baobab Pulse
Intelligence]
    DOC --> PULSE

    WORLD[Markets / News / Trade Data / Weather / Macro / Internal Engines] --> PULSE

    PULSE --> INS[Insight]
    PULSE --> RISK[Risk]
    PULSE --> OPP[Opportunity]
    PULSE --> FC[Forecast]
    PULSE --> REC[Recommendation]

    REC --> DEC[Authorised Human / Policy Decision]
    DEC --> PEP[Owning Operational Engine]
~~~

---

## 60. Final Decision Statement

Baobab Pulse SHALL remain the platform's **System of Intelligence, Research and Analytical Evidence**.

Its regulatory, customs and trade-document intelligence capabilities SHALL continue, but under the following authority boundary:

> **Pulse may discover, observe, preserve, contextualise, correlate, analyse, forecast and recommend from regulatory and documentary evidence. Baobab Regulations alone owns canonical Baobab regulatory meaning and regulatory decisions. Baobab Trade Docs alone owns canonical trade-document lifecycle and documentary/customs workflow state. Pulse references those authorities; it does not reproduce them.**

This ADR supersedes only the conflicting authority implications of earlier Pulse regulatory/customs/documentary sections. Their general research, evidence, provenance, temporal and analytical principles remain in force.
