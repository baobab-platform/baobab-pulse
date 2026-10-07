"""P-CAP-04 PostgreSQL ResearchMission durability and tenant-isolation test."""

from __future__ import annotations

import asyncpg
import pytest

from baobab_pulse.configuration.settings import Settings
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, ConfidenceBand, TenantScope
from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.infrastructure.persistence.connection import Database
from baobab_pulse.infrastructure.persistence.research_mission_repository import (
    PostgresResearchMissionRepository,
)

_MISSION_ID = "rms_44444444444444444444444444444444"


async def _database() -> Database | None:
    database = Database(Settings().database_url)
    try:
        await database.connect()
    except (OSError, asyncpg.PostgresError):
        return None
    if not await database.is_ready():
        await database.disconnect()
        return None
    relation = await database.pool.fetchval(
        "SELECT to_regclass('intelligence.research_missions')"
    )
    if relation is None:
        await database.disconnect()
        return None
    return database


async def test_research_mission_round_trip_is_durable_and_tenant_scoped() -> None:
    database = await _database()
    if database is None:
        pytest.skip("no live migrated PostgreSQL reachable — see PULSE_DATABASE_URL")

    repository = PostgresResearchMissionRepository(database)
    mission = ResearchMission(
        id=_MISSION_ID,
        title="Durable research mission",
        research_question="Can this aggregate survive process memory?",
        tenant_scope=TenantScope.TENANT,
        tenant_context=TenantContext(
            tenant_id="tn_pcap04",
            context_id="22222222-2222-4222-8222-222222222222",
            organisation_id="org_test",
        ),
        classification=Classification.TENANT,
        confidence_requirement=ConfidenceBand.MODERATE,
    )

    try:
        await database.pool.execute(
            "DELETE FROM intelligence.research_missions WHERE id = $1",
            _MISSION_ID,
        )
        await repository.add(mission)

        same_tenant = await repository.get_for_tenant(
            _MISSION_ID,
            tenant_id="tn_pcap04",
        )
        other_tenant = await repository.get_for_tenant(
            _MISSION_ID,
            tenant_id="tn_other",
        )

        assert same_tenant == mission
        assert other_tenant is None

        row = await database.pool.fetchrow(
            """
            SELECT tenant_id, status, classification, payload
            FROM intelligence.research_missions
            WHERE id = $1
            """,
            _MISSION_ID,
        )
        assert row is not None
        assert row["tenant_id"] == "tn_pcap04"
        assert row["status"] == "PROPOSED"
        assert row["classification"] == "TENANT"
    finally:
        await database.pool.execute(
            "DELETE FROM intelligence.research_missions WHERE id = $1",
            _MISSION_ID,
        )
        await database.disconnect()
