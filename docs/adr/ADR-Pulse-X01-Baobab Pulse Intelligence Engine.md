# ADR-Pulse-X01-Baobab Pulse Intelligence Engine  
## Parent Architecture Specification

**Document ID:** `ARCH-PULSE-001`  
**Status:** Proposed  
**Classification:** Baobab Platform Architecture — Parent Implementation Contract  
**Repository:** `nabhold/baobab-pulse`  
**Organisation:** Nabhold  
**Platform:** Baobab Enterprise Platform  
**Engine:** Baobab Pulse  
**Engine Type:** Intelligence and Decision-Support Engine  
**Primary implementation language:** Python 3.14  
**Primary operational datastore:** PostgreSQL 17  
**Architecture style:** Headless, API-first, event-driven, polyglot-platform compatible, multi-tenant, evidence-oriented, temporally aware  
**Related repositories:** `nabhold/shared`, `nabhold/baobab-cp`, `nabhold/baobab-trade`, `nabhold/baobab-erp`, Payload CMS engine repository, `nabhold/infrastructure`, `nabhold/baobab-dev`

---

# 1. Purpose

Baobab Pulse is the **Intelligence Engine of the Baobab Platform**.

Its purpose is to continuously acquire, normalise, preserve, correlate and analyse internal and external information so that Baobab-consuming organisations can understand:

- what is happening;
- what has changed;
- why it may have changed;
- what is likely to happen next;
- where opportunities may exist;
- where risk is accumulating;
- what evidence supports an assessment;
- and which decisions merit human consideration.

Pulse is not an ERP system.

Pulse is not a commerce system.

Pulse is not a content management system.

Pulse is not the Baobab Control Plane.

Pulse is not merely an LLM wrapper.

Pulse is a dedicated **system of intelligence** operating over evidence derived from both Baobab engines and authorised external data sources.

Its defining responsibility is:

> **Transform heterogeneous evidence into traceable, contextualised, time-aware intelligence without becoming the system of record for the operational domains from which that evidence originates.**

---

# 2. Architectural Position

The Baobab Platform contains specialised engines with deliberately different responsibilities.

```text
                         BAOBAB PLATFORM

                      ┌──────────────────┐
                      │  CONTROL PLANE   │
                      │    baobab-cp     │
                      └────────┬─────────┘
                               │
                    Platform Context
                    Identity / Tenancy
                    Markets / Engines
                    Capabilities
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ PAYLOAD CMS  │ │   MEDUSAJS   │ │  IDEMPIERE   │
      │              │ │              │ │              │
      │ Content SoR  │ │ Commerce SoR │ │   ERP SoR    │
      └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                    Events / APIs / Evidence
                               │
                               ▼
                    ┌──────────────────────┐
                    │    BAOBAB PULSE      │
                    │                      │
                    │ System of            │
                    │ Intelligence         │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
             Signals        Insights     Recommendations
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                          Decisions
```

The fundamental relationship is:

```text
Payload CMS   → tells us what is being communicated
MedusaJS      → tells us what is being traded
iDempiere     → tells us what the enterprise is doing
External data → tells us what the world around it is doing
Pulse         → determines what the combined evidence may mean
```

---

# 3. Architectural Classification

Baobab Pulse SHALL be classified as:

```text
Engine:
    type: INTELLIGENCE

Operating model:
    headless

Integration:
    API-first
    event-driven

Data model:
    evidence-centric
    provenance-preserving
    temporal

Tenancy:
    context-aware
    isolation-enforced

Execution:
    synchronous where necessary
    asynchronous by preference

Decision authority:
    advisory by default
    autonomous only under explicit policy
```

---

# 4. Core Architectural Principles

## 4.1 Evidence before inference

No material Pulse conclusion SHALL exist independently of its supporting evidence.

An intelligence product should therefore be representable as:

```text
Evidence
   ↓
Observation
   ↓
Signal
   ↓
Analysis
   ↓
Insight
   ↓
Recommendation
```

Each transformation must remain traceable.

---

## 4.2 Provenance is mandatory

Every externally acquired datum MUST preserve sufficient provenance to establish:

- originating source;
- source organisation;
- source identifier;
- acquisition mechanism;
- source URL or endpoint where applicable;
- publication timestamp;
- observed timestamp;
- retrieval timestamp;
- applicable geography;
- applicable market;
- source version where available;
- content hash;
- licence or usage restrictions;
- transformation history;
- quality assessment;
- downstream derivations.

Pulse SHALL be able to answer:

> “Where did this number come from?”

and:

> “What evidence caused this conclusion?”

---

# 5. Intelligence Scope

Pulse SHALL initially support eleven first-class external intelligence domains.

These are not optional examples. They form the foundational external-data capability model.

| Capability | Primary purpose |
|---|---|
| FX | Currency movements, exposure and conversion context |
| Commodity Prices | Commodity benchmarks and input/output economics |
| Weather | Agricultural, infrastructure and logistics effects |
| Trade Statistics | Bilateral and multilateral flow analysis |
| Customs Data | Import/export movement and border intelligence |
| Macroeconomic Indicators | Economic conditions and structural trends |
| Market Prices | Local and international price discovery |
| Company Registries | Counterparty and market-structure intelligence |
| Geospatial Data | Location, distance, infrastructure and spatial risk |
| Government Open Data | Public-sector statistics and administrative evidence |
| News | Current events and emerging signals |
| Regulatory Changes | Legal, policy, tariff and compliance change |

The architecture MUST allow additional domains without redesigning the core intelligence model.

---

# 6. External Intelligence Capability Architecture

```text
                    EXTERNAL WORLD

 ┌────────┬────────┬────────┬────────┬────────────┐
 │   FX   │Weather │ Trade  │Customs │ Commodities│
 └───┬────┴───┬────┴───┬────┴───┬────┴─────┬──────┘
     │        │        │        │          │
 ┌───┴────┬───┴────┬───┴────┬───┴──────┬───┴────┐
 │ Macro  │ Market │Company │Gov Open  │Regulatory│
 │ Data   │ Prices │Registry│Data      │ Changes  │
 └────┬───┴────┬───┴────┬───┴────┬────┴────┬─────┘
      │        │        │        │         │
      │                 NEWS                │
      └──────────────────┬──────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ SOURCE ADAPTERS  │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ RAW ACQUISITION  │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ NORMALISATION    │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ VALIDATION       │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ PROVENANCE       │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ OBSERVATIONS     │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │ INTELLIGENCE     │
                └──────────────────┘
```

---

# 7. FX Intelligence

Pulse SHALL support foreign-exchange information as a first-class temporal dataset.

FX information may include:

- spot rates;
- reference rates;
- closing rates;
- indicative rates;
- bid/ask observations;
- cross rates;
- historical series;
- volatility;
- rate-of-change;
- currency indexes;
- central-bank rates where relevant.

The canonical observation SHOULD support:

```text
base_currency
quote_currency
rate
rate_type
provider
observed_at
published_at
retrieved_at
market
source
```

Pulse MUST distinguish between:

```text
USD/ZAR at 10:00
```

and:

```text
USD/ZAR official daily reference rate
```

They are different observations even if numerically similar.

---

# 8. Commodity Intelligence

Commodity data may include:

- coffee;
- cocoa;
- crude oil;
- natural gas;
- metals;
- grains;
- fertiliser;
- timber;
- livestock;
- agricultural inputs;
- renewable-energy inputs;
- other strategically relevant commodities.

Commodity observations SHALL encode:

```text
commodity
grade
contract
exchange
delivery_location
unit
currency
price
observation_time
source
```

For agricultural commodities, quality classifications are significant.

For example:

```text
Coffee
 ├── Arabica
 │    ├── exchange benchmark
 │    ├── origin
 │    ├── grade
 │    └── differential
 │
 └── Robusta
      ├── exchange benchmark
      ├── origin
      ├── grade
      └── differential
```

Pulse MUST NOT incorrectly collapse materially different grades or benchmarks into one commodity price.

---

# 9. Weather Intelligence

Weather information SHALL support:

- historical observations;
- forecasts;
- rainfall;
- temperature;
- humidity;
- drought;
- wind;
- storms;
- frost;
- soil moisture where available;
- extreme weather events;
- climate anomalies.

Weather information becomes particularly important when correlated with:

```text
weather
   +
crop region
   +
commodity
   +
harvest calendar
   ↓
potential supply signal
```

Weather forecasts MUST remain distinguishable from measured weather observations.

A forecast SHALL NOT silently become historical fact after its forecast date passes.

---

# 10. Trade Statistics

Pulse SHALL ingest structured trade statistics capable of supporting analysis by:

```text
reporter country
partner country
commodity
HS classification
period
trade flow
quantity
net weight
trade value
currency
transport mode
customs procedure
```

International merchandise trade will require explicit handling of commodity-classification versions.

For example:

```text
HS1992
HS1996
HS2002
HS2007
HS2012
HS2017
HS2022
```

Pulse MUST NOT assume that a code is semantically identical across classification revisions.

Trade statistics should make analyses such as the following possible:

```text
Uganda
   │
   ├── exports coffee
   │
   ▼
South Africa
   │
   ├── imports coffee
   │
   ▼
Observed market gap
```

or:

```text
South African imports
        ↓
origin concentration
        ↓
supplier risk
```

The engine must support bilateral, regional and global comparisons.

---

# 11. Customs Intelligence

Customs information is related to but distinct from aggregate trade statistics.

Potential information includes:

- declarations;
- tariffs;
- HS codes;
- duties;
- ports;
- border posts;
- origin;
- destination;
- importer/exporter information where legally available;
- shipment quantities;
- customs valuation;
- declaration dates;
- clearance dates;
- customs procedures.

Pulse SHALL model source-specific legal and confidentiality restrictions.

Access to commercially sensitive customs information MUST be policy-controlled.

---

# 12. Macroeconomic Intelligence

Macroeconomic datasets SHOULD include:

- GDP;
- GDP growth;
- inflation;
- interest rates;
- unemployment;
- government debt;
- current account;
- exchange reserves;
- population;
- income;
- industrial production;
- agricultural production;
- money supply;
- purchasing power;
- business-confidence indicators;
- consumer-confidence indicators.

Sources may include official institutions and international organisations.

For example, the World Bank Indicators API provides programmatic access to thousands of time-series indicators, while IMF data is available through SDMX APIs.

Pulse SHALL preserve the original indicator definitions.

An indicator name such as:

```text
GDP growth
```

is insufficient without:

```text
provider
indicator_code
methodology
unit
frequency
adjustment
geography
release
```

---

# 13. Market Prices

Market-price intelligence SHOULD support information that does not necessarily qualify as formal exchange or commodity-benchmark data.

Examples include:

- wholesale agricultural prices;
- retail prices;
- fuel prices;
- property prices;
- freight rates;
- shipping rates;
- warehouse prices;
- input costs;
- equipment prices;
- electricity prices.

Market observations SHOULD support:

```text
product/service
market
location
currency
unit
price
quantity basis
provider
observed_at
```

This enables analysis such as:

```text
international benchmark
        vs
local wholesale price
        vs
import landed cost
        ↓
commercial opportunity
```

---

# 14. Company Registry Intelligence

Company registry information SHALL be treated primarily as **entity intelligence**.

Potential fields include:

```text
registered_name
registration_number
jurisdiction
entity_type
incorporation_date
status
registered_address
directors
officers
beneficial ownership
industry
filing status
```

Availability varies substantially between jurisdictions.

Pulse MUST therefore model:

```text
data availability
confidence
legal restriction
source authority
last verified
```

rather than assuming uniform registry completeness.

Registry entities SHALL be mapped, when appropriate, to Baobab canonical entities using `ExternalReference` and mapping mechanisms governed through `nabhold/shared` and the Control Plane.

---

# 15. Geospatial Intelligence

Pulse SHALL treat location as more than a text field.

Geospatial capability may represent:

- countries;
- regions;
- administrative boundaries;
- farms;
- ports;
- roads;
- border posts;
- warehouses;
- markets;
- factories;
- mines;
- infrastructure;
- rainfall zones;
- agricultural zones;
- transport corridors.

Spatial questions should eventually include:

```text
What coffee-growing areas
are within 200 km
of this logistics corridor?
```

or:

```text
Which border disruptions
could affect this supply route?
```

The geospatial capability SHOULD support PostgreSQL spatial extensions where justified, without making the extension mandatory for the first ingestion implementation.

---

# 16. Government Open Data

Government open data SHALL be treated as an important source class rather than a fallback.

Potential datasets include:

- agriculture;
- transport;
- land;
- commerce;
- procurement;
- tenders;
- imports;
- exports;
- population;
- planning approvals;
- infrastructure;
- companies;
- energy;
- employment;
- prices.

Each dataset MUST retain its governmental source authority.

Government statistics SHOULD NOT automatically be classified as high-confidence merely because they originate from a government institution.

Pulse SHALL distinguish:

```text
source authority
```

from:

```text
data quality
```

---

# 17. News Intelligence

News ingestion SHALL be architecturally separate from structured statistical ingestion.

News requires:

```text
publisher
article identity
publication time
authors
language
jurisdiction
topic
named entities
source URL
content rights
retrieval time
```

Pulse SHOULD derive structured observations from news only through traceable transformations.

For example:

```text
News article
     ↓
Entity extraction
     ↓
Event extraction
     ↓
Evidence
     ↓
Possible signal
```

One article alone SHOULD rarely constitute sufficient evidence for a high-confidence strategic recommendation.

News signals should support corroboration across multiple independent sources.

---

# 18. Regulatory Intelligence

Regulatory changes constitute a separate, high-value intelligence domain.

Pulse SHOULD support:

- legislation;
- regulations;
- tariff amendments;
- tax rules;
- customs changes;
- import restrictions;
- export restrictions;
- standards;
- licences;
- permits;
- environmental rules;
- sanctions;
- central-bank directives;
- industry regulator notices.

The canonical regulatory lifecycle SHOULD distinguish:

```text
announced
proposed
published
adopted
effective
amended
suspended
repealed
```

This distinction is critical.

A proposed regulation is not an effective regulation.

---

# 19. Internal Baobab Evidence

Pulse SHALL consume authorised evidence from Baobab engines.

## Payload CMS

Potential evidence:

```text
content published
campaign activity
content taxonomy
market-facing messaging
publication frequency
audience interactions where available
```

## MedusaJS

Potential evidence:

```text
catalogue activity
orders
pricing
inventory
customers
regions
markets
promotions
sales channels
returns
cart behaviour
```

## iDempiere

Potential evidence:

```text
procurement
inventory
financial transactions
accounting
suppliers
receivables
payables
projects
assets
manufacturing
costs
cash movements
```

Pulse MUST consume these through approved contracts, APIs or events.

Direct cross-engine database access is prohibited.

---

# 20. Intelligence Processing Pipeline

The canonical Pulse pipeline is:

```text
ACQUIRE
   ↓
PRESERVE
   ↓
NORMALISE
   ↓
VALIDATE
   ↓
ENRICH
   ↓
RESOLVE
   ↓
CORRELATE
   ↓
DERIVE
   ↓
ANALYSE
   ↓
SCORE
   ↓
EXPLAIN
   ↓
PUBLISH
   ↓
OBSERVE OUTCOME
   ↓
LEARN
```

---

# 21. Acquisition

Acquisition adapters MAY support:

```text
REST
GraphQL
SOAP
SDMX
WebSocket
RSS/Atom
SFTP
CSV
JSON
XML
XLSX
Parquet
event streams
webhooks
authorised web extraction
manual uploads
```

Adapters MUST remain isolated from canonical-domain processing.

Conceptually:

```text
source-specific format
        ↓
source adapter
        ↓
raw source record
        ↓
normaliser
        ↓
canonical observation
```

---

# 22. Raw Preservation

Where licensing and security permit, Pulse SHOULD preserve raw acquisition artefacts.

This allows:

- reprocessing;
- auditing;
- parser upgrades;
- dispute resolution;
- forensic analysis;
- reproducibility.

The raw zone MUST be treated as immutable or append-only wherever practical.

---

# 23. Normalisation

Normalisation converts source representations into canonical semantics.

Examples:

```text
"South Africa"
"ZA"
"ZAF"
"710"
```

may resolve to one canonical geography.

Likewise:

```text
ZAR
R
South African Rand
```

must resolve to a canonical currency.

Normalisation MUST NOT destroy source-original values.

Therefore:

```text
raw_value
canonical_value
```

must both remain available where necessary.

---

# 24. Entity Resolution

Pulse SHALL provide controlled entity resolution.

Examples:

```text
"Nabhold Pty Ltd"
"NABHOLD (PTY) LTD"
"Nabhold"
```

may or may not represent the same entity.

Entity resolution SHALL support:

```text
exact match
deterministic match
reference mapping
probabilistic candidate match
human-confirmed match
```

Probabilistic identity matches MUST NOT silently become canonical mappings.

---

# 25. Temporal Architecture

Pulse is inherently temporal.

A datum may have several independent timestamps:

```text
valid_time
observed_time
published_time
effective_time
retrieved_time
processed_time
superseded_time
```

These MUST NOT be conflated.

For example:

```text
Inflation for June
    measured during June
    published 15 July
    retrieved 16 July
```

represents at least three distinct temporal facts.

---

# 26. Bitemporal Design

Where justified, intelligence records SHOULD distinguish:

```text
valid time
```

from:

```text
system time
```

This allows Pulse to answer:

> What was believed on 1 June about conditions valid on 15 May?

rather than only:

> What does the database currently say?

Temporal correctness is essential for backtesting and decision reconstruction.

---

# 27. Core Canonical Intelligence Entities

The detailed canonical model will be defined separately, but this parent specification establishes the mandatory conceptual entities.

```text
Source
DataSource
Dataset
DatasetVersion
Acquisition
RawRecord

Observation
Measurement
Indicator

Entity
EntityReference
Location
Market
Instrument
Commodity

Evidence
EvidenceSet

Signal
Trend
Anomaly

Analysis
Insight

Opportunity
Risk
Forecast

Recommendation
Decision

Outcome
Feedback

Model
ModelVersion
ModelRun

IntelligenceJob
IntelligenceProduct

ProvenanceRecord
QualityAssessment
```

---

# 28. Observation

An `Observation` is the foundational semantic unit.

It represents:

> Something observed, reported or measured about a subject at a particular contextual and temporal point.

Examples:

```text
USD/ZAR = 17.82

Arabica futures = X

Uganda coffee exports = Y tonnes

South Africa inflation = Z%

Cape Town rainfall = N mm
```

An observation is not itself an insight.

---

# 29. Evidence

Evidence references one or more observations, source artefacts, events or documents used to support a later analytical conclusion.

```text
EvidenceSet
 ├── Observation A
 ├── Observation B
 ├── Government publication
 └── Trade event
```

Evidence MUST remain independently inspectable.

---

# 30. Signal

A `Signal` represents a potentially meaningful change, pattern or condition.

Examples:

```text
FX volatility increased 18%

coffee import volumes rising

competitor registrations accelerating

port congestion worsening

regulatory deadline approaching

regional rainfall below seasonal norm
```

Signals may be generated through:

```text
rules
statistical methods
machine learning
event correlation
human input
AI-assisted analysis
```

---

# 31. Insight

An `Insight` is an interpreted statement supported by evidence.

Example:

```text
South African demand for imported
specialty coffee appears to be growing
faster than supply from existing origins.
```

An insight SHALL include:

```text
evidence
confidence
method
scope
validity period
created_at
```

---

# 32. Opportunity

An `Opportunity` is an actionable condition in which available evidence suggests that an organisation may create economic, strategic or operational value.

An opportunity may include:

```text
market
sector
product
geography
time horizon
estimated magnitude
confidence
evidence
risks
recommended actions
```

Example:

```text
Uganda → South Africa
specialty coffee supply opportunity
```

---

# 33. Risk

A `Risk` represents an uncertain event or condition capable of negatively affecting objectives.

Potential risk categories include:

```text
market
FX
regulatory
supplier
customer
country
weather
logistics
financial
operational
reputational
```

---

# 34. Forecast

Forecasts MUST preserve:

```text
forecast origin
forecast horizon
prediction interval
method
model version
input dataset versions
generated_at
target period
```

The engine SHALL allow forecasts to later be compared with actual outcomes.

---

# 35. Recommendation

A recommendation is a proposed action derived from available intelligence.

Recommendations MUST indicate:

```text
what is recommended
why
evidence
confidence
expected outcome
risk
urgency
assumptions
```

A recommendation is not a command unless an explicit automation policy authorises execution.

---

# 36. Decision and Outcome

Pulse SHALL model the full decision loop.

```text
Insight
    ↓
Recommendation
    ↓
Decision
    ↓
Action
    ↓
Outcome
    ↓
Feedback
```

A human may:

```text
accept
reject
modify
defer
request additional evidence
```

a recommendation.

Capturing this feedback allows later assessment of intelligence quality.

---

# 37. Intelligence Quality

Every material intelligence object SHOULD support a quality profile including:

```text
source_quality
freshness
completeness
consistency
corroboration
method_confidence
model_confidence
overall_confidence
```

Confidence MUST NOT be represented as arbitrary AI-generated prose alone.

Where scoring is used, the scoring methodology must be defined and versioned.

---

# 38. Source Trust

Pulse SHALL maintain independent source assessments.

```text
Source
 ├── authority
 ├── reliability
 ├── timeliness
 ├── completeness
 ├── accessibility
 ├── licence
 └── historical accuracy
```

A highly authoritative source may still be stale.

A fast source may be inaccurate.

Authority and quality are not synonymous.

---

# 39. Contradictory Evidence

Pulse MUST support disagreement between sources.

It SHALL NOT simply overwrite one observation with another.

Example:

```text
Source A: production = 2.4m tonnes
Source B: production = 2.7m tonnes
```

The correct representation is:

```text
two observations
+
two provenance chains
+
possible reconciliation
```

rather than:

```text
production = 2.55m
```

unless a defined analytical method explicitly produces that estimate.

---

# 40. Multi-Tenancy

Pulse SHALL conform to the Baobab tenancy architecture.

A legal entity may be a default tenant boundary but is not synonymous with tenancy.

Each intelligence record MUST carry sufficient platform context to determine:

```text
tenant
scope
market
organisation
legal entity where applicable
digital estate where applicable
data classification
```

---

# 41. Public and Tenant Data

Pulse MUST distinguish at minimum:

```text
PUBLIC
BAOBAB_INTERNAL
TENANT
CONFIDENTIAL
RESTRICTED
```

Public World Bank data and confidential tenant financial data cannot be governed identically merely because they reside in the same intelligence engine.

---

# 42. Cross-Tenant Intelligence

Pulse SHALL NOT expose one tenant's confidential evidence to another tenant.

However, cross-market or aggregated intelligence MAY be derived if an explicit governance policy permits it.

Such derived information MUST prevent prohibited reconstruction of source-tenant information.

---

# 43. PostgreSQL Isolation

PostgreSQL 17 supports Row-Level Security policies that restrict which rows are visible or modifiable. Pulse SHOULD use database-enforced isolation as defence in depth for tenant-scoped relational datasets.

Application-level tenant filters alone SHALL NOT be considered sufficient isolation for sensitive tenant datasets.

---

# 44. Physical Storage Architecture

Initial storage SHOULD favour simplicity.

```text
                PostgreSQL 17
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   Metadata       Canonical      Intelligence
                  Observations      Objects
       │              │              │
       └──────────────┼──────────────┘
                      │
                  Object Storage
                      │
                 Raw Artefacts
```

Separate specialist technologies SHOULD be introduced only where demonstrated requirements justify them.

---

# 45. PostgreSQL Partitioning

High-volume temporal tables such as:

```text
observations
measurements
signals
ingestion_records
```

MAY be declaratively partitioned.

PostgreSQL 17 provides declarative table partitioning and partition pruning for large tables.

Partitioning strategy SHALL be evidence-driven rather than universally applied.

---

# 46. No Premature Data Platform Sprawl

The first implementation SHOULD NOT require:

```text
Kafka
Spark
Hadoop
OpenSearch
dedicated feature store
dedicated vector database
distributed graph database
lakehouse platform
```

unless a measurable requirement cannot reasonably be met without one.

Start with:

```text
PostgreSQL
+
object storage
+
workers
+
HTTP/event integration
```

The architectural contracts SHALL nevertheless allow future specialist infrastructure.

---

# 47. Analytical Compute

Analytical execution SHALL be separated from the request-serving API.

```text
Pulse API
   │
   ├── lightweight read/query
   │
   └── submit work
             │
             ▼
        Job Scheduler
             │
             ▼
        Worker Pool
             │
     ┌───────┼───────┐
     ▼       ▼       ▼
 ingestion analysis model
 workers   workers   workers
```

Long-running analysis MUST NOT block API request workers.

---

# 48. Python Architecture

Python 3.14 is the preferred implementation runtime.

The repository SHOULD remain compatible with conventional CPython first.

Free-threaded Python may later improve CPU utilisation for suitable threaded workloads, but Python's own documentation notes that third-party extension compatibility must be considered because some packages may re-enable the GIL.

Pulse SHALL therefore not make free-threaded execution an initial platform dependency.

---

# 49. Package Boundaries

A likely top-level implementation structure is:

```text
src/baobab_pulse/
│
├── api/
├── application/
├── domain/
├── contracts/
├── ingestion/
│   ├── adapters/
│   ├── scheduling/
│   └── pipelines/
├── provenance/
├── quality/
├── normalization/
├── entities/
├── temporal/
├── signals/
├── analysis/
├── opportunities/
├── risks/
├── forecasting/
├── recommendations/
├── models/
├── ai/
├── decisions/
├── events/
├── storage/
├── security/
├── tenancy/
├── observability/
└── configuration/
```

The exact package contract SHALL be defined in a subsequent implementation specification.

---

# 50. AI Architecture

AI SHALL be a capability inside Pulse rather than the engine's architectural centre.

```text
             Intelligence Engine
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
     Rules      Statistics       ML
        │           │            │
        └───────────┼────────────┘
                    │
                    ▼
                  AI/LLM
                    │
              where appropriate
```

A deterministic rule SHOULD be preferred to an LLM when it solves the same problem reliably.

---

# 51. LLM Usage

Permitted uses may include:

```text
document summarisation
entity extraction
classification
semantic comparison
narrative synthesis
hypothesis generation
natural-language querying
explanation generation
research assistance
```

LLMs SHALL NOT become authoritative sources.

An LLM output may produce:

```text
candidate interpretation
```

but evidence must remain external and traceable.

---

# 52. Agentic AI

Agentic workflows may eventually:

```text
discover data
query authorised sources
compare evidence
run analyses
request additional information
prepare recommendations
```

but autonomous side effects SHALL require explicit policies.

The platform SHALL distinguish:

```text
read
analyse
recommend
propose action
execute action
```

These are progressively different authority levels.

---

# 53. Model Registry

Any analytical or machine-learning model whose outputs materially influence intelligence SHALL be registered.

At minimum:

```text
Model
ModelVersion
ModelRun
```

SHOULD capture:

```text
name
purpose
owner
version
algorithm/provider
parameters
training/reference data
deployment status
created_at
retired_at
```

---

# 54. Reproducibility

Pulse SHOULD make material intelligence reproducible.

Given:

```text
model version
+
dataset version
+
parameters
+
source records
```

the platform should be capable, where technically feasible, of reconstructing an analysis.

---

# 55. Event Architecture

Pulse SHALL be an event consumer and event producer.

Potential consumed events:

```text
trade.order.completed
trade.product.changed
trade.inventory.changed

erp.invoice.posted
erp.payment.received
erp.inventory.changed
erp.purchase_order.completed

content.published
content.updated

control_plane.context.changed
control_plane.mapping.changed
```

Potential emitted events:

```text
pulse.observation.created
pulse.signal.detected
pulse.insight.created
pulse.opportunity.detected
pulse.risk.detected
pulse.forecast.created
pulse.recommendation.created
pulse.decision.recorded
pulse.intelligence.invalidated
```

Canonical event definitions belong in `nabhold/shared`.

---

# 56. Event Reliability

Pulse event publication SHOULD follow a transactional-outbox strategy where events correspond to committed state changes.

Consumers MUST assume:

```text
at-least-once delivery
```

unless infrastructure explicitly provides stronger guarantees.

Handlers SHALL therefore be idempotent.

---

# 57. Correlation and Causation

All cross-engine workflows SHALL propagate:

```text
event_id
correlation_id
causation_id
tenant_id
context_id
occurred_at
schema_version
```

This enables reconstruction of an intelligence chain.

---

# 58. API Architecture

Pulse SHALL expose headless APIs.

Initial API categories SHOULD include:

```text
/sources
/datasets
/observations
/signals
/insights
/opportunities
/risks
/forecasts
/recommendations
/decisions
/intelligence-products
/jobs
/models
```

Administrative interfaces SHALL remain logically distinct from tenant-consumption interfaces.

---

# 59. Query APIs

The engine SHOULD support filters such as:

```text
tenant
market
country
region
industry
commodity
currency
source
time range
confidence
status
```

Temporal filtering is a fundamental API concern, not an afterthought.

---

# 60. Intelligence Products

Pulse SHALL support reusable, productised intelligence outputs.

Examples:

```text
Market Pulse
Commodity Pulse
FX Pulse
Trade Corridor Pulse
Country Pulse
Supplier Risk Pulse
Regulatory Pulse
Opportunity Radar
Executive Brief
```

These products compose intelligence capabilities without changing engine ownership.

---

# 61. Opportunity Radar

One high-value Pulse capability SHALL be an `Opportunity Radar`.

Conceptually:

```text
Trade statistics
     +
Market prices
     +
FX
     +
Macroeconomics
     +
Regulations
     +
Company activity
     +
News
     +
Internal demand
     ↓
Opportunity Detection
     ↓
Opportunity
```

Example:

```text
Commodity:
    green coffee

Origin:
    Uganda

Destination:
    South Africa

Evidence:
    rising imports
    favourable origin prices
    adequate FX conditions
    supply availability
    customer demand

Output:
    commercial opportunity
```

---

# 62. Risk Radar

Likewise:

```text
Weather
+
FX
+
Supplier data
+
News
+
Regulation
+
Operational exposure
        ↓
Risk Detection
```

may identify:

```text
currency exposure
supply disruption
border disruption
regulatory risk
counterparty distress
weather-related shortage
```

---

# 63. Human Oversight

High-impact recommendations SHALL support human review.

Human users SHOULD be able to inspect:

```text
recommendation
evidence
sources
reasoning summary
assumptions
confidence
alternative interpretations
```

before accepting a recommendation.

---

# 64. Explainability

Every important intelligence object SHOULD answer:

```text
What happened?

What evidence supports it?

Which method produced it?

How confident are we?

What assumptions were made?

What contradicting evidence exists?

When will this assessment become stale?
```

If Pulse cannot answer these questions, it should be considered insufficiently governed for consequential decision support.

---

# 65. Freshness

Different intelligence classes have different useful lifetimes.

Example:

```text
FX                 minutes
news               hours
weather forecast   hours
commodity price    minutes/hours
trade statistics   weeks/months
GDP                months/quarters
company registry   days/months
regulations        event-driven
```

Freshness MUST therefore be policy-driven per dataset.

---

# 66. Staleness

Pulse SHALL explicitly identify stale intelligence.

An old valid observation is not necessarily invalid.

But a recommendation based upon stale inputs may no longer be trustworthy.

Intelligence objects SHOULD therefore carry:

```text
valid_until
```

or equivalent freshness policies where appropriate.

---

# 67. Source Failure

Source acquisition MUST tolerate external failure.

```text
External API unavailable
        ↓
retry policy
        ↓
backoff
        ↓
circuit breaker
        ↓
record acquisition failure
        ↓
preserve previous data
        ↓
mark freshness degradation
```

Source failure SHALL NOT automatically delete or invalidate previously acquired evidence.

---

# 68. Rate Limits

Adapters SHALL honour provider:

```text
rate limits
quotas
terms of use
robots policies where applicable
licences
```

Credentials MUST be stored outside source code.

---

# 69. Data Licensing

Pulse SHALL record licensing metadata where available.

Potential licences include:

```text
open
public domain
attribution
commercial subscription
internal licence
restricted
unknown
```

Data ingestion does not automatically grant unrestricted redistribution rights.

---

# 70. Security

Pulse SHALL conform to Baobab platform security requirements including:

```text
authentication
authorisation
tenant isolation
secret management
encryption
audit
least privilege
network segmentation
data classification
dependency security
container security
```

External content must be treated as untrusted input.

---

# 71. Prompt Injection and Untrusted Content

News articles, web documents, uploaded documents and other externally sourced natural-language material SHALL be considered potentially hostile when processed through LLMs.

External text MUST NOT be allowed to redefine:

```text
system instructions
security policies
tool permissions
tenant context
authorisation
```

LLM-facing pipelines require explicit trust boundaries.

---

# 72. Personally Identifiable Information

Pulse SHALL collect personal information only where there is a legitimate authorised purpose.

Company registry records may contain personal information about:

```text
directors
officers
beneficial owners
```

Such information SHALL be governed according to jurisdiction, purpose and data classification.

---

# 73. Observability

Pulse SHALL emit:

```text
traces
metrics
structured logs
```

using OpenTelemetry-compatible instrumentation.

OpenTelemetry provides vendor-neutral telemetry for traces, metrics and logs; its current Python implementation lists traces and metrics as stable while its logs implementation remains under development.

Instrumentation SHOULD capture:

```text
source
adapter
job
pipeline
tenant
dataset
correlation
duration
outcome
```

without leaking sensitive data into logs.

---

# 74. Operational Metrics

Key metrics SHOULD include:

```text
source availability
ingestion latency
records acquired
records rejected
normalisation failures
duplicate rate
dataset freshness
worker queue depth
analysis duration
signal generation rate
recommendation acceptance
source error rate
API latency
```

---

# 75. Intelligence Effectiveness Metrics

Pulse SHOULD eventually measure not only system performance but intelligence quality.

Examples:

```text
forecast accuracy
signal precision
signal recall
opportunity conversion
recommendation acceptance
recommendation success
false-positive rate
time-to-detection
time-to-decision
```

This closes the loop between software operation and business value.

---

# 76. Control Plane Relationship

`baobab-cp` owns platform control metadata.

Pulse MUST consume, not redefine:

```text
Engine
EngineInstance
Capability
CapabilityBinding
Context
Market
DigitalEstate
IsolationProfile
CanonicalEntity
ExternalReference
Mapping
MappingScope
```

Pulse intelligence objects reference those canonical platform identities.

---

# 77. `nabhold/shared` Relationship

`nabhold/shared` owns organisation-wide contracts.

Pulse SHALL import or generate bindings from canonical definitions for:

```text
events
schemas
identifiers
contexts
errors
security claims
enumerations
API conventions
```

Pulse SHALL NOT independently redefine shared canonical concepts.

---

# 78. Payload Relationship

Payload CMS remains the content system of record.

Pulse may:

```text
consume published content
analyse content
generate intelligence
propose content
```

but it SHALL NOT silently become the content repository.

Pulse-generated narrative intended for publication SHOULD return through a governed workflow to Payload.

---

# 79. MedusaJS Relationship

Medusa remains the commerce system of record.

Pulse may derive:

```text
sales trends
pricing signals
inventory risk
customer patterns
market opportunities
```

but SHALL NOT directly mutate Medusa operational data without an approved integration workflow.

---

# 80. iDempiere Relationship

iDempiere remains the ERP system of record.

Pulse may analyse:

```text
finance
costs
inventory
procurement
suppliers
working capital
assets
operations
```

but SHALL NOT replace accounting or ERP control logic.

---

# 81. Intelligence-to-Action Boundary

The canonical boundary is:

```text
PULSE
  ↓
recommendation/event
  ↓
owning engine
  ↓
business workflow
  ↓
approved operational mutation
```

Not:

```text
PULSE
  ↓
direct database update
```

---

# 82. Deployment

Pulse SHALL be independently deployable.

Initial production components may include:

```text
pulse-api
pulse-worker
pulse-scheduler

postgresql
object-storage

optional redis
```

Services SHOULD be individually scalable without creating artificial microservices.

---

# 83. Reproducible Engineering Environment

Development SHALL use the approved `baobab-dev` profile.

The environment SHOULD provide:

```text
Python 3.14
uv
PostgreSQL client
Docker
Docker Compose
GitHub CLI
contract tooling
linting
testing
security tooling
```

Runtime images SHALL remain distinct from the development image.

---

# 84. CI/CD

Every Pulse build SHALL enforce at minimum:

```text
format
lint
type checking
unit tests
integration tests
contract tests
migration tests
security scanning
dependency scanning
container scanning
reproducible build
```

GitHub Actions SHALL follow Nabhold's SHA-pinning policy.

---

# 85. Schema Evolution

All externally visible contracts require explicit versions.

Breaking changes SHALL NOT silently alter:

```text
event semantics
API representations
canonical intelligence entities
```

Migrations must support rolling compatibility where practical.

---

# 86. Data Evolution

Source schemas will change.

Therefore adapters MUST distinguish:

```text
source schema
```

from:

```text
Pulse canonical schema
```

An upstream provider changing JSON structure SHOULD normally require adapter changes rather than propagation of breaking changes throughout Pulse.

---

# 87. Backfills

Pulse SHALL support historical ingestion.

Backfill jobs MUST be distinguishable from live ingestion.

```text
LIVE
BACKFILL
REPROCESS
CORRECTION
```

should be explicit acquisition modes.

Backfilled records MUST preserve appropriate source and observation dates rather than pretending they were newly observed facts.

---

# 88. Corrections

Statistical agencies frequently revise historical series.

Pulse MUST preserve revisions.

A corrected GDP figure should not simply destroy the previously published figure.

The system should be capable of representing:

```text
version 1
    ↓
superseded by
    ↓
version 2
```

---

# 89. Deduplication

Duplicate acquisition SHALL be detected through a combination of:

```text
source identity
external identifiers
content hashes
semantic keys
timestamps
```

Deduplication MUST NOT merge genuinely independent corroborating sources.

---

# 90. Research Capability

Pulse MAY later provide structured research workflows such as:

```text
Question
   ↓
Evidence search
   ↓
Source retrieval
   ↓
Evidence extraction
   ↓
Cross-source comparison
   ↓
Analysis
   ↓
Cited intelligence brief
```

Such workflows must preserve source attribution and evidence lineage.

---

# 91. Scenario Analysis

The engine SHOULD eventually support scenario modelling.

Example:

```text
IF
    ZAR depreciates 10%
AND
    coffee benchmark rises 8%
AND
    freight rises 5%

THEN
    estimated landed cost = ?
    gross margin = ?
    recommended pricing = ?
```

Scenario outputs must remain separate from observed reality.

---

# 92. What Pulse Must Not Become

Pulse SHALL NOT become:

```text
a second ERP
a second CMS
a second commerce engine
a shadow Control Plane
a general file store
an uncontrolled data lake
an LLM playground
a collection of arbitrary agents
a cross-tenant data leakage mechanism
```

---

# 93. MVP Capability Boundary

The first production slice SHOULD prove the complete intelligence chain on a manageable set of domains.

Recommended first domains:

```text
FX
Commodity Prices
Trade Statistics
Macroeconomic Indicators
News
```

These provide useful commercial intelligence while exercising both structured and unstructured ingestion.

The remaining domains then join the same architecture:

```text
Weather
Customs
Market Prices
Company Registries
Geospatial
Government Open Data
Regulatory Changes
```

No architectural redesign should be required.

---

# 94. Target End-State Capability

The desired end-state is:

```text
                           BAOBAB PULSE

                               WORLD
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
    ECONOMIC                 PHYSICAL                INSTITUTIONAL
       │                        │                        │
   FX                         Weather               Government
   Macro                      Geography             Regulation
   Commodities               Logistics             Registries
   Market prices                                    Customs
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                              TRADE
                       statistics / flows
                                 │
                                 ▼
                               NEWS
                                 │
                                 ▼
                         EXTERNAL EVIDENCE
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
       Payload                 Medusa               iDempiere
       Content                Commerce                ERP
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                             EVIDENCE
                                 │
                                 ▼
                           OBSERVATIONS
                                 │
                                 ▼
                              SIGNALS
                                 │
                                 ▼
                              INSIGHTS
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             OPPORTUNITIES     RISKS       FORECASTS
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                        RECOMMENDATIONS
                                 │
                                 ▼
                             DECISIONS
                                 │
                                 ▼
                              OUTCOMES
                                 │
                                 ▼
                             FEEDBACK
```

---

# 95. Architectural Success Criteria

Baobab Pulse shall be considered architecturally successful when it can demonstrate all of the following:

1. acquire heterogeneous external data without contaminating the canonical model with provider-specific structures;
2. preserve provenance to the originating evidence;
3. represent competing or contradictory observations;
4. contextualise evidence by market, geography, tenant and time;
5. consume Baobab engine events without database coupling;
6. generate deterministic and analytical signals;
7. produce evidence-backed insights;
8. identify opportunities and risks;
9. generate explainable recommendations;
10. preserve the human decision;
11. measure eventual outcomes;
12. learn from decision feedback;
13. maintain tenant and confidentiality boundaries;
14. reproduce material analytical results;
15. scale acquisition and analytical workloads independently;
16. replace external data providers without redesigning the engine;
17. introduce new analytical or AI techniques without rewriting ingestion;
18. add new intelligence domains without redesigning the platform;
19. expose intelligence through stable headless contracts;
20. remain operationally understandable.

---

# 96. Governing Architectural Rules

The following rules are normative.

**PULSE-001**  
Pulse is the Baobab system of intelligence.

**PULSE-002**  
Operational systems of record remain authoritative for their domains.

**PULSE-003**  
No engine shall be integrated through direct shared-database coupling.

**PULSE-004**  
All material intelligence must have traceable evidence.

**PULSE-005**  
Source provenance shall survive every transformation.

**PULSE-006**  
Observed, published, retrieved, effective and processed times shall not be casually conflated.

**PULSE-007**  
Raw source values shall remain recoverable where licensing permits.

**PULSE-008**  
Contradictory evidence shall be preserved rather than silently overwritten.

**PULSE-009**  
Source authority and source quality shall remain separate concepts.

**PULSE-010**  
AI output is not evidence merely because an AI generated it.

**PULSE-011**  
Deterministic computation shall be preferred when an LLM adds no material capability.

**PULSE-012**  
Autonomous operational mutations require explicit policy.

**PULSE-013**  
Cross-tenant intelligence must respect isolation and confidentiality.

**PULSE-014**  
Public data and tenant-private data require distinct governance.

**PULSE-015**  
External-source adapters shall remain isolated from the canonical domain.

**PULSE-016**  
Long-running acquisition and analysis shall execute asynchronously.

**PULSE-017**  
Canonical events shall be versioned.

**PULSE-018**  
Material models shall be registered and versioned.

**PULSE-019**  
Recommendations shall expose evidence, confidence and assumptions.

**PULSE-020**  
Decision outcomes should feed back into intelligence-quality assessment.

**PULSE-021**  
Infrastructure complexity shall be introduced only after workload evidence justifies it.

**PULSE-022**  
Pulse shall remain independently deployable.

**PULSE-023**  
Control Plane identities shall not be redefined locally.

**PULSE-024**  
Organisation-wide schemas belong in `nabhold/shared`.

**PULSE-025**  
Temporal history shall be preserved wherever revision history affects interpretation.

---

# 97. Required Child Architecture Documents

This parent specification SHALL govern a dedicated Pulse ADR family.

At minimum, subsequent decisions should address:

```text
ADR-PULSE-001  Engine Mission and Boundary
ADR-PULSE-002  Intelligence Domain Model
ADR-PULSE-003  Source Adapter Architecture
ADR-PULSE-004  Raw Acquisition and Immutable Evidence
ADR-PULSE-005  Canonical Observation Model
ADR-PULSE-006  Provenance and Lineage
ADR-PULSE-007  Temporal and Bitemporal Semantics
ADR-PULSE-008  Entity Resolution
ADR-PULSE-009  Data Quality and Confidence
ADR-PULSE-010  Tenant Isolation and Data Classification
ADR-PULSE-011  PostgreSQL Physical Architecture
ADR-PULSE-012  Object Storage
ADR-PULSE-013  Scheduling and Worker Execution
ADR-PULSE-014  Event Consumption and Publication
ADR-PULSE-015  Signal Detection
ADR-PULSE-016  Opportunity and Risk Detection
ADR-PULSE-017  Forecasting
ADR-PULSE-018  Model Registry and Model Lifecycle
ADR-PULSE-019  LLM Integration
ADR-PULSE-020  Agentic Execution and Human Oversight
ADR-PULSE-021  Recommendation and Decision Lifecycle
ADR-PULSE-022  External Data Licensing and Compliance
ADR-PULSE-023  Source Credential and Secret Management
ADR-PULSE-024  API Architecture
ADR-PULSE-025  Observability
ADR-PULSE-026  Reproducibility and Backtesting
ADR-PULSE-027  Retention, Revision and Archival
ADR-PULSE-028  Resilience and External Source Failure
ADR-PULSE-029  Intelligence Product Composition
ADR-PULSE-030  Security and Adversarial External Content
```

Additional ADRs may be introduced as implementation discovers genuine architectural decisions.

---

# 98. Required Derived Implementation Contracts

After the ADR family stabilises, this parent specification SHALL produce at least:

```text
1. Baobab Pulse Canonical Intelligence Model

2. External Data Source Contract

3. Source Adapter Interface Specification

4. PostgreSQL Physical Data Model

5. Python Package and Interface Specification

6. OpenAPI Contract

7. AsyncAPI / Canonical Event Contract

8. Intelligence Quality and Confidence Specification

9. Temporal Data Specification

10. Model and AI Governance Specification

11. Deployment and Runtime Specification

12. Repository Scaffold Specification
```

---

# 99. Final Architectural Statement

Baobab Pulse exists to make Baobab **aware of its environment**.

Payload CMS, MedusaJS and iDempiere establish what Baobab organisations publish, trade and operate.

Pulse adds something fundamentally different:

```text
outside world
      +
enterprise activity
      +
historical evidence
      +
analytical methods
      ↓
context
      ↓
understanding
      ↓
anticipation
      ↓
decision support
```

Its competitive value will not come primarily from having the newest model or the largest number of AI agents.

Its enduring value will come from owning a trustworthy intelligence architecture capable of answering:

> **What is happening?**

> **What changed?**

> **Where?**

> **Why might it matter?**

> **What evidence supports that conclusion?**

> **What opportunity or risk does it create?**

> **What should the organisation consider doing next?**

> **And did that decision ultimately prove correct?**

The target is therefore not merely an AI engine.

The target is an **evidence-backed, continuously learning enterprise intelligence capability** capable of combining:

**FX, commodity prices, weather, trade statistics, customs data, macroeconomic indicators, market prices, company registries, geospatial information, government open data, news and regulatory change**

with the operational reality supplied by the Baobab Platform.

That is the architectural purpose of **Baobab Pulse**.
