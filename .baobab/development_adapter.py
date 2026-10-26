#!/usr/bin/env python3
"""DEV-15 Pulse owner adapter; never a CP/IAM authority.

Infrastructure owns leases, genuine issuer provisioning, governed CP fixtures,
image pins, independent evidence and teardown. Connected phases run inside its
private non-root owner container and exercise real Pulse HTTP, PostgreSQL and
Qdrant. Legacy health-only phases cannot claim joined acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

PHASES = ("readiness", "migrate", "seed", "exercise", "cleanup")
CONNECTED_PHASES = ("prepare", "test", "observe", "unavailable", "denied", "restored")
REASONS = {
    "readiness": "NATIVE_PULSE_NOT_READY",
    "migrate": "NATIVE_PULSE_MIGRATION_FAILED",
    "seed": "CP_GOVERNED_SEED_NOT_WIRED",
    "exercise": "REAL_IAM_CP_DOMAIN_QUALIFIER_NOT_WIRED",
    "cleanup": "INDEPENDENT_CLEANUP_WITNESS_REQUIRED",
}


def refuse(phase: str, reason: str) -> dict:
    return {
        "schema": "baobab.engine-development-adapter-result.v1",
        "engine": "baobab-pulse",
        "phase": phase,
        "result": "BLOCKED",
        "reason": reason,
        "native_effect_observed": False,
        "runtime_eng_onb_qualified": False,
        "protected_acceptance": False,
        "production_authorized": False,
    }


def observe_ready(endpoint: str) -> bool:
    """Use only a fixed loopback endpoint: never allow an arbitrary SSRF URL."""
    if endpoint != "http://127.0.0.1:8000/readyz":
        return False
    try:
        with urllib.request.urlopen(endpoint, timeout=3) as response:  # noqa: S310
            if response.status != 200:
                return False
            body = response.read(4097)
            if len(body) > 4096:
                return False
            observation = json.loads(body)
            return (
                isinstance(observation, dict)
                and observation.get("status") == "ready"
                and isinstance(observation.get("dependencies"), dict)
                and observation["dependencies"].get("database") is True
            )
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return False


def migrate() -> bool:
    # No migration is permitted on a reused, protected or missing DB. The
    # trusted Infrastructure caller must supply an ephemeral native DB URL.
    if os.environ.get("BAOBAB_DEV14_PRIVATE_RUN") != "1":
        return False
    if os.environ.get("BAOBAB_ENVIRONMENT") != "development":
        return False
    # A caller-provided 'development' flag alone is NOT database authority.
    # Require the privately named one-shot Pulse store; refuse loopback,
    # public hosts, special PostgreSQL socket URLs or a reused server.
    source = os.environ.get("PULSE_DATABASE_URL", "")
    try:
        endpoint = urlsplit(source)
        if not (
            endpoint.scheme == "postgresql"
            and endpoint.hostname == "pulse-db"
            and endpoint.port == 5432
            and endpoint.path == "/pulse"
            and bool(endpoint.username)
            and bool(endpoint.password)
            and endpoint.query == ""
            and endpoint.fragment == ""
        ):
            return False
    except ValueError:
        return False
    script = Path(__file__).resolve().parents[1] / "scripts" / "migrate.py"
    if not script.is_file():
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(script)],
            check=False, capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def run(phase: str) -> tuple[int, dict]:
    if phase not in PHASES:
        raise ValueError("UNKNOWN_OWNER_PHASE")
    if phase in {"readiness", "migrate"}:
        passed = observe_ready("http://127.0.0.1:8000/readyz") if phase == "readiness" else migrate()
        if passed:
            observation = refuse(phase, "OWNER_COMPONENT_OBSERVED")
            observation["result"] = "PASS"
            observation["reason"] = "OWNER_COMPONENT_OBSERVED"
            observation["native_effect_observed"] = phase == "migrate"
            return 0, observation
    return 2, refuse(phase, REASONS[phase])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=PHASES+CONNECTED_PHASES)
    args = parser.parse_args(argv)
    if args.phase in {"prepare", "test", "observe", "unavailable", "denied", "restored"}:
        try:
            print(json.dumps(connected(args.phase), sort_keys=True))
            return 0
        except Exception:
            print("PULSE_CONNECTED_ADAPTER_REFUSED", file=sys.stderr)
            return 2
    status, receipt = run(args.phase)
    print(json.dumps(receipt, sort_keys=True))
    return status




def connected(phase: str) -> dict:
    """Called only inside Infrastructure's private, non-root owner container."""
    import asyncio
    import hashlib
    import uuid

    from engine_sdk import Driver

    driver = Driver()
    custody = driver.context
    if custody.get("schema") != "baobab.engine-adapter-context.v1":
        raise ValueError("PRIVATE_ENGINE_CONTEXT_REQUIRED")
    tenant = custody["tenant"]["id"]
    neighbour = custody["neighbour"]["id"]
    text = "DEV-15 synthetic native canonical evidence."
    cases = {name: {"result": "BLOCKED", "reason": "NOT_EXECUTED"} for name in (
        "PULSE-CANONICAL-SEARCH", "PULSE-MISSION-CREATE-GET", "PULSE-MISSION-REPLAY-CONFLICT",
        "PULSE-WRONG-TENANT", "PULSE-CLASSIFICATION", "PULSE-ORPHAN-VECTOR",
        "PULSE-PROJECTION-MISMATCH", "PULSE-QDRANT-OUTAGE-RECOVERY", "PULSE-PROJECTION-REBUILD",
        "PULSE-INVALID-EVENT-CONTEXT", "PULSE-REVOKED-ACCESS",
    )}

    def check(ok: bool) -> None:
        if not ok:
            raise ValueError("NATIVE_ASSERTION_FAILED")

    def witness():
        actual = custody["witness"]
        return actual["caller_token"], actual["context"]["context_id"]

    def search(evidence="evs_dev15_current", token=None, context=None):
        bearer, cid = witness()
        return driver.native("/evidence/search", {"query_text": text, "evidence_set_id": evidence, "top_k": 10}, token or bearer, context or cid)

    def mission(body, key=None, token=None, context=None):
        bearer, cid = witness()
        return driver.native("/research-missions/manage", body, token or bearer, context or cid, key)

    create = {"operation": "CREATE", "title": "DEV-15 synthetic mission", "research_question": "Can current authority execute a native mission?",
              "tenant_scope": "TENANT", "classification": "TENANT", "confidence_requirement": "MODERATE"}

    async def native(seed=False):
        from baobab_pulse.api.dependencies import (
            get_database,
            get_evidence_repository,
            get_qdrant_evidence_store,
        )
        from baobab_pulse.application.ports.vector_projection_port import (
            ProjectionCollection,
            ProjectionRecord,
        )
        from baobab_pulse.domain.evidence import Evidence, EvidenceSet
        from baobab_pulse.domain.shared.enums import Classification, EvidenceDirection, TenantScope
        from baobab_pulse.domain.shared.value_objects import Reference, TenantContext
        database = get_database()
        await database.connect()
        try:
            if seed:
                repository, vectors = get_evidence_repository(), get_qdrant_evidence_store()
                for suffix, owner, classification, version in (
                    ("current", tenant, Classification.CONFIDENTIAL, 1),
                    ("restricted", tenant, Classification.RESTRICTED, 1),
                    ("neighbour", neighbour, Classification.CONFIDENTIAL, 1),
                    ("stale", tenant, Classification.CONFIDENTIAL, 2),
                    ("future", tenant, Classification.CONFIDENTIAL, 1),
                ):
                    doc = EvidenceSet(id="evs_dev15_"+suffix, purpose="disposable DEV-15 native proof", tenant_scope=TenantScope.TENANT,
                        tenant_context=TenantContext(tenant_id=owner), classification=classification, version=version,
                        entries=(Evidence(id="evd_dev15_"+suffix, referenced_object=Reference(object_type="observation", object_id="obs_dev15_"+suffix), direction=EvidenceDirection.SUPPORTS),))
                    await repository.add_with_text(doc, {"evd_dev15_"+suffix: text})
                    await vectors.upsert_projection(ProjectionCollection.EVIDENCE, ProjectionRecord(canonical_object_id="evd_dev15_"+suffix,
                        evidence_set_id=doc.id, canonical_version=99 if suffix=="future" else 1, tenant_id=tenant if suffix=="neighbour" else owner, classification=Classification.PUBLIC if suffix=="restricted" else classification, content=text,
                        content_hash=hashlib.sha256(text.encode()).hexdigest(), embedding_model_id="mock:mock-model", embedding_model_version="1"))
                await vectors.upsert_projection(ProjectionCollection.EVIDENCE, ProjectionRecord(canonical_object_id="evd_dev15_orphan",
                    evidence_set_id="evs_dev15_orphan", canonical_version=1, tenant_id=tenant, classification=Classification.CONFIDENTIAL,
                    content=text, content_hash=hashlib.sha256(text.encode()).hexdigest(), embedding_model_id="mock:mock-model", embedding_model_version="1"))
            counts = {}
            for key, table in (("canonical_sets", "evidence.evidence_sets"), ("missions", "intelligence.research_missions"),
                               ("mutation_audits", "intelligence.research_mission_mutation_audit"), ("read_audits", "intelligence.evidence_read_audit"), ("outbox", "intelligence.outbox")):
                counts[key] = await database.pool.fetchval("SELECT count(*) FROM "+table+" WHERE tenant_id=$1", tenant)
            # Actual owner-store read-back, separate from the HTTP command.
            resolutions = await database.pool.fetch("SELECT resolution_id FROM intelligence.evidence_read_audit WHERE tenant_id=$1 UNION SELECT resolution_id FROM intelligence.research_mission_mutation_audit WHERE tenant_id=$1", tenant)
            held = await database.pool.fetchval("SELECT count(*) FROM intelligence.outbox WHERE tenant_id=$1 AND publication_status<>'HELD_UNREGISTERED'", tenant)
            return {"effects": counts, "resolutions": [row["resolution_id"] for row in resolutions], "checks": {"outbox_held": held == 0}}
        finally:
            await database.disconnect()

    if phase == "prepare":
        check(migrate())
        asyncio.run(native(seed=True))
        return {"prepared": True}
    if phase == "observe":
        return asyncio.run(native())
    if phase in {"unavailable", "denied", "restored"}:
        before = asyncio.run(native()) if phase != "unavailable" else None
        code, _ = search()
        if phase == "restored":
            check(code == 200)
            check(mission(create,"dev15-mission-"+custody["run"]["id"])[0]==200)
        elif phase == "unavailable":
            check(code == 503)
            if not custody.get("fault_phase","").endswith("-qdrant"):
                check(mission(create,"dev15-outage-"+uuid.uuid4().hex)[0]==503)
        else:
            check(code in (403, 404))
            check(mission(create, "dev15-denied-"+uuid.uuid4().hex)[0] in (403, 404))
            check(asyncio.run(native())["effects"] == before["effects"])
        if phase=="restored" and custody.get("fault_phase","").endswith("-qdrant"):
            return {"observed":True,"case_updates":{"PULSE-QDRANT-OUTAGE-RECOVERY":{"result":"PASS","reason":"OBSERVED"}}}
        return {"observed": True}
    check(phase == "test")

    def observe(name, work):
        try:
            work()
            cases[name] = {"result": "PASS", "reason": "OBSERVED"}
        except Exception:
            cases[name] = {"result": "FAIL", "reason": "ASSERTION_FAILED"}

    def canonical():
        code, body = search()
        check(code == 200 and len(body["candidates"]) == 1 and body["candidates"][0]["canonical_object_id"] == "evd_dev15_current" and body["candidates"][0]["is_stale"] is False)
    observe("PULSE-CANONICAL-SEARCH", canonical)

    def mission_lifecycle():
        key = "dev15-mission-"+custody["run"]["id"]
        code, created = mission(create, key)
        check(code == 200)
        cid = created["id"]
        check(mission({"operation": "GET", "research_mission_id": cid}) == (200, created))
        before = asyncio.run(native())["effects"]
        check(mission(create, key) == (200, created))
        check(mission({**create, "title": "Different request"}, key)[0] == 409)
        check(asyncio.run(native())["effects"] == before)
        cases["PULSE-MISSION-REPLAY-CONFLICT"] = {"result": "PASS", "reason": "OBSERVED"}
    observe("PULSE-MISSION-CREATE-GET", mission_lifecycle)

    def isolation():
        foreign = custody["witness"]["neighbour_context"]["context_id"]
        check(search(context=foreign)[0] in (403, 404))
        check(search("evs_dev15_neighbour")[0] == 200 and search("evs_dev15_neighbour")[1]["candidates"] == [])
    observe("PULSE-WRONG-TENANT", isolation)
    observe("PULSE-CLASSIFICATION", lambda: check(search("evs_dev15_restricted") == (200, {"candidates": []}) and mission({**create, "classification": "RESTRICTED"}, "dev15-restricted-"+uuid.uuid4().hex)[0] == 403))
    observe("PULSE-ORPHAN-VECTOR", lambda: check(search("evs_dev15_orphan") == (200, {"candidates": []})))
    observe("PULSE-PROJECTION-MISMATCH", lambda: check(search("evs_dev15_stale")[0] == 200 and search("evs_dev15_stale")[1]["candidates"][0]["is_stale"] is True and search("evs_dev15_future")[1]["candidates"][0]["is_stale"] is True))

    def rebuild():
        result = subprocess.run([sys.executable, "-B", "/app/scripts/rebuild_projection.py", "--evidence-set-id", "evs_dev15_stale"], capture_output=True, timeout=120)
        check(result.returncode == 0)
        code, body = search("evs_dev15_stale")
        check(code == 200 and len(body["candidates"]) == 1 and body["candidates"][0]["is_stale"] is False)
    observe("PULSE-PROJECTION-REBUILD", rebuild)

    def security():
        before = asyncio.run(native())["effects"]
        for name, statuses in (("revoked", (401,)), ("untrusted_issuer", (401,)), ("expired", (401,)), ("wrong_audience", (401,)), ("missing_scope", (403,))):
            check(search(token=custody["security_tokens"][name])[0] in statuses)
            check(mission(create, "dev15-invalid-"+uuid.uuid4().hex, token=custody["security_tokens"][name])[0] in statuses)
        check(asyncio.run(native())["effects"] == before)
    observe("PULSE-REVOKED-ACCESS", security)

    def invalid_context():
        before = asyncio.run(native())["effects"]
        check(mission({**create, "tenant_id": neighbour}, "dev15-event-"+uuid.uuid4().hex)[0] == 422)
        check(mission(create, "dev15-event-"+uuid.uuid4().hex, context=str(uuid.uuid4()))[0] == 404)
        check(asyncio.run(native())["effects"] == before)
    observe("PULSE-INVALID-EVENT-CONTEXT", invalid_context)
    return {"cases": cases}


if __name__ == "__main__":
    sys.exit(main())
