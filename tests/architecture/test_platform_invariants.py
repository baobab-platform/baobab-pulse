"""Required architectural tests #6-10 (platform brief item 129).

#1-5 (dependency-direction boundaries) live in
``test_dependency_boundaries.py``; #7 (tenant context) has its own focused
suite at ``tests/unit/tenancy/test_context.py`` — this module covers the
remaining three plus a credential-free smoke check for #6.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from haystack.components.generators.chat import MockChatGenerator

from baobab_pulse.application.services.research_mission_service import ResearchMissionService
from baobab_pulse.domain.evidence import Evidence, EvidenceSet
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, EvidenceDirection, TenantScope
from baobab_pulse.domain.shared.identifiers import new_id
from baobab_pulse.domain.shared.value_objects import Reference, TenantContext
from baobab_pulse.infrastructure.haystack.errors import PulseHaystackError, translate_exceptions
from baobab_pulse.infrastructure.haystack.pipeline_adapter import HaystackPipelineAdapter


async def test_6_core_pipeline_runs_with_no_model_provider_credentials(monkeypatch) -> None:
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PULSE_OPENAI_API_KEY", "PULSE_ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    tenant_context = TenantContext(tenant_id="tn_test01")
    evidence_id = new_id("evd")
    evidence_set = EvidenceSet(
        id=new_id("evs"),
        purpose="test",
        tenant_scope=TenantScope.TENANT,
        tenant_context=tenant_context,
        classification=Classification.TENANT,
        entries=(
            Evidence(
                id=evidence_id,
                referenced_object=Reference(object_type="observation", object_id="obs_1"),
                direction=EvidenceDirection.SUPPORTS,
            ),
        ),
    )
    mission = ResearchMission(
        id=new_id("rms"),
        title="test",
        research_question="q?",
        tenant_scope=TenantScope.TENANT,
        tenant_context=tenant_context,
        classification=Classification.TENANT,
    )
    reply = json.dumps([{"statement": "s", "claim_type": "INFERRED", "evidence_ids": [evidence_id]}])
    adapter = HaystackPipelineAdapter(chat_generator=MockChatGenerator(responses=reply))
    service = ResearchMissionService(pipeline_port=adapter)

    claims = await service.run_research_pipeline(
        mission, evidence_set, {evidence_id: "text"}, pipeline_name="test", pipeline_version="1"
    )
    assert len(claims) == 1


async def test_8_provider_exceptions_do_not_escape_as_raw_exceptions() -> None:
    @translate_exceptions("simulated Haystack failure")
    def _boom() -> None:
        raise RuntimeError("simulated provider outage")

    try:
        _boom()
    except PulseHaystackError as exc:
        assert "simulated Haystack failure failed" in str(exc)
        assert isinstance(exc.__cause__, RuntimeError)
    else:
        raise AssertionError("expected PulseHaystackError to be raised")


async def test_9_reference_pipeline_is_deterministic_across_runs() -> None:
    tenant_context = TenantContext(tenant_id="tn_test01")
    evidence_id = new_id("evd")
    evidence_set = EvidenceSet(
        id=new_id("evs"),
        purpose="test",
        tenant_scope=TenantScope.TENANT,
        tenant_context=tenant_context,
        classification=Classification.TENANT,
        entries=(
            Evidence(
                id=evidence_id,
                referenced_object=Reference(object_type="observation", object_id="obs_1"),
                direction=EvidenceDirection.SUPPORTS,
            ),
        ),
    )
    mission = ResearchMission(
        id=new_id("rms"),
        title="test",
        research_question="q?",
        tenant_scope=TenantScope.TENANT,
        tenant_context=tenant_context,
        classification=Classification.TENANT,
    )
    reply = json.dumps([{"statement": "the same statement every time", "claim_type": "INFERRED", "evidence_ids": [evidence_id]}])

    statements = set()
    for _ in range(3):
        adapter = HaystackPipelineAdapter(chat_generator=MockChatGenerator(responses=reply))
        service = ResearchMissionService(pipeline_port=adapter)
        claims = await service.run_research_pipeline(
            mission, evidence_set, {evidence_id: "text"}, pipeline_name="test", pipeline_version="1"
        )
        statements.add(claims[0].statement)

    assert statements == {"the same statement every time"}


def test_10_repository_builds_reproducibly_from_documented_inputs() -> None:
    """A locked, pinned dependency set is the actual reproducibility
    mechanism (item 88, ``uv.lock``) — this test only asserts the documented
    input exists and is internally consistent, not that a full container
    build is bit-for-bit reproducible (that is CI's job, per
    ``.github/workflows/foundation.yml``'s Trivy/reproducibility checks)."""
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "uv.lock").is_file(), "uv.lock must be committed for reproducible installs"
    assert (repo_root / ".python-version").is_file(), "the exact Python line must be pinned"

    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.14"' in pyproject
    # An exact pin, whichever version it is: a version bump (Dependabot included) must not need this test edited, but a floating
    # range must still fail it.
    assert re.search(r'"haystack-ai==\d+(\.\d+)*"', pyproject), "the Haystack version must be pinned, not left floating"
