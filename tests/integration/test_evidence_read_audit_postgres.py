"""Real owner PG17 resource-read audit and append-only evidence; not INT-07."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import asyncpg
import pytest
from tests.integration.test_research_mission_postgres_roundtrip import _database

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.capability_invocation import CapabilityInvocation
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.infrastructure.persistence.evidence_read_audit import PostgresEvidenceReadAudit


async def test_bound_resource_read_audit_is_durable_and_immutable() -> None:
    database = await _database()
    if database is None:
        pytest.skip("no migrated PG17 available; owner CI must execute this test")
    try:
        tenant = "tn_audit_" + uuid4().hex
        invocation = CapabilityInvocation(
            "res_" + uuid4().hex,
            "grant_" + uuid4().hex,
            "bind_" + uuid4().hex,
            "provider_" + uuid4().hex,
            "ei_" + uuid4().hex,
            datetime.now(UTC) + timedelta(seconds=30),
        )
        context = TrustedPlatformContext(context_id=uuid4(), tenant_id=tenant)
        await PostgresEvidenceReadAudit(database).record(
            context=context,
            caller=AuthenticatedCaller(subject="synthetic_workload"),
            invocation=invocation,
            evidence_set_id="evs_synthetic",
            result_count=1,
        )
        record = await database.pool.fetchrow(
            "SELECT * FROM intelligence.evidence_read_audit WHERE tenant_id=$1", tenant
        )
        assert (
            record is not None
            and record["resolution_id"] == invocation.resolution_id
            and record["result_count"] == 1
        )
        assert record["binding_id"] == invocation.binding_id and record["grant_id"] == invocation.grant_id
        for sql in (
            "UPDATE intelligence.evidence_read_audit SET result_count=0 WHERE tenant_id=$1",
            "DELETE FROM intelligence.evidence_read_audit WHERE tenant_id=$1",
        ):
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await database.pool.execute(sql, tenant)
    finally:
        await database.disconnect()
