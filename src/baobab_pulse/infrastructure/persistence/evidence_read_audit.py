"""Persist the successful resource read before any candidates leave Pulse."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.capability_invocation import CapabilityInvocation
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.domain.shared.errors import CapabilityAuthorityUnavailableError
from baobab_pulse.infrastructure.persistence.connection import Database


class PostgresEvidenceReadAudit:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record(
        self,
        *,
        context: TrustedPlatformContext,
        caller: AuthenticatedCaller,
        invocation: CapabilityInvocation,
        evidence_set_id: str | None,
        result_count: int,
    ) -> None:
        try:
            async with asyncio.timeout(3), self._database.pool.acquire() as connection:
                await connection.execute(
                    """INSERT INTO intelligence.evidence_read_audit
                    (audit_id,tenant_id,context_id,actor_subject,actor_client_id,
                     resolution_id,grant_id,binding_id,provider_id,engine_instance_id,
                     evidence_set_id,result_count,occurred_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                    uuid4(),
                    context.tenant_id,
                    context.context_id,
                    caller.subject,
                    caller.client_id,
                    invocation.resolution_id,
                    invocation.grant_id,
                    invocation.binding_id,
                    invocation.provider_id,
                    invocation.engine_instance_id,
                    evidence_set_id,
                    result_count,
                    datetime.now(UTC),
                )
        except (OSError, RuntimeError, TimeoutError, asyncpg.PostgresError) as error:
            raise CapabilityAuthorityUnavailableError("durable resource-read audit unavailable") from error
