from __future__ import annotations

import pytest

from baobab_pulse.domain.evidence import Evidence
from baobab_pulse.domain.shared.value_objects import (
    CrossEngineObjectReference,
    CrossEngineObjectVersion,
    CrossEngineReferenceMode,
    CrossEngineReferenceScope,
    CrossEngineVersionKind,
)


def test_tenant_identity_pinned_reference_matches_shared_semantics() -> None:
    reference = CrossEngineObjectReference(
        owner_engine_id="baobab-trade-docs",
        object_type="DOCUMENT_VERSION",
        object_id="tdocv_01",
        reference_mode=CrossEngineReferenceMode.IDENTITY_PINNED,
        scope=CrossEngineReferenceScope.TENANT,
        tenant_id="tn_test01",
    )
    assert reference.tenant_id == "tn_test01"


def test_version_pinned_reference_requires_owner_version() -> None:
    with pytest.raises(ValueError, match="require object_version"):
        CrossEngineObjectReference(
            owner_engine_id="baobab-pulse",
            object_type="EVIDENCE_SET",
            object_id="evset_01",
            reference_mode=CrossEngineReferenceMode.VERSION_PINNED,
            scope=CrossEngineReferenceScope.TENANT,
            tenant_id="tn_test01",
        )

    reference = CrossEngineObjectReference(
        owner_engine_id="baobab-pulse",
        object_type="EVIDENCE_SET",
        object_id="evset_01",
        reference_mode=CrossEngineReferenceMode.VERSION_PINNED,
        object_version=CrossEngineObjectVersion(
            kind=CrossEngineVersionKind.VERSION,
            value="4",
        ),
        scope=CrossEngineReferenceScope.TENANT,
        tenant_id="tn_test01",
    )
    assert reference.object_version is not None


def test_current_reference_rejects_version_and_platform_reference_rejects_tenant() -> None:
    with pytest.raises(ValueError, match="must not carry object_version"):
        CrossEngineObjectReference(
            owner_engine_id="baobab-cp",
            object_type="CAPABILITY",
            object_id="intelligence.evidence.search",
            reference_mode=CrossEngineReferenceMode.CURRENT,
            object_version=CrossEngineObjectVersion(
                kind=CrossEngineVersionKind.VERSION,
                value="1",
            ),
            scope=CrossEngineReferenceScope.PLATFORM,
        )

    with pytest.raises(ValueError, match="must not carry tenant_id"):
        CrossEngineObjectReference(
            owner_engine_id="baobab-cp",
            object_type="CAPABILITY",
            object_id="intelligence.evidence.search",
            reference_mode=CrossEngineReferenceMode.CURRENT,
            scope=CrossEngineReferenceScope.PLATFORM,
            tenant_id="tn_test01",
        )


def test_evidence_can_contextualise_foreign_object_without_copying_it() -> None:
    reference = CrossEngineObjectReference(
        owner_engine_id="baobab-regulations",
        object_type="REGULATORY_DECISION",
        object_id="regdec_01",
        reference_mode=CrossEngineReferenceMode.IDENTITY_PINNED,
        scope=CrossEngineReferenceScope.TENANT,
        tenant_id="tn_test01",
    )

    evidence = Evidence(id="evd_test", referenced_object=reference)

    assert evidence.referenced_object == reference
    assert not hasattr(evidence, "regulatory_decision")
