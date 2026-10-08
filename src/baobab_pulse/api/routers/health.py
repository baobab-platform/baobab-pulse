"""Liveness/readiness (item 117; Qdrant refactor item 69).

Readiness distinguishes three separate signals rather than one boolean:

- service alive (``/healthz`` — always 200 while the process runs)
- canonical persistence ready (PostgreSQL reachable)
- semantic retrieval ready (Qdrant reachable)

Qdrant is deliberately NOT required for overall readiness (item 36, 69):
a Pulse deployment with PostgreSQL up and Qdrant down is "ready" with
semantic search degraded, not "not ready" outright — callers that need
semantic search specifically see that failure at the point they use it
(``SemanticRetrievalUnavailable``, mapped to 503 in ``api.error_handlers``),
not as a global outage.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from baobab_pulse.api.dependencies import get_database, get_qdrant_evidence_store
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
)
from baobab_pulse.infrastructure.persistence.connection import Database

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/readyz")
async def readiness(
    database: Database = Depends(get_database),
    qdrant: QdrantEvidenceProjectionStore = Depends(get_qdrant_evidence_store),
) -> JSONResponse:
    database_ready = await database.is_ready()
    semantic_retrieval_ready = await qdrant.is_ready()
    body = {
        "status": "ready" if database_ready else "not_ready",
        "dependencies": {
            "database": database_ready,
            "semantic_retrieval": semantic_retrieval_ready,
        },
    }
    # Canonical persistence is the only hard readiness gate — semantic
    # retrieval degrading does not take the whole service "not ready".
    return JSONResponse(status_code=200 if database_ready else 503, content=body)
