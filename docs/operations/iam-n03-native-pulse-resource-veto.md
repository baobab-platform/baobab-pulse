# IAM-N03 — Pulse native resource current-issuer veto (development candidate)

**Status:** SOURCE-ONLY, CONNECTED CONSUMER QUALIFICATION HELD.  
**Governance:** EA v2.3 / EA-DEV DEV-14/15, IAM N03, accepted Shared issuer/CP authority controls.  
**Owning resource:** `baobab-platform/baobab-pulse`; issuer and native credential issuance remain IAM-owned; Context, tenant, Principal, EngineInstance and resource policy decisions remain CP-owned.

## Why the N03 wrapper is required

Before this change the Pulse production composition used
`OidcJwksWorkloadAuthenticator`. It verified signed workload JWTs, expiry,
issuer and `baobab-pulse` audience, but a valid **revoked yet unexpired**
JWT could still pass the *resource* signature check until expiry. Current CP
context validation is a distinct veto; it does not justify treating static
JWKS signature verification as live issuer revocation proof.

The N03 resource adapter
`src/baobab_pulse/infrastructure/authentication/current_issuer_status.py`
does the following **for each presented request**:

1. Call the **existing JWKS signature/audience/actor/lifetime verifier** first.
   Fail before issuer status if that fails.
2. Require a signed `client_id` binding and the original raw token.
3. Use a **separately authorised issuer introspection client** to perform
   authenticated RFC 7662 `POST /oauth2/introspect` on that exact token.
   Never reuse the CP `context:validate` client secret, fall back to bearer
   user credentials, cache an active response or follow redirects.
4. Require `active: true`, exact issuer, signed workload subject and client
   ID, singleton `baobab-pulse` audience, equal scopes and a future integer
   expiry. Revocation, mismatched identity, broad audience/scope and expired
   issuer observation deny. HTTP failure, malformed/oversized JSON, redirect,
   TLS or network failure becomes **authority unavailable**, not ALLOW.
5. Only *then* return the authenticated caller. Existing Pulse business
   resource layers still require **real CP** context/capability validation and
   PostgreSQL-authoritative domain rules; issuer status is never CP authority.

The observer is bound to the configured signed issuer origin. Redirects and
HTTP proxies are disabled; HTTPS is required except exact
`http://127.0.0.1` in an explicitly nonprotected development/local profile.
The issuer response is bounded to 8192 bytes and rejects duplicate JSON keys.

## Configuration and the provisioning hold

`PULSE_IAM_INTROSPECTION_URL` — trusted issuer's exact
`/oauth2/introspect` endpoint; `PULSE_IAM_INTROSPECTION_CLIENT_ID` and
`PULSE_IAM_INTROSPECTION_CLIENT_SECRET` — a **distinct** reviewed private
credential for status observation. The preexisting
`PULSE_IAM_CLIENT_ID/SECRET` remains the Pulse-to-CP
`context:validate` caller, not the observer.

Protected staging and production capability composition now refuses startup
without the separate issuer status identity. In development, the current-status
adapter is enabled only with all three complete settings. Source code does
not register this Hydra client, allocate a Shared scope, grant CP permissions,
activate a provider, or provide that private credential. It must be
independently provisioned and qualified in IAM; no generic scope or client
reuse is authorised.

## Mandatory original runtime evidence (still BLOCKED)

Development synthetic host only, reviewed immutable IAM/Shared/CP/Pulse heads,
private credentials, real Hydra issuer and current CP native validator:

- Actual issuer-signed JWT successfully admitted to the **real running Pulse**
  route, with issuer status `active:true` and real CP scoped Context
  + capability resolution. Observe PostgreSQL-backed result and correlation.
- Revoke the *same JWT before expiry* at Hydra; observe its independent
  introspection status `active:false` and immediate native Pulse denial.
  Preserve expiry evidence showing revocation preceded natural expiry.
- Reject unregistered/wrong client, altered signature, wrong audience,
  missing or extra scope, wrong tenant/context, inactive CP Principal and
  unavailable CP/issuer; preserve correct 401/403/503 distinctions. No
  negative outcome may be relabelled as a positive provider success.
- Original source-pin/runtime/image identity, original issuer/CP/Pulse
  request evidence, host/network lifecycle, private digest sidecars and
  independently verified run-owned teardown. Use privacy-safe closed
  statuses, not JWTs, client secrets or arbitrary provider bodies.
- Repeat separately for Payments under its own resource-server ownership;
  this PR says **nothing** about Payments' outstanding five ENG-ONB cases.

The tests in `tests/unit/security/test_current_issuer_status.py` and
`tests/architecture/test_n03_current_issuer_composition.py` are **mock/source
tests only**. No connected issuer, native resource, original evidence archive,
independent witness or provider support promotion has occurred. This PR stays
draft and unmerged until final-head CI and required native verification succeed.

## Owner-run N03 native consumer probe (source added, NOT EXECUTED)

`scripts/n03_native_development.py` now exercises **actual** Hydra
client-credentials issuance, independently authenticated issuer introspection,
real running Pulse `POST /evidence/search` with CP-assigned Context A and B,
cross-context denial, missing-bearer denial, real Hydra token revocation,
independent `active:false` readback and immediate native Pulse denial.
A passing run produces only owner-private `native-observation.json` and
`native-observation.sha256` (0600, unique inode, fsynced), with all seven
original scenario keys and **UNATTESTED** development classification. Source
tests cannot generate a qualified observation.

Create an owned, `chmod 0600` JSON profile at an *absolute* private path.
Required keys:
`schema=baobab.pulse.n03.native-dev.v1`,
`environment=development`, `protected_accepted=false`,
`run_id` (32 lowercase hex), immutable 40-character
`pulse_source_sha`, `iam_source_sha`, `cp_source_sha`,
`shared_source_sha`, exact `hydra_origin` and `pulse_origin`,
`clients` (an ordered two-element array containing the exact named Shared
development onboarding and onboarding-neighbour clients, each with
`client_id`, owner-private `secret_file` and independently issued
`context_id` UUID), plus `issuer_observer` with a **different** IAM
`client_id` and private `secret_file`. No private values or token bytes
are recorded in the output.

```sh
export BAOBAB_ENVIRONMENT=development
export PULSE_N03_PRIVATE_PROFILE=/absolute/private/n03-profile.json
export PULSE_N03_EVIDENCE_DIR=/absolute/private/originals
# Run from an immutable, clean, pinned Pulse checkout in a private
# network with real Hydra, CP and Pulse; never inside mock source tests.
python3 -B scripts/n03_native_development.py
```

**Before running:** both original CP Contexts must be demonstrably assigned
to distinct governed development tenants and active client identities; Hydra
must issue signed, Pulse-audience workload tokens with a maximum 15-minute
lifetime and allow **actual access-token revocation**, which must be
independently observable through authenticated introspection. A consent,
missing registry client, wrong audience, revoked token or CP failure must
cause a genuine rejection. Set `PULSE_IAM_NATIVE_N03_REQUIRED=true` and
the separate observer credential on the running Pulse resource so the
development runtime cannot fall back to JWKS-only checks.

**Evidence ceiling:** this script does not create the CP tenants/Contexts,
grant or activate a workload client, manage provider credentials, mutate CP
configuration, qualify Payments or verify host teardown. It explicitly
records `two_tenants_independently_attested=false`. Only an independent
current CP tenant/source readback and disposable host resource inventory
can raise this candidate's assurance; never edit this original.
