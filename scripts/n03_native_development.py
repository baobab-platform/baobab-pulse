#!/usr/bin/env python3
"""N03 supervised *real* Hydra -> Pulse -> CP development consumer probe.

No local fixture success, mocked issuer, signed-token synthesis, caller-selected
business permission or source-only PASS. All URLs/credentials are private
operator-provisioned; no token, browser, identity, URL or provider body is logged.
A passing observation is explicitly UNATTESTED until independently witnessed
CP tenant/context binding and teardown have been reviewed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import UUID

SHA = re.compile(r"[a-f0-9]{40}\Z")
RUN = re.compile(r"[a-f0-9]{32}\Z")
ALLOWED_CLIENTS = ("baobab-dev-pulse-onboarding", "baobab-dev-pulse-onboarding-neighbour")
SCOPE = "intelligence:evidence:search"
AUDIENCE = "baobab-pulse"
CASES = (
    "N03_HYDRA_CURRENT_ISSUER_ISSUANCE",
    "N03_NATIVE_PULSE_OWN_CONTEXT",
    "N03_NATIVE_PULSE_NEIGHBOUR_OWN_CONTEXT",
    "N03_NATIVE_PULSE_CROSS_CONTEXT_DENIAL",
    "N03_NATIVE_PULSE_MISSING_BEARER_DENIAL",
    "N03_HYDRA_REVOCATION_READBACK",
    "N03_NATIVE_PULSE_REVOKED_BEARER_DENIAL",
)


class Refused(Exception):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def private_file(path: str, limit: int = 32768) -> bytes:
    ref = Path(path)
    require(ref.is_absolute(), "PRIVATE_ABSOLUTE_PATH_REQUIRED")
    fd = os.open(ref, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and info.st_size <= limit
                and info.st_mode & 0o077 == 0, "OWNER_PRIVATE_FILE_REQUIRED")
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "PRIVATE_FILE_TOO_LARGE")
    return raw


def origin(raw: Any) -> str:
    require(isinstance(raw, str), "REVIEWED_ORIGIN_REQUIRED")
    url = urllib.parse.urlsplit(raw)
    require(url.hostname is not None and url.username is None and url.password is None
            and not url.query and not url.fragment and url.path in ("", "/")
            and (url.scheme == "https" or
                 (url.scheme == "http" and url.hostname == "127.0.0.1")),
            "UNTRUSTED_NATIVE_ORIGIN")
    return raw.rstrip("/")


def profile() -> dict[str, Any]:
    data = json.loads(private_file(os.environ.get("PULSE_N03_PRIVATE_PROFILE", "")),
                      object_pairs_hook=unique)
    require(isinstance(data, dict) and
            data.get("schema") == "baobab.pulse.n03.native-dev.v1"
            and data.get("environment") == "development"
            and os.environ.get("BAOBAB_ENVIRONMENT") == "development"
            and data.get("protected_accepted") is False,
            "N03_PRIVATE_DEVELOPMENT_PROFILE_REQUIRED")
    require(isinstance(data.get("run_id"), str) and
            RUN.fullmatch(data["run_id"]) is not None, "N03_BOUNDED_RUN_REQUIRED")
    for key in ("pulse_source_sha", "iam_source_sha", "cp_source_sha", "shared_source_sha"):
        require(isinstance(data.get(key), str) and SHA.fullmatch(data[key]) is not None,
                "N03_EXACT_PEER_SOURCE_REQUIRED")
    source = Path(__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True,
            text=True, timeout=8, check=True,
        ).stdout.strip()
        dirt = subprocess.run(
            ["git", "-C", str(source), "status", "--porcelain"],
            capture_output=True, text=True, timeout=8, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        raise Refused("N03_IMMUTABLE_SOURCE_UNAVAILABLE") from None
    require(revision == data["pulse_source_sha"] and not dirt,
            "N03_LOCAL_SOURCE_PIN_DRIFT")
    for key in ("hydra_origin", "pulse_origin"):
        data[key] = origin(data.get(key))
    require(data["pulse_origin"] != data["hydra_origin"], "N03_ISSUER_RESOURCE_COLLISION")
    clients = data.get("clients")
    require(isinstance(clients, list) and len(clients) == 2 and
            [item.get("client_id") for item in clients if isinstance(item, dict)]
            == list(ALLOWED_CLIENTS), "N03_EXACT_SYNTHETIC_CLIENTS_REQUIRED")
    for item in clients:
        require(isinstance(item.get("secret_file"), str) and
                isinstance(item.get("context_id"), str), "N03_CLIENT_AND_CONTEXT_REQUIRED")
        try:
            UUID(item["context_id"])
        except ValueError:
            raise Refused("N03_CANONICAL_CONTEXT_REQUIRED") from None
    require(clients[0]["context_id"] != clients[1]["context_id"],
            "N03_DISTINCT_CONTEXTS_REQUIRED")
    observer = data.get("issuer_observer")
    require(isinstance(observer, dict)
            and isinstance(observer.get("client_id"), str)
            and observer["client_id"] not in ALLOWED_CLIENTS
            and isinstance(observer.get("secret_file"), str),
            "N03_INDEPENDENT_ISSUER_OBSERVER_REQUIRED")
    return data


class LiveHTTP:
    def __init__(self) -> None:
        # Disable ambient HTTP proxies and redirects. HTTPS uses the native
        # platform CA trust store; never disable certificate verification.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                return None
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )

    def send(self, url: str, *, body: bytes | None, headers: dict[str, str],
             method: str) -> tuple[int, bytes]:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=8) as response:
                raw = response.read(16385)
                require(len(raw) <= 16384, "N03_RESPONSE_TOO_LARGE")
                return response.status, raw
        except urllib.error.HTTPError as error:
            # Read no untrusted provider body on denied requests.
            return error.code, b""
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Refused("N03_NATIVE_PROVIDER_UNAVAILABLE") from None

    def json(self, url: str, *, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        code, raw = self.send(url, body=body, headers=headers, method="POST")
        require(code == 200, "N03_ISSUER_HTTP_NOT_ACCEPTED")
        result = json.loads(raw, object_pairs_hook=unique)
        require(isinstance(result, dict), "N03_ISSUER_JSON_INVALID")
        return result


def basic(client_id: str, secret: str) -> str:
    encoded = (urllib.parse.quote(client_id, safe="") + ":" +
               urllib.parse.quote(secret, safe="")).encode("utf-8")
    return "Basic " + base64.b64encode(encoded).decode("ascii")


def issue(http: LiveHTTP, issuer: str, client: dict[str, Any]) -> str:
    secret = private_file(client["secret_file"], 4096).decode("utf-8").strip()
    require(len(secret) >= 32, "N03_PRIVATE_CLIENT_CREDENTIAL_REQUIRED")
    result = http.json(issuer + "/oauth2/token",
        body=urllib.parse.urlencode({
            "grant_type": "client_credentials", "scope": SCOPE,
            "audience": AUDIENCE,
        }).encode(),
        headers={"Authorization": basic(client["client_id"], secret),
                 "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    token = result.get("access_token")
    duration = result.get("expires_in")
    require(isinstance(token, str) and 128 <= len(token) <= 8192
            and token.count(".") == 2 and result.get("token_type", "").lower() == "bearer"
            and type(duration) is int and 60 <= duration <= 900,
            "N03_REAL_SIGNED_WORKLOAD_TOKEN_REQUIRED")
    return token


def introspect(http: LiveHTTP, issuer: str, observer: dict[str, Any],
               token: str) -> dict[str, Any]:
    secret = private_file(observer["secret_file"], 4096).decode().strip()
    require(len(secret) >= 32, "N03_PRIVATE_OBSERVER_REQUIRED")
    return http.json(issuer + "/oauth2/introspect",
        body=urllib.parse.urlencode({
            "token": token, "token_type_hint": "access_token",
        }).encode(),
        headers={"Authorization": basic(observer["client_id"], secret),
                 "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})


def call_pulse(http: LiveHTTP, resource: str, token: str | None,
               context: str) -> tuple[int, bytes]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Baobab-Context-Id": context,
    }
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    return http.send(resource + "/evidence/search",
        body=b'{"query_text":"synthetic native IAM/CP evidence","top_k":1}',
        headers=headers, method="POST")


def require_success(code: int, raw: bytes) -> None:
    require(code == 200, "N03_NATIVE_RESOURCE_SUCCESS_MISSING")
    result = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(result, dict) and isinstance(result.get("candidates"), list),
            "N03_NATIVE_RESPONSE_CONTRACT_DRIFT")


def execute(data: dict[str, Any]) -> dict[str, str]:
    http = LiveHTTP()
    issuer, resource = data["hydra_origin"], data["pulse_origin"]
    own, neighbour = data["clients"]
    observer = data["issuer_observer"]
    token_a = issue(http, issuer, own)
    token_b = issue(http, issuer, neighbour)
    for token, client in ((token_a, own), (token_b, neighbour)):
        status = introspect(http, issuer, observer, token)
        aud = status.get("aud")
        auds = [aud] if isinstance(aud, str) else aud
        require(status.get("active") is True
                and status.get("client_id") == client["client_id"]
                and auds == [AUDIENCE]
                and SCOPE in str(status.get("scope", "")).split()
                and type(status.get("exp")) is int
                and status["exp"] > int(time.time()) + 10,
                "N03_REAL_ISSUER_TOKEN_READBACK_REQUIRED")
    outcomes = {key: "BLOCKED" for key in CASES}
    outcomes[CASES[0]] = "OBSERVED"
    require_success(*call_pulse(http, resource, token_a, own["context_id"]))
    outcomes[CASES[1]] = "OBSERVED"
    require_success(*call_pulse(http, resource, token_b, neighbour["context_id"]))
    outcomes[CASES[2]] = "OBSERVED"
    code, _ = call_pulse(http, resource, token_a, neighbour["context_id"])
    require(code in (401, 403, 404), "N03_CROSS_CONTEXT_WAS_ACCEPTED")
    outcomes[CASES[3]] = "OBSERVED"
    code, _ = call_pulse(http, resource, None, own["context_id"])
    require(code == 401, "N03_MISSING_BEARER_WAS_ACCEPTED")
    outcomes[CASES[4]] = "OBSERVED"
    secret = private_file(own["secret_file"], 4096).decode().strip()
    code, _ = http.send(issuer + "/oauth2/revoke",
        body=urllib.parse.urlencode({"token": token_a,
                                   "token_type_hint": "access_token"}).encode(),
        headers={"Authorization": basic(own["client_id"], secret),
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    require(code in (200, 204), "N03_REAL_REVOCATION_UNCONFIRMED")
    inactive = introspect(http, issuer, observer, token_a)
    require(inactive.get("active") is False,
            "N03_ISSUER_REVOCATION_NOT_OBSERVED")
    outcomes[CASES[5]] = "OBSERVED"
    code, _ = call_pulse(http, resource, token_a, own["context_id"])
    require(code in (401, 403), "N03_REVOKED_NATIVE_BEARER_WAS_ACCEPTED")
    outcomes[CASES[6]] = "OBSERVED"
    return outcomes


def write_original(data: dict[str, Any], cases: dict[str, str]) -> None:
    out = Path(os.environ.get("PULSE_N03_EVIDENCE_DIR", ""))
    require(out.is_absolute() and not out.is_symlink(), "N03_PRIVATE_OUTPUT_REQUIRED")
    meta = out.lstat()
    require(stat.S_ISDIR(meta.st_mode) and meta.st_uid == os.getuid()
            and meta.st_mode & 0o077 == 0, "N03_PRIVATE_OUTPUT_REQUIRED")
    require(set(cases) == set(CASES)
            and all(item == "OBSERVED" for item in cases.values()),
            "N03_SEVEN_RUNTIME_CASES_REQUIRED")
    receipt = {
        "schema": "baobab.pulse.n03.native-observation.v1",
        "classification": "REAL_NATIVE_HYDRA_PULSE_CP_UNATTESTED",
        "environment": "development",
        "run_id": data["run_id"],
        "pulse_source_sha": data["pulse_source_sha"],
        "iam_source_sha": data["iam_source_sha"],
        "cp_source_sha": data["cp_source_sha"],
        "shared_source_sha": data["shared_source_sha"],
        "cases": cases,
        "two_tenants_independently_attested": False,
        "protected_accepted": False,
    }
    raw = json.dumps(receipt, separators=(",", ":"), sort_keys=True).encode()
    for name, body in (("native-observation.json", raw),
                       ("native-observation.sha256", (
                            hashlib.sha256(raw).hexdigest() + "\n").encode())):
        path = out / name
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(body)
            file.flush()
            os.fsync(file.fileno())
    fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    try:
        data = profile()
        cases = execute(data)
        write_original(data, cases)
    except Exception as exc:
        code = str(exc) if isinstance(exc, Refused) else "NATIVE_RUNTIME_OR_EVIDENCE_UNAVAILABLE"
        if not re.fullmatch(r"[A-Z0-9_]+", code):
            code = "NATIVE_RUNTIME_OR_EVIDENCE_UNAVAILABLE"
        print("N03_NATIVE_DEV_BLOCKED " + code, file=sys.stderr)
        return 1
    print("N03_REAL_NATIVE_OBSERVED_UNATTESTED; CP tenant and provider acceptance HELD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
