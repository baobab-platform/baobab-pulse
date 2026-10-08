"""EvidenceRetrievalService (Qdrant refactor item 42) — fail-closed tenancy,
staleness detection against the current canonical version, and the
single-EvidenceSet hydration scope limit.

Fakes stand in for ``SemanticRetrievalPort``/``EvidenceSetHydrationPort`` —
both are structural ``Protocol``s, so no base class is needed — keeping this
a pure application-layer test with no real Qdrant/PostgreSQL involved.
"""

from __future__ import annotations

import pytest

from baobab_pulse.application.ports.semantic_retrieval_port import EvidenceRetrievalQuery, SemanticCandidate
from baobab_pulse.application.services.evidence_retrieval_service import EvidenceRetrievalService
from baobab_pulse.domain.evidence import Evidence, EvidenceSet
from baobab_pulse.domain.shared.enums import Classification, EvidenceDirection, TenantScope
from baobab_pulse.domain.shared.errors import InvariantViolation, TenantContextMissingError
from baobab_pulse.domain.shared.value_objects import Reference, TenantContext
from baobab_pulse.tenancy.context import bind_tenant_context


class _FakeSemanticRetrieval:
    def __init__(self, candidates: tuple[SemanticCandidate, ...]) -> None:
        self._candidates = candidates
        self.last_query: EvidenceRetrievalQuery | None = None

    async def retrieve_evidence(self, query: EvidenceRetrievalQuery) -> tuple[SemanticCandidate, ...]:
        self.last_query = query
        return self._candidates


class _FakeHydration:
    def __init__(
        self,
        *,
        current_versions: dict[str, int | None],
        sets: dict[str, tuple[EvidenceSet, dict[str, str]]],
    ) -> None:
        self._current_versions = current_versions
        self._sets = sets

    async def current_version(self, entity_id: str) -> int | None:
        return self._current_versions.get(entity_id)

    async def get_with_text(self, entity_id: str) -> tuple[EvidenceSet, dict[str, str]] | None:
        return self._sets.get(entity_id)


def _candidate(
    *, canonical_object_id: str = "evd_1", evidence_set_id: str = "evs_1", canonical_version: int = 1, score: float = 0.9
) -> SemanticCandidate:
    return SemanticCandidate(
        canonical_object_id=canonical_object_id,
        evidence_set_id=evidence_set_id,
        canonical_version=canonical_version,
        score=score,
    )


def _evidence_set(evidence_set_id: str, evidence_ids: tuple[str, ...]) -> EvidenceSet:
    tenant_context = TenantContext(tenant_id="tn_test01")
    return EvidenceSet(
        id=evidence_set_id,
        purpose="test",
        tenant_scope=TenantScope.TENANT,
        tenant_context=tenant_context,
        classification=Classification.TENANT,
        entries=tuple(
            Evidence(
                id=evidence_id,
                referenced_object=Reference(object_type="observation", object_id=f"obs_{evidence_id}"),
                direction=EvidenceDirection.SUPPORTS,
            )
            for evidence_id in evidence_ids
        ),
    )


async def test_search_raises_without_a_bound_tenant_context() -> None:
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(()), hydration=_FakeHydration(current_versions={}, sets={})
    )
    with pytest.raises(TenantContextMissingError):
        await service.search("anything")


async def test_search_flags_a_candidate_stale_when_the_canonical_version_has_advanced() -> None:
    semantic_retrieval = _FakeSemanticRetrieval((_candidate(canonical_version=7),))
    hydration = _FakeHydration(current_versions={"evs_1": 8}, sets={})
    service = EvidenceRetrievalService(semantic_retrieval=semantic_retrieval, hydration=hydration)

    with bind_tenant_context(TenantContext(tenant_id="tn_test01")):
        results = await service.search("query")

    assert len(results) == 1
    assert results[0].is_stale is True


async def test_search_does_not_flag_a_candidate_matching_the_current_canonical_version() -> None:
    semantic_retrieval = _FakeSemanticRetrieval((_candidate(canonical_version=7),))
    hydration = _FakeHydration(current_versions={"evs_1": 7}, sets={})
    service = EvidenceRetrievalService(semantic_retrieval=semantic_retrieval, hydration=hydration)

    with bind_tenant_context(TenantContext(tenant_id="tn_test01")):
        results = await service.search("query")

    assert len(results) == 1
    assert results[0].is_stale is False


async def test_search_drops_a_candidate_whose_source_no_longer_exists_canonically() -> None:
    semantic_retrieval = _FakeSemanticRetrieval((_candidate(evidence_set_id="evs_deleted"),))
    hydration = _FakeHydration(current_versions={"evs_deleted": None}, sets={})
    service = EvidenceRetrievalService(semantic_retrieval=semantic_retrieval, hydration=hydration)

    with bind_tenant_context(TenantContext(tenant_id="tn_test01")):
        results = await service.search("query")

    assert results == ()


async def test_search_binds_the_requester_clearance_and_scope_into_the_query() -> None:
    semantic_retrieval = _FakeSemanticRetrieval(())
    hydration = _FakeHydration(current_versions={}, sets={})
    service = EvidenceRetrievalService(semantic_retrieval=semantic_retrieval, hydration=hydration)

    with bind_tenant_context(TenantContext(tenant_id="tn_test01")):
        await service.search(
            "query", requester_clearance=Classification.RESTRICTED, evidence_set_id="evs_1", top_k=5
        )

    assert semantic_retrieval.last_query is not None
    assert semantic_retrieval.last_query.requester_clearance == Classification.RESTRICTED
    assert semantic_retrieval.last_query.evidence_set_id == "evs_1"
    assert semantic_retrieval.last_query.top_k == 5
    assert semantic_retrieval.last_query.tenant_context.tenant_id == "tn_test01"


async def test_hydrate_for_pipeline_raises_when_every_candidate_is_stale() -> None:
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(()), hydration=_FakeHydration(current_versions={}, sets={})
    )
    stale = (await _search_with([_candidate(canonical_version=1)], current_versions={"evs_1": 2}))[0]
    assert stale.is_stale is True

    with pytest.raises(InvariantViolation):
        await service.hydrate_for_pipeline([stale])


async def test_hydrate_for_pipeline_raises_when_candidates_span_multiple_evidence_sets() -> None:
    fresh_candidates = await _search_with(
        [_candidate(evidence_set_id="evs_1"), _candidate(canonical_object_id="evd_2", evidence_set_id="evs_2")],
        current_versions={"evs_1": 1, "evs_2": 1},
    )
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(()), hydration=_FakeHydration(current_versions={}, sets={})
    )

    with pytest.raises(InvariantViolation):
        await service.hydrate_for_pipeline(fresh_candidates)


async def test_hydrate_for_pipeline_raises_when_the_source_no_longer_exists_canonically() -> None:
    fresh_candidates = await _search_with([_candidate(evidence_set_id="evs_1")], current_versions={"evs_1": 1})
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(()),
        hydration=_FakeHydration(current_versions={"evs_1": 1}, sets={}),
    )

    with pytest.raises(InvariantViolation):
        await service.hydrate_for_pipeline(fresh_candidates)


async def test_hydrate_for_pipeline_narrows_text_to_only_the_matched_candidates() -> None:
    evidence_set = _evidence_set("evs_1", ("evd_1", "evd_2", "evd_3"))
    full_text = {"evd_1": "text one", "evd_2": "text two", "evd_3": "text three"}
    fresh_candidates = await _search_with(
        [
            _candidate(canonical_object_id="evd_1", evidence_set_id="evs_1"),
            _candidate(canonical_object_id="evd_2", evidence_set_id="evs_1"),
        ],
        current_versions={"evs_1": 1},
    )
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(()),
        hydration=_FakeHydration(current_versions={"evs_1": 1}, sets={"evs_1": (evidence_set, full_text)}),
    )

    hydrated_set, narrowed_text = await service.hydrate_for_pipeline(fresh_candidates)

    assert hydrated_set is evidence_set
    assert narrowed_text == {"evd_1": "text one", "evd_2": "text two"}


async def _search_with(candidates: list[SemanticCandidate], *, current_versions: dict[str, int | None]) -> tuple:
    service = EvidenceRetrievalService(
        semantic_retrieval=_FakeSemanticRetrieval(tuple(candidates)),
        hydration=_FakeHydration(current_versions=current_versions, sets={}),
    )
    with bind_tenant_context(TenantContext(tenant_id="tn_test01")):
        return await service.search("query")
