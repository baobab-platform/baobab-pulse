# ADR-Pulse-X01-Baobab Pulse Canonical Intelligence Model

**Document ID:** `ARCH-PULSE-CIM-001`  
**Status:** Proposed  
**Parent:** `ARCH-PULSE-001 — Baobab Pulse Intelligence Engine Parent Architecture Specification`  
**Repository:** `nabhold/baobab-pulse`  
**Canonical contract owner:** `nabhold/shared`  
**Platform context owner:** `nabhold/baobab-cp`  
**Engine:** Baobab Pulse  
**Classification:** Parent Semantic Implementation Contract

---

# 1. Purpose

This document defines the **canonical semantic model for intelligence in Baobab Pulse**.

Its purpose is to establish one stable vocabulary and relationship model for transforming heterogeneous source material into evidence-backed intelligence.

It defines the canonical concepts required to represent:

```text
Source
↓
Acquisition
↓
Raw Record
↓
Observation
↓
Evidence
↓
Signal
↓
Analysis
↓
Insight
↓
Opportunity / Risk / Forecast
↓
Recommendation
↓
Decision
↓
Outcome
↓
Feedback
```

This model is deliberately independent of:

- source provider;
- external API;
- database schema;
- Python ORM;
- machine-learning framework;
- LLM provider;
- transport protocol;
- user interface.

It therefore represents the **semantic truth of Pulse**, from which physical schemas, Python models, OpenAPI resources and events shall later be derived.

---

# 2. Design Objective

The model SHALL enable Baobab Pulse to answer, for every material intelligence product:

1. What was observed?
2. Who or what reported it?
3. When was it valid?
4. When was it observed?
5. When was it published?
6. When did Baobab acquire it?
7. What transformation occurred?
8. Which canonical entity does it concern?
9. Which geography, market and tenant context apply?
10. Which evidence supports the conclusion?
11. Which method produced the conclusion?
12. What contradictory evidence exists?
13. How confident is Pulse?
14. What action was recommended?
15. What decision was taken?
16. What eventually happened?

---

# 3. Core Model

```text
                     ┌──────────────┐
                     │    Source    │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  DataSource  │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Dataset    │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Acquisition  │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  RawRecord   │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Observation  │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Evidence   │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Signal    │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Analysis   │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Insight    │
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │Opportunity │ │    Risk    │ │  Forecast  │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             └───────────────┼───────────────┘
                             ▼
                    ┌────────────────┐
                    │ Recommendation │
                    └───────┬────────┘
                            ▼
                    ┌────────────────┐
                    │    Decision    │
                    └───────┬────────┘
                            ▼
                    ┌────────────────┐
                    │    Outcome     │
                    └───────┬────────┘
                            ▼
                    ┌────────────────┐
                    │    Feedback    │
                    └────────────────┘
```

---

# 4. Canonical Identity

Every canonical Pulse entity SHALL have:

```text
id
type
created_at
updated_at
```

where `id` is a globally unique, immutable canonical identifier.

The canonical identifier SHALL NOT depend on:

- provider identifiers;
- tenant identifiers;
- database sequence numbers;
- source URLs;
- external business keys.

External identifiers shall instead be represented through references.

---

# 5. Canonical Context

All material intelligence entities SHALL be context-aware.

A canonical context MAY include:

```text
tenant_id
context_id
market_id
legal_entity_id
organisation_id
digital_estate_id
country_id
region_id
location_id
engine_id
engine_instance_id
```

Context MUST be inherited explicitly, not guessed implicitly.

---

# 6. Context Inheritance Rule

Context propagates down an intelligence derivation chain unless explicitly narrowed or overridden.

Example:

```text
Observation
 tenant = Thamani
 market = South Africa
 commodity = green coffee
        ↓
Signal
        ↓
Insight
        ↓
Opportunity
```

The derived objects SHALL inherit:

```text
tenant = Thamani
market = South Africa
commodity = green coffee
```

unless the derivation changes scope.

---

# 7. Scope Narrowing

Derived intelligence MAY narrow context.

Example:

```text
Insight:
    East African coffee exports increasing
```

may generate:

```text
Opportunity:
    Uganda → South Africa specialty coffee
```

This is valid because the derived scope is narrower than the parent scope.

---

# 8. Scope Broadening

Derived intelligence SHALL NOT broaden confidential tenant scope without explicit authorisation.

A tenant-private insight cannot automatically become:

```text
public regional intelligence
```

merely through aggregation.

---

# 9. CanonicalEntity Reference

Pulse SHALL reuse the platform-wide `CanonicalEntity` model defined in Baobab Control Plane contracts.

Pulse-specific concepts SHALL therefore reference:

```text
CanonicalEntity
```

rather than redefining:

```text
Company
Supplier
Customer
LegalEntity
Product
Commodity
Location
```

where such entities already exist canonically.

---

# 10. Intelligence Entity Categories

Pulse entities fall into seven conceptual families.

| Family | Examples |
|---|---|
| Source | Source, DataSource, Dataset |
| Acquisition | Acquisition, RawRecord |
| Evidence | Observation, Measurement, Evidence |
| Detection | Signal, Trend, Anomaly |
| Interpretation | Analysis, Insight |
| Decision Intelligence | Opportunity, Risk, Forecast, Recommendation |
| Learning | Decision, Outcome, Feedback |

---

# 11. Source

A `Source` represents an authority, organisation, institution, engine or provider from which information originates.

Examples:

```text
World Bank
IMF
South African Reserve Bank
Uganda Bureau of Statistics
Reuters
Payload CMS
MedusaJS
iDempiere
```

Canonical attributes:

```text
Source
 ├── id
 ├── name
 ├── source_type
 ├── organisation_reference
 ├── jurisdiction
 ├── authority_class
 ├── website
 ├── trust_profile
 ├── status
 └── metadata
```

---

# 12. SourceType

Permitted conceptual types include:

```text
GOVERNMENT
CENTRAL_BANK
INTERNATIONAL_ORGANISATION
NEWS_ORGANISATION
MARKET_DATA_PROVIDER
WEATHER_PROVIDER
REGISTRY
RESEARCH_INSTITUTION
COMMERCIAL_PROVIDER
BAOBAB_ENGINE
TENANT
MANUAL
OTHER
```

---

# 13. Source Cardinalities

```text
Source
 1 ─────── * DataSource
```

A source may expose many data sources.

A data source belongs to exactly one canonical source.

---

# 14. DataSource

A `DataSource` represents an actual acquisition endpoint, feed, publication stream or information channel.

Examples:

```text
World Bank Indicators API
SARB daily exchange-rate feed
Medusa order event stream
Reuters RSS feed
OpenCorporates company endpoint
```

Attributes:

```text
DataSource
 ├── id
 ├── source_id
 ├── name
 ├── data_domain
 ├── transport
 ├── endpoint_reference
 ├── authentication_type
 ├── refresh_policy
 ├── licence_profile
 ├── schema_profile
 ├── status
 └── metadata
```

---

# 15. Data Domain

Canonical domain values SHOULD include:

```text
FX
COMMODITY
WEATHER
TRADE
CUSTOMS
MACROECONOMIC
MARKET_PRICE
COMPANY_REGISTRY
GEOSPATIAL
GOVERNMENT_OPEN_DATA
NEWS
REGULATORY
CONTENT
COMMERCE
ERP
OTHER
```

---

# 16. Dataset

A `Dataset` represents a logically coherent collection of records exposed through a DataSource.

Example:

```text
World Bank:
    GDP growth annual dataset

Weather provider:
    hourly precipitation observations

iDempiere:
    posted invoice event dataset
```

Attributes:

```text
Dataset
 ├── id
 ├── data_source_id
 ├── name
 ├── dataset_code
 ├── description
 ├── domain
 ├── unit_profile
 ├── geography_profile
 ├── frequency
 ├── classification
 ├── status
 └── metadata
```

---

# 17. DatasetVersion

Datasets SHALL support versioning where the upstream source or Pulse transformation requires it.

```text
Dataset
 1 ─────── * DatasetVersion
```

Attributes include:

```text
version
valid_from
valid_to
schema_version
methodology_version
released_at
supersedes
```

---

# 18. Acquisition

An `Acquisition` represents one execution that retrieves source material.

Examples:

```text
FX polling job at 08:00
World Bank monthly refresh
news feed retrieval
Medusa event consumption
historical trade-statistics backfill
```

Attributes:

```text
Acquisition
 ├── id
 ├── data_source_id
 ├── dataset_id
 ├── mode
 ├── started_at
 ├── completed_at
 ├── status
 ├── cursor
 ├── records_received
 ├── records_accepted
 ├── records_rejected
 ├── checksum
 ├── error_summary
 └── metadata
```

---

# 19. AcquisitionMode

```text
LIVE
SCHEDULED
BACKFILL
REPROCESS
CORRECTION
MANUAL
EVENT_DRIVEN
```

---

# 20. Acquisition Cardinality

```text
Dataset
 1 ─────── * Acquisition

Acquisition
 1 ─────── * RawRecord
```

---

# 21. RawRecord

A `RawRecord` represents the preserved source-native representation of acquired information.

Attributes:

```text
RawRecord
 ├── id
 ├── acquisition_id
 ├── external_record_id
 ├── raw_location
 ├── media_type
 ├── source_schema_version
 ├── content_hash
 ├── observed_at
 ├── published_at
 ├── retrieved_at
 ├── classification
 └── metadata
```

The raw payload itself may reside in object storage rather than PostgreSQL.

---

# 22. Raw Immutability

A RawRecord SHALL be immutable after successful acquisition except for metadata corrections that do not modify source content.

If the source changes:

```text
RawRecord v1
RawRecord v2
```

SHALL be preserved as separate source artefacts.

---

# 23. Observation

An `Observation` represents a canonicalised claim or measurement derived from one or more source records.

Definition:

> An Observation is a statement that a measurable, categorical or stateful property of a subject had a particular value within a defined temporal and contextual scope.

Examples:

```text
USD/ZAR = 17.82

GDP growth = 2.1%

Rainfall = 14 mm

Coffee exports = 310,000 tonnes

Company registration status = active
```

---

# 24. Observation Structure

```text
Observation
 ├── id
 ├── subject_reference
 ├── metric
 ├── value
 ├── value_type
 ├── unit
 ├── currency
 ├── geography
 ├── market
 ├── valid_time
 ├── observed_time
 ├── published_time
 ├── acquired_time
 ├── source_id
 ├── dataset_id
 ├── quality_profile
 ├── classification
 └── metadata
```

---

# 25. Observation Subject

Every Observation SHOULD refer to a subject.

A subject may be:

```text
CanonicalEntity
Commodity
CurrencyPair
Market
Country
Location
Indicator
Route
Regulation
Product
Organisation
```

The physical representation may later use typed references.

---

# 26. Measurement

`Measurement` is a specialised form of Observation where the value is numeric or quantitatively measurable.

```text
Observation
     ▲
     │
Measurement
```

Examples:

```text
price
temperature
rainfall
volume
GDP
exchange rate
weight
distance
```

---

# 27. State Observation

An Observation MAY instead represent state.

Examples:

```text
company.status = ACTIVE

regulation.status = EFFECTIVE

port.status = DISRUPTED
```

---

# 28. Observation Source Cardinality

```text
RawRecord
 * ─────── * Observation
```

One raw record may produce several observations.

One canonical observation may derive from multiple raw records.

Therefore the relationship SHALL be modelled through explicit lineage rather than a single foreign key.

---

# 29. ProvenanceRecord

A `ProvenanceRecord` SHALL represent derivation between entities.

Canonical form:

```text
ProvenanceRecord
 ├── id
 ├── input_reference
 ├── output_reference
 ├── transformation_type
 ├── transformation_version
 ├── actor_type
 ├── actor_reference
 ├── executed_at
 └── metadata
```

This provides the basis of lineage.

---

# 30. Provenance Chain

Pulse SHALL be capable of traversing:

```text
Recommendation
   ↓
Insight
   ↓
Analysis
   ↓
Evidence
   ↓
Observation
   ↓
RawRecord
   ↓
Acquisition
   ↓
Dataset
   ↓
DataSource
   ↓
Source
```

---

# 31. Evidence

`Evidence` is a canonical reference to information used to support or contradict an analytical assertion.

Evidence may reference:

```text
Observation
Document
External publication
Baobab event
Existing insight
Model result
```

Evidence does not copy the underlying item.

It references and contextualises it.

---

# 32. Evidence Structure

```text
Evidence
 ├── id
 ├── referenced_object
 ├── role
 ├── relevance
 ├── direction
 ├── weight
 ├── quality
 ├── valid_from
 ├── valid_to
 └── metadata
```

---

# 33. EvidenceDirection

```text
SUPPORTS
CONTRADICTS
NEUTRAL
CONTEXTUAL
```

This is essential for preserving conflicting evidence.

---

# 34. EvidenceSet

An `EvidenceSet` groups evidence used for a particular analysis, signal, insight or recommendation.

```text
EvidenceSet
 1 ─────── * Evidence
```

An Evidence MAY participate in several EvidenceSets.

---

# 35. Evidence Cardinality

```text
Observation
 1 ─────── * Evidence

EvidenceSet
 * ─────── * Evidence
```

---

# 36. QualityAssessment

A `QualityAssessment` captures the assessed quality of a source object.

Possible dimensions:

```text
accuracy
completeness
timeliness
consistency
authority
corroboration
method_quality
```

Each assessment SHALL indicate:

```text
method
score
scale
assessor
assessed_at
```

---

# 37. Confidence

Confidence is distinct from source quality.

A high-quality observation may still support a low-confidence prediction.

Canonical confidence MAY consist of:

```text
confidence_score
confidence_band
confidence_method
confidence_version
```

Possible bands:

```text
VERY_LOW
LOW
MODERATE
HIGH
VERY_HIGH
```

---

# 38. Signal

A `Signal` represents a detected condition, change, threshold, correlation or pattern judged potentially meaningful.

Examples:

```text
ZAR depreciation exceeds 5%

coffee imports rising for three consecutive periods

port delays exceed historical baseline

regulatory deadline within 30 days
```

---

# 39. Signal Structure

```text
Signal
 ├── id
 ├── signal_type
 ├── subject_reference
 ├── evidence_set_id
 ├── detection_method
 ├── detection_version
 ├── severity
 ├── confidence
 ├── first_detected_at
 ├── last_detected_at
 ├── valid_from
 ├── valid_to
 ├── status
 └── metadata
```

---

# 40. SignalType

Possible types include:

```text
THRESHOLD
CHANGE
TREND
ANOMALY
CORRELATION
EVENT
DIVERGENCE
CONVERGENCE
RISK_INDICATOR
OPPORTUNITY_INDICATOR
```

---

# 41. Trend

A `Trend` is a specialised Signal representing directional persistence.

```text
Signal
  ▲
  │
Trend
```

Examples:

```text
UPWARD
DOWNWARD
STABLE
ACCELERATING
DECELERATING
CYCLICAL
```

---

# 42. Anomaly

An `Anomaly` is a specialised Signal representing statistically, operationally or contextually unusual behaviour.

```text
Signal
  ▲
  │
Anomaly
```

An anomaly is not automatically a risk.

---

# 43. Signal Lifecycle

```text
DETECTED
   ↓
ACTIVE
   ↓
CONFIRMED
   ↓
RESOLVED
```

Alternative paths:

```text
DETECTED → DISMISSED

ACTIVE → EXPIRED

CONFIRMED → SUPERSEDED
```

---

# 44. Analysis

An `Analysis` represents an explicit analytical execution over evidence.

Examples:

```text
year-over-year comparison
landed-cost calculation
regression model
forecasting model
LLM-assisted synthesis
rule evaluation
geospatial proximity analysis
```

---

# 45. Analysis Structure

```text
Analysis
 ├── id
 ├── analysis_type
 ├── method
 ├── method_version
 ├── evidence_set_id
 ├── parameters
 ├── model_version_id
 ├── started_at
 ├── completed_at
 ├── status
 ├── result_reference
 ├── reproducibility_profile
 └── metadata
```

---

# 46. AnalysisType

Possible types:

```text
DESCRIPTIVE
DIAGNOSTIC
COMPARATIVE
STATISTICAL
FORECAST
SCENARIO
GEOSPATIAL
SEMANTIC
RULE_BASED
ML
LLM_ASSISTED
HYBRID
```

---

# 47. Analysis Cardinality

```text
EvidenceSet
 1 ─────── * Analysis

Analysis
 1 ─────── * Insight
```

An Insight MAY reference multiple analyses where synthesis occurs.

---

# 48. Insight

An `Insight` is a contextualised interpretation supported by evidence and analysis.

Example:

```text
South African specialty-coffee imports
are increasing while sourcing remains
concentrated in a small number of origins.
```

An Insight is more than a Signal because it contains interpretation.

---

# 49. Insight Structure

```text
Insight
 ├── id
 ├── title
 ├── statement
 ├── insight_type
 ├── subject_reference
 ├── evidence_set_id
 ├── analysis_references
 ├── confidence
 ├── significance
 ├── valid_from
 ├── valid_to
 ├── status
 └── metadata
```

---

# 50. InsightType

```text
MARKET
TRADE
FINANCIAL
OPERATIONAL
REGULATORY
SUPPLY_CHAIN
CUSTOMER
COMPETITIVE
MACROECONOMIC
GEOSPATIAL
WEATHER
STRATEGIC
OTHER
```

---

# 51. Insight Lifecycle

```text
DRAFT
  ↓
VALIDATED
  ↓
PUBLISHED
```

Possible terminal states:

```text
EXPIRED
SUPERSEDED
WITHDRAWN
REJECTED
```

---

# 52. Insight Supersession

Insights SHALL not normally be destructively overwritten.

```text
Insight v1
   ↓
SUPERSEDED_BY
   ↓
Insight v2
```

This preserves historical decision context.

---

# 53. Opportunity

An `Opportunity` represents a condition whereby evidence suggests possible strategic, commercial, operational or financial benefit.

---

# 54. Opportunity Structure

```text
Opportunity
 ├── id
 ├── title
 ├── description
 ├── opportunity_type
 ├── insight_references
 ├── evidence_set_id
 ├── tenant_scope
 ├── market
 ├── geography
 ├── estimated_value
 ├── value_currency
 ├── value_range
 ├── time_horizon
 ├── confidence
 ├── urgency
 ├── feasibility
 ├── status
 └── metadata
```

---

# 55. OpportunityType

```text
MARKET_ENTRY
EXPORT
IMPORT
PRODUCT
PRICING
SUPPLY
PROCUREMENT
PARTNERSHIP
INVESTMENT
COST_REDUCTION
CAPACITY
REGULATORY
STRATEGIC
OTHER
```

---

# 56. Opportunity Lifecycle

```text
DETECTED
   ↓
QUALIFIED
   ↓
ASSESSED
   ↓
PROPOSED
   ↓
ACTIONED
```

Possible exits:

```text
DISMISSED
EXPIRED
LOST
SUPERSEDED
```

---

# 57. Risk

A `Risk` represents uncertainty with potentially negative impact.

---

# 58. Risk Structure

```text
Risk
 ├── id
 ├── title
 ├── description
 ├── risk_type
 ├── insight_references
 ├── evidence_set_id
 ├── likelihood
 ├── impact
 ├── severity
 ├── exposure
 ├── time_horizon
 ├── confidence
 ├── status
 └── metadata
```

---

# 59. RiskType

```text
MARKET
FX
COUNTRY
SUPPLIER
CUSTOMER
WEATHER
LOGISTICS
REGULATORY
FINANCIAL
OPERATIONAL
CYBER
REPUTATIONAL
STRATEGIC
OTHER
```

---

# 60. Risk Lifecycle

```text
IDENTIFIED
    ↓
ASSESSED
    ↓
MONITORED
    ↓
MITIGATED
```

Possible states:

```text
ACCEPTED
MATERIALISED
CLOSED
EXPIRED
SUPERSEDED
```

---

# 61. Forecast

A `Forecast` represents a prediction concerning a future state or measurement.

---

# 62. Forecast Structure

```text
Forecast
 ├── id
 ├── target_reference
 ├── target_metric
 ├── forecast_origin
 ├── target_time
 ├── horizon
 ├── predicted_value
 ├── lower_bound
 ├── upper_bound
 ├── confidence
 ├── model_version_id
 ├── evidence_set_id
 ├── generated_at
 └── metadata
```

---

# 63. Forecast Outcome Comparison

When the target period passes:

```text
Forecast
   ↓
Actual Observation
   ↓
ForecastEvaluation
```

This enables:

```text
error
bias
accuracy
calibration
```

to be measured.

---

# 64. Recommendation

A `Recommendation` represents a proposed action derived from intelligence.

---

# 65. Recommendation Structure

```text
Recommendation
 ├── id
 ├── title
 ├── action
 ├── rationale
 ├── opportunity_references
 ├── risk_references
 ├── insight_references
 ├── evidence_set_id
 ├── expected_benefit
 ├── expected_cost
 ├── urgency
 ├── confidence
 ├── authority_requirement
 ├── status
 └── metadata
```

---

# 66. Recommendation Lifecycle

```text
DRAFT
  ↓
READY
  ↓
PRESENTED
  ↓
UNDER_REVIEW
```

Possible decisions:

```text
ACCEPTED
REJECTED
MODIFIED
DEFERRED
EXPIRED
WITHDRAWN
```

---

# 67. Recommendation Authority

Recommendations SHALL carry an authority profile.

Possible levels:

```text
INFORMATIONAL
ADVISORY
HUMAN_APPROVAL_REQUIRED
POLICY_AUTOMATABLE
AUTOMATED
```

The initial default SHALL be:

```text
HUMAN_APPROVAL_REQUIRED
```

for consequential actions.

---

# 68. Decision

A `Decision` records the response to a Recommendation or strategic issue.

---

# 69. Decision Structure

```text
Decision
 ├── id
 ├── recommendation_id
 ├── decision_type
 ├── decision
 ├── rationale
 ├── decided_by
 ├── decided_at
 ├── authority_reference
 ├── status
 └── metadata
```

---

# 70. DecisionType

```text
ACCEPT
REJECT
MODIFY
DEFER
REQUEST_MORE_EVIDENCE
CANCEL
```

---

# 71. Decision Cardinality

```text
Recommendation
 1 ─────── * Decision
```

Normally one final decision is effective at any given time, but decision history SHALL be preserved.

---

# 72. Action

Where implementation requires explicit tracking, a Decision MAY create one or more Actions.

```text
Decision
 1 ─────── * Action
```

An Action may execute in:

```text
MedusaJS
iDempiere
Payload CMS
external workflow
human process
```

Pulse SHALL not assume ownership of the operational execution.

---

# 73. Outcome

An `Outcome` represents what happened after a Decision or Action.

Examples:

```text
supplier contracted

market entry abandoned

gross margin improved

forecast missed

risk materialised

campaign increased sales
```

---

# 74. Outcome Structure

```text
Outcome
 ├── id
 ├── decision_id
 ├── action_reference
 ├── outcome_type
 ├── description
 ├── measured_value
 ├── unit
 ├── observed_at
 ├── evidence_set_id
 └── metadata
```

---

# 75. Feedback

`Feedback` records an assessment of intelligence usefulness, accuracy or decision performance.

Feedback may originate from:

```text
human
system
model evaluation
business outcome
```

---

# 76. Feedback Structure

```text
Feedback
 ├── id
 ├── target_reference
 ├── feedback_type
 ├── rating
 ├── comment
 ├── evidence_set_id
 ├── submitted_by
 ├── submitted_at
 └── metadata
```

---

# 77. FeedbackType

```text
ACCURACY
RELEVANCE
TIMELINESS
USEFULNESS
CONFIDENCE_CALIBRATION
OUTCOME_SUCCESS
FALSE_POSITIVE
FALSE_NEGATIVE
OTHER
```

---

# 78. Closed Intelligence Loop

The complete canonical learning cycle is:

```text
Observation
    ↓
Evidence
    ↓
Signal
    ↓
Analysis
    ↓
Insight
    ↓
Opportunity / Risk / Forecast
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
    ↓
Quality / Model / Method Improvement
```

---

# 79. Indicator

An `Indicator` represents a defined metric that may be observed repeatedly.

Examples:

```text
GDP growth
consumer inflation
coffee export volume
inventory turnover
USD/ZAR exchange rate
```

---

# 80. Indicator Structure

```text
Indicator
 ├── id
 ├── code
 ├── name
 ├── definition
 ├── unit
 ├── frequency
 ├── methodology
 ├── source_profile
 └── metadata
```

---

# 81. Indicator Cardinality

```text
Indicator
 1 ─────── * Observation
```

An Observation may reference one Indicator.

---

# 82. Commodity

Commodity SHOULD reuse the platform canonical entity model where appropriate.

Pulse-specific commodity metadata may include:

```text
classification
grade
variety
benchmark
exchange
unit
origin
```

---

# 83. CurrencyPair

FX observations require a canonical CurrencyPair concept.

```text
CurrencyPair
 ├── base_currency
 └── quote_currency
```

The ordering is semantically significant.

```text
USD/ZAR
```

is not equivalent to:

```text
ZAR/USD
```

although values are mathematically related.

---

# 84. Market

Pulse SHALL reuse the Control Plane `Market`.

Intelligence can therefore be scoped to:

```text
country
commercial market
sales region
economic region
digital estate
```

without inventing independent Pulse market semantics.

---

# 85. Location

Canonical location references SHALL support hierarchical geography.

```text
World
 ↓
Continent
 ↓
Country
 ↓
Province / Region
 ↓
District
 ↓
Locality
 ↓
Site
```

Geospatial objects MAY also carry geometry.

---

# 86. Temporal Model

Pulse SHALL distinguish:

```text
valid_time
observed_time
published_time
effective_time
retrieved_time
processed_time
created_time
superseded_time
```

No generic `date` field SHALL replace these semantics.

---

# 87. Valid Time

`valid_time` answers:

> During what real-world period is this statement true?

---

# 88. Observed Time

`observed_time` answers:

> When was the phenomenon actually measured or observed?

---

# 89. Published Time

`published_time` answers:

> When did the source make the information available?

---

# 90. Retrieved Time

`retrieved_time` answers:

> When did Pulse acquire the source information?

---

# 91. Effective Time

`effective_time` is particularly important for:

```text
regulations
tariffs
contracts
policy changes
```

It answers:

> When does this rule or state actually take effect?

---

# 92. System Time

System time records when Pulse believed or stored a fact.

This enables bitemporal reasoning.

---

# 93. Temporal Interval

Where applicable:

```text
valid_from
valid_to
```

SHALL represent half-open intervals:

```text
[valid_from, valid_to)
```

unless a child contract explicitly specifies another convention.

---

# 94. Open-Ended Validity

An unknown end date SHALL be represented as open-ended rather than fabricated.

---

# 95. Supersession

Canonical objects that can be revised SHOULD support:

```text
supersedes_id
superseded_by_id
```

or equivalent temporal relationships.

---

# 96. Status versus Validity

Lifecycle status and temporal validity are distinct.

Example:

```text
Insight.status = PUBLISHED
```

does not mean the Insight remains temporally valid forever.

---

# 97. Classification

Every material intelligence object SHALL have a data classification.

Canonical values:

```text
PUBLIC
BAOBAB_INTERNAL
TENANT
CONFIDENTIAL
RESTRICTED
```

---

# 98. Classification Inheritance

A derived object's classification SHALL be at least as restrictive as its most restrictive contributing evidence unless an explicit declassification policy applies.

Example:

```text
PUBLIC evidence
+
CONFIDENTIAL tenant financial data
=
CONFIDENTIAL insight
```

not:

```text
PUBLIC insight
```

---

# 99. Tenant Scope

Each object SHALL be capable of one of the following scopes:

```text
GLOBAL
PLATFORM
TENANT
CONTEXT
PRIVATE
```

---

# 100. Public Evidence and Private Intelligence

Public observations MAY legitimately produce tenant-private intelligence.

Example:

```text
public FX rate
+
public coffee benchmark
+
Thamani private procurement cost
    ↓
Thamani confidential margin insight
```

---

# 101. Derived Object Classification

The derived object's classification SHALL be computed according to policy and explicitly stored.

---

# 102. ExternalReference

Any source entity that carries provider-specific identity SHALL map through the Baobab platform `ExternalReference` contract.

Example:

```text
CanonicalEntity:
    Uganda

ExternalReferences:
    ISO: UG
    World Bank: UGA
    Provider-X: 800
```

Pulse SHALL not maintain isolated mapping conventions.

---

# 103. Mapping

Mappings between external source semantics and canonical semantics SHALL use shared mapping contracts.

This includes:

```text
country codes
commodity codes
HS classifications
company identifiers
market identifiers
currency identifiers
indicator identifiers
```

---

# 104. Taxonomy

Pulse MAY maintain intelligence-specific taxonomies for:

```text
risk types
opportunity types
signal types
analysis types
industry classifications
topics
news categories
```

Taxonomies SHALL be versionable.

---

# 105. Classification Versioning

External classification schemes SHALL preserve version.

Examples:

```text
HS2017
HS2022
ISIC Rev.4
NAICS 2022
```

A code SHALL not be interpreted outside its classification version.

---

# 106. Transformation

A transformation represents the process that converts one representation into another.

Canonical transformation types include:

```text
PARSE
NORMALISE
MAP
ENRICH
AGGREGATE
FILTER
DEDUPE
RESOLVE
CLASSIFY
EXTRACT
CALCULATE
MODEL
SYNTHESISE
```

---

# 107. Transformation Version

Every transformation that materially affects semantic output SHALL be versioned.

---

# 108. Actor

Provenance SHALL identify whether an operation was performed by:

```text
SYSTEM
HUMAN
MODEL
EXTERNAL_SOURCE
BAOBAB_ENGINE
```

---

# 109. Model

A `Model` represents an analytical or AI capability.

Examples:

```text
FX volatility model
demand forecast model
LLM summarisation model
entity matching model
risk-scoring model
```

---

# 110. ModelVersion

```text
Model
 1 ─────── * ModelVersion
```

A ModelVersion SHALL preserve:

```text
version
provider
algorithm
configuration
training_reference
release_date
status
```

---

# 111. ModelRun

A `ModelRun` records one execution.

```text
ModelVersion
 1 ─────── * ModelRun
```

Attributes:

```text
input_reference
parameters
started_at
completed_at
result_reference
status
cost
usage
```

---

# 112. Model Lifecycle

```text
DRAFT
  ↓
VALIDATED
  ↓
APPROVED
  ↓
ACTIVE
  ↓
DEPRECATED
  ↓
RETIRED
```

---

# 113. Method

Not all intelligence requires a model.

A method may be:

```text
formula
rule
SQL aggregation
statistical test
human analysis
ML model
LLM
```

Pulse SHALL not force deterministic methods into the Model abstraction unnecessarily.

---

# 114. IntelligenceJob

`IntelligenceJob` represents scheduled or requested analytical work.

Examples:

```text
daily FX scan
weekly market opportunity analysis
monthly supplier risk review
regulatory-change sweep
```

---

# 115. IntelligenceJob Lifecycle

```text
PENDING
  ↓
SCHEDULED
  ↓
RUNNING
  ↓
SUCCEEDED
```

Alternatives:

```text
FAILED
CANCELLED
PARTIAL
RETRYING
```

---

# 116. IntelligenceProduct

An `IntelligenceProduct` represents a reusable composition of analytical capabilities.

Examples:

```text
Market Pulse
Country Pulse
FX Pulse
Commodity Pulse
Opportunity Radar
Risk Radar
Executive Brief
```

---

# 117. IntelligenceProduct Definition

```text
IntelligenceProduct
 ├── id
 ├── name
 ├── product_type
 ├── scope
 ├── configuration
 ├── schedule
 ├── output_profile
 ├── audience
 └── status
```

---

# 118. IntelligenceProductRun

Each execution SHALL be independently recorded.

```text
IntelligenceProduct
 1 ─────── * IntelligenceProductRun
```

---

# 119. IntelligenceProduct Composition

An intelligence product MAY consume:

```text
Signals
Insights
Opportunities
Risks
Forecasts
Recommendations
```

without changing their ownership.

---

# 120. Correlation

Correlation between observations SHALL be representable explicitly.

A correlation result SHALL identify:

```text
variables
method
coefficient
period
sample
significance
```

Correlation MUST NOT automatically become causation.

---

# 121. Causal Assertion

If Pulse ever represents causal claims, they SHALL use a stronger explicit semantic type than ordinary Insight.

Such assertions SHOULD preserve:

```text
causal_method
assumptions
evidence
counterfactual basis
confidence
```

---

# 122. Contradiction

Contradictory intelligence SHALL be modelled explicitly.

Possible relation:

```text
CONTRADICTS
```

between:

```text
Evidence
Insight
Forecast
```

---

# 123. Agreement

Similarly:

```text
SUPPORTS
CORROBORATES
```

may represent independent agreement.

---

# 124. Relationships

Generic semantic relationships MAY be represented through an `IntelligenceRelation`.

```text
IntelligenceRelation
 ├── subject_reference
 ├── relation_type
 ├── object_reference
 ├── evidence_set_id
 ├── confidence
 └── valid_time
```

---

# 125. RelationType

Examples:

```text
SUPPORTS
CONTRADICTS
CORROBORATES
CAUSES
CORRELATES_WITH
DERIVED_FROM
SUPERSEDES
RELATED_TO
AFFECTS
EXPOSES
MITIGATES
```

---

# 126. Cardinality Summary

Core cardinalities are:

```text
Source
  1 ─── *

DataSource
  1 ─── *

Dataset
  1 ─── *

DatasetVersion

Dataset
  1 ─── *

Acquisition
  1 ─── *

RawRecord

RawRecord
  * ─── *

Observation

Observation
  1 ─── *

Evidence

EvidenceSet
  * ─── *

Evidence

EvidenceSet
  1 ─── *

Analysis

Analysis
  * ─── *

Insight

Insight
  * ─── *

Opportunity

Insight
  * ─── *

Risk

Insight
  * ─── *

Forecast

Opportunity / Risk / Forecast
  * ─── *

Recommendation

Recommendation
  1 ─── *

Decision

Decision
  1 ─── *

Outcome

Outcome
  1 ─── *

Feedback
```

---

# 127. Derivation Cardinality

No analytical object SHALL be constrained to exactly one evidence item.

Real intelligence commonly requires many-to-many derivation.

---

# 128. Parent-Child Inheritance Rule

Specialised concepts SHALL inherit canonical semantics from their parents.

Examples:

```text
Measurement IS-A Observation

Trend IS-A Signal

Anomaly IS-A Signal
```

The physical implementation MAY use composition rather than class inheritance, but semantic inheritance remains normative.

---

# 129. No Semantic Duplication

Child contracts SHALL not redefine:

```text
confidence
classification
tenant context
provenance
temporal semantics
```

independently for each entity.

Shared value objects shall be used.

---

# 130. Canonical Value Objects

The implementation SHALL define reusable canonical value objects for at least:

```text
TemporalContext
TenantContext
GeographicContext
MarketContext
Confidence
QualityProfile
Classification
Money
Quantity
Unit
Reference
Provenance
LifecycleStatus
```

---

# 131. Money

Money SHALL always preserve:

```text
amount
currency
```

A naked decimal SHALL not represent monetary value.

---

# 132. Quantity

Quantities SHALL preserve:

```text
value
unit
```

where units are explicit.

---

# 133. Unit Conversion

Unit conversion SHALL be explicit and traceable.

Example:

```text
60 kg bag
→
kilogram
```

shall produce a transformation record if the converted value is persisted.

---

# 134. Currency Conversion

Currency conversion SHALL preserve:

```text
source_amount
source_currency
target_amount
target_currency
FX observation
conversion_time
```

---

# 135. Missing Values

Pulse SHALL distinguish:

```text
UNKNOWN
NOT_AVAILABLE
NOT_APPLICABLE
WITHHELD
NOT_COLLECTED
```

where the source permits such distinctions.

A missing value SHALL not default to zero.

---

# 136. Null Semantics

Database `NULL` alone SHALL not encode every semantic reason for absence where the reason materially affects interpretation.

---

# 137. Precision

Numeric observations SHALL preserve source precision where material.

Pulse SHALL not falsely imply greater precision than the source provides.

---

# 138. Revision

An Observation MAY be revised by its originating source.

Revisions SHALL result in:

```text
new canonical observation version
```

or equivalent temporal history.

The previous published state SHALL remain reconstructable.

---

# 139. Correction

A Pulse-generated error correction SHALL be distinguishable from an upstream source revision.

---

# 140. Duplicate

Exact duplicate acquisition SHALL not create semantically duplicated canonical observations.

However, independent sources reporting the same value remain separate evidence.

---

# 141. Idempotency

Canonical creation workflows SHALL support stable idempotency keys for repeated ingestion.

---

# 142. Freshness

Objects whose usefulness decays SHALL support freshness policies.

```text
fresh_until
```

or computed equivalent.

---

# 143. Staleness

Staleness SHALL not automatically delete intelligence.

It changes confidence or usability according to policy.

---

# 144. Expiration

Some entities may enter:

```text
EXPIRED
```

when their operational relevance ends.

Historical retention remains separate.

---

# 145. Deletion

Hard deletion of evidence-backed intelligence SHOULD be exceptional.

Normal lifecycle transitions should favour:

```text
WITHDRAWN
RETIRED
SUPERSEDED
EXPIRED
```

because auditability matters.

---

# 146. Retention

Retention SHALL be governed by:

```text
classification
licensing
source terms
tenant policy
legal obligations
operational value
```

---

# 147. Canonical Event Mapping

Every major entity lifecycle MAY emit canonical events.

Examples:

```text
pulse.observation.created
pulse.observation.revised

pulse.signal.detected
pulse.signal.resolved

pulse.insight.published
pulse.insight.superseded

pulse.opportunity.detected

pulse.risk.identified

pulse.forecast.created
pulse.forecast.evaluated

pulse.recommendation.presented

pulse.decision.recorded

pulse.outcome.recorded

pulse.feedback.recorded
```

---

# 148. Event Payload Rule

Events SHALL reference canonical entities.

They SHALL NOT attempt to serialize arbitrary entire database records.

---

# 149. Event Identity

Every event SHALL carry:

```text
event_id
event_type
event_version
occurred_at
correlation_id
causation_id
tenant_id
context_id
subject_id
```

where applicable.

---

# 150. Read Models

Physical implementations MAY create denormalised read models for:

```text
dashboards
search
reports
market summaries
alert feeds
```

but read models SHALL not redefine canonical semantics.

---

# 151. Search Indexes

Search documents are projections.

They are never canonical systems of record.

---

# 152. Vector Representations

Embeddings MAY be generated for:

```text
news
documents
insights
evidence
```

but embeddings SHALL be treated as derived indexes.

They SHALL not replace canonical content or provenance.

---

# 153. Natural Language

LLM-generated prose may represent a human-readable rendering of:

```text
Insight
Recommendation
IntelligenceProduct
```

but the structured canonical entity remains authoritative.

---

# 154. AI Citation Rule

An LLM-generated analysis SHALL retain references to the EvidenceSet that grounded the output.

---

# 155. Unverified AI Output

AI output not yet validated SHALL have explicit status such as:

```text
DRAFT
UNVERIFIED
```

and SHALL not silently become published intelligence.

---

# 156. Human Validation

Human validation MAY increase lifecycle status but SHALL NOT erase model provenance.

---

# 157. Decision Authority

Decision identity SHALL reference the canonical actor authorised to make the decision.

A model cannot claim human decision authority.

---

# 158. Automation Policy

Automated Decisions SHALL reference an explicit policy identifier.

---

# 159. Explainability Contract

Every published Recommendation SHALL be able to expose:

```text
supporting evidence
contradictory evidence
source provenance
analytical method
confidence
assumptions
validity
```

---

# 160. Audit Reconstruction

Given a Decision, Pulse SHALL be able to reconstruct:

```text
Decision
 ↓
Recommendation
 ↓
Opportunity/Risk/Forecast
 ↓
Insight
 ↓
Analysis
 ↓
EvidenceSet
 ↓
Evidence
 ↓
Observation
 ↓
RawRecord
 ↓
Source
```

---

# 161. Core Invariant

No material Recommendation SHOULD exist without:

```text
Recommendation
 → at least one Insight
 → at least one EvidenceSet
 → at least one Evidence
```

unless explicitly classified as human-authored and unsupported.

---

# 162. Evidence Integrity Invariant

Every Evidence object SHALL reference an existing canonical or external evidence object.

Dangling evidence references are invalid.

---

# 163. Temporal Integrity Invariant

Where:

```text
valid_from
valid_to
```

are both defined:

```text
valid_from < valid_to
```

MUST hold.

---

# 164. Source Integrity Invariant

Every acquired RawRecord SHALL trace to:

```text
Acquisition
→ Dataset
→ DataSource
→ Source
```

---

# 165. Model Integrity Invariant

Every ModelRun SHALL reference exactly one ModelVersion.

---

# 166. Forecast Integrity Invariant

A Forecast SHALL identify:

```text
forecast origin
target period
```

The target period must occur after or at the forecast origin according to the forecast semantics.

---

# 167. Classification Integrity Invariant

No derived object SHALL have a less restrictive classification than permitted by its contributing evidence and applicable policy.

---

# 168. Tenant Integrity Invariant

Tenant-scoped evidence SHALL not participate in another tenant's derived intelligence unless an authorised aggregation or sharing policy explicitly permits it.

---

# 169. Canonical Identity Invariant

External IDs SHALL never substitute for Pulse canonical IDs.

---

# 170. Immutability Invariant

Historical provenance edges SHALL not be destructively rewritten merely because current interpretation changes.

---

# 171. Idempotency Invariant

Repeated delivery of the same external event SHALL not create duplicate canonical semantic events.

---

# 172. Confidence Invariant

Confidence SHALL identify its scoring method.

A bare value such as:

```text
0.87
```

without a defined scoring method is insufficient for consequential intelligence.

---

# 173. Confidence Aggregation

Confidence aggregation SHALL be method-specific.

Pulse SHALL NOT average arbitrary confidence scores unless the method defines that operation.

---

# 174. Source Trust Inheritance

Source trust SHALL influence intelligence confidence but SHALL not deterministically dictate it.

---

# 175. Contradictory Evidence Rule

Contradictory Evidence MUST remain visible to downstream analyses unless explicitly excluded by a documented method.

---

# 176. Lifecycle Independence

Source, Observation, Insight and Recommendation lifecycles SHALL remain independent.

For example:

```text
Source = ACTIVE
Observation = SUPERSEDED
Insight = EXPIRED
Recommendation = REJECTED
```

is valid.

---

# 177. Cross-Domain Intelligence

The canonical model SHALL support combining multiple data domains.

Example:

```text
FX observation
+
Commodity observation
+
Weather signal
+
Trade observation
+
ERP cost observation
+
News evidence
     ↓
Opportunity
```

No data domain receives privileged canonical status.

---

# 178. Example: FX Opportunity Chain

```text
Source:
    Central Bank

DataSource:
    FX API

Dataset:
    USD/ZAR rates

RawRecord:
    source JSON

Observation:
    USD/ZAR = 18.40

Signal:
    ZAR depreciated 7% over 30 days

Insight:
    imported inventory costs are rising

Risk:
    margin compression likely

Recommendation:
    review pricing and hedging

Decision:
    accept

Outcome:
    new pricing implemented

Feedback:
    margin preserved
```

---

# 179. Example: Coffee Trade Opportunity

```text
Trade Observation:
    South African green-coffee imports rising

Commodity Observation:
    Ugandan origin price competitive

FX Observation:
    UGX/ZAR conditions favourable

Registry Evidence:
    additional potential suppliers active

News Evidence:
    production outlook stable

Weather Evidence:
    harvest conditions favourable
```

↓

```text
Signal:
    potential supply opportunity
```

↓

```text
Insight:
    Uganda may offer commercially attractive
    incremental supply into South Africa
```

↓

```text
Opportunity:
    Uganda → South Africa green coffee
```

↓

```text
Recommendation:
    initiate supplier qualification
```

↓

```text
Decision:
    request supplier due diligence
```

↓

```text
Outcome:
    supply agreement / rejection
```

---

# 180. Example: Regulatory Chain

```text
Raw publication
      ↓
Regulatory Observation
      ↓
effective date identified
      ↓
Signal:
    tariff increase approaching
      ↓
Insight:
    imported landed cost likely increases
      ↓
Risk
      ↓
Recommendation:
    review procurement timing
```

---

# 181. Example: Weather Supply Risk

```text
Weather observations
       +
production geography
       +
crop calendar
       +
historical yields
       ↓
Signal:
    sustained rainfall deficit
       ↓
Forecast:
    lower production possible
       ↓
Risk:
    supply shortage
       ↓
Recommendation:
    diversify procurement
```

---

# 182. Logical Aggregate Boundaries

The physical implementation SHOULD consider the following aggregate roots:

```text
Source
Dataset
Acquisition
Observation
EvidenceSet
Signal
Analysis
Insight
Opportunity
Risk
Forecast
Recommendation
Decision
Model
IntelligenceProduct
```

Not every subordinate concept needs an independent transactional aggregate.

---

# 183. Aggregate Isolation

A Source update SHALL not require rewriting historical Observations.

Likewise, an Insight revision SHALL not mutate historical Evidence.

---

# 184. Domain Service Candidates

The canonical model implies domain services such as:

```text
SourceRegistry
AcquisitionService
NormalizationService
EntityResolutionService
ProvenanceService
EvidenceService
SignalDetectionService
AnalysisService
InsightService
OpportunityService
RiskService
ForecastService
RecommendationService
DecisionService
FeedbackService
ConfidenceService
QualityService
```

These are logical service boundaries, not necessarily deployable microservices.

---

# 185. Resolver Services

Pulse will require canonical resolvers for:

```text
entity
country
market
currency
commodity
HS classification
indicator
organisation
location
```

Canonical platform concepts SHOULD resolve through Baobab Control Plane or shared contracts where applicable.

---

# 186. Repository Ownership

Semantic ownership shall be:

```text
nabhold/shared
    canonical schemas
    enums
    event contracts
    cross-engine identifiers

nabhold/baobab-cp
    platform entity identities
    market/context/mapping

nabhold/baobab-pulse
    intelligence-domain implementation
```

---

# 187. Physical Model Independence

This document deliberately does not prescribe:

```text
table names
indexes
PostgreSQL schemas
Python class names
API URL paths
event payload schemas
```

Those shall derive from this canonical model.

---

# 188. Required Physical Derivations

This model SHALL next produce:

1. PostgreSQL physical data model.
2. Python package/interface specification.
3. OpenAPI resources.
4. AsyncAPI canonical events.
5. Source Adapter Contract.
6. Provenance schema.
7. Quality and Confidence schema.
8. Temporal model constraints.
9. Canonical enums.
10. Testable domain invariants.

---

# 189. Final Canonical Principle

The central semantic principle of Baobab Pulse is:

```text
DATA
is not
EVIDENCE

EVIDENCE
is not
A SIGNAL

A SIGNAL
is not
AN INSIGHT

AN INSIGHT
is not
AN OPPORTUNITY

AN OPPORTUNITY
is not
A RECOMMENDATION

A RECOMMENDATION
is not
A DECISION

A DECISION
is not
AN OUTCOME
```

Each represents a different level of interpretation and authority.

Preserving those distinctions is essential.

Without them, Pulse would blur:

```text
what happened
```

with:

```text
what we think it means
```

and eventually with:

```text
what somebody should do about it
```

That would make the system difficult to audit and unsafe to trust.

Baobab Pulse shall therefore preserve the full chain:

```text
SOURCE
   ↓
RAW FACT
   ↓
OBSERVATION
   ↓
EVIDENCE
   ↓
SIGNAL
   ↓
ANALYSIS
   ↓
INSIGHT
   ↓
OPPORTUNITY / RISK / FORECAST
   ↓
RECOMMENDATION
   ↓
DECISION
   ↓
OUTCOME
   ↓
FEEDBACK
```

This chain constitutes the canonical semantic backbone of the **Baobab Pulse Intelligence Engine**.
