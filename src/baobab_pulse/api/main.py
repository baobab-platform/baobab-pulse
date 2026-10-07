"""The ``pulse-api`` ASGI application (item 61, 67-68).

    uvicorn baobab_pulse.api.main:app

``create_app`` is a factory (not a bare module-level ``app``) so tests can
build isolated instances and override dependencies without import-order
side effects.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from baobab_pulse.api.composition import build_capability_runtime
from baobab_pulse.api.dependencies import get_database, get_settings
from baobab_pulse.api.error_handlers import register_error_handlers
from baobab_pulse.api.middleware import TenancyMiddleware
from baobab_pulse.api.routers import evidence, health, research_missions
from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.infrastructure.observability.logging_config import configure_logging
from baobab_pulse.infrastructure.observability.telemetry import configure_telemetry


def create_app(runtime: CapabilityApiRuntime | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_telemetry(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # A dependency being unreachable at startup is a readiness fact, not
        # a reason to crash the process (item 121-123: graceful degradation
        # — /readyz reports the truth via Database.is_ready(), the process
        # itself stays up and retries on the next request rather than
        # crash-looping the whole container over one transient DB outage).
        database = get_database()
        try:
            await database.connect()
        except Exception:  # noqa: BLE001 -- any startup connection failure degrades to not_ready, never a crash
            logging.getLogger(__name__).warning("database unreachable at startup; /readyz will report not_ready")
        try:
            yield
        finally:
            await database.disconnect()

    app = FastAPI(
        title="Baobab Pulse",
        description="Baobab's headless Intelligence, Research and Evidence Engine.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.capability_runtime = runtime
    app.add_middleware(TenancyMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(research_missions.router)
    app.include_router(evidence.router)
    return app


app = create_app(build_capability_runtime())
