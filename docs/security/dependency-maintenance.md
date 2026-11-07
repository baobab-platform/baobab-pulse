# BA-SEC-DEP-001 — baobab-pulse dependency and security maintenance audit

**Review date:** 7 November 2026. **Repository:** `baobab-platform/baobab-pulse`. **Status:** SOURCE_COMMITTED only.

## Observed manifests and Dependabot coverage

GitHub Actions /; uv / (pyproject.toml + uv.lock); Docker / (Dockerfile and Dockerfile.integration); Docker Compose / (docker-compose.yml).

## Actual dependency/security surveillance

Existing pinned Shared security-python.yml executes Bandit and pip-audit on the uv-locked security group. Its schedule is now daily. A source-level workflow declaration does not prove a successful live scan or a real Haystack/Qdrant provider integration.

## Findings, unqualified boundaries and exception custody

Open Pulse #63 is an N03 issuer-status enforcement workstream; keep that refusal and native issuance proof separate. Pulse #54 proposes qdrant-haystack major 12; no automatic major migration is authorised. Source-pinned images still require actual image scanning, registry digest/provenance and connected Haystack/Qdrant tests.

**Current disposition:** Actual root uv.lock is present; Python security scan and upgrade alerts require execution/readback.

## Governance and evidence levels

Governing authority: [approved BA-SEC-DEP-001 v1.0, Shared #429](https://github.com/baobab-platform/shared/pull/429). The proposed stricter Shared validator is NOT released; this branch uses the SHA-pinned accepted Shared v2.3.0 structural validator and an owner-local positive/negative source suite. Weekly Monday Africa/Johannesburg version updates are distinct from advisory-driven security response. Routine groups apply only to minor/patch version-updates; major or security updates require independent review.

Evidence state **SOURCE_COMMITTED** means source reviewed/committed, not executed. **CI_VERIFIED**, **SECURITY_ALERT_PATH_VERIFIED**, **CONSUMER_QUALIFIED**, **STAGING_VERIFIED**, and **PRODUCTION_VERIFIED** are NOT claimed. Findings are **BLOCKED** pending an independently approved remediation or expiring exception. **WAIVED is not PASSED**. Security CODEOWNERS review applies to manifest and exception changes.

## Exit criteria

1. Run the actual final-head policy regression and accepted Shared validator; inspect live GitHub Dependabot job logs, dependency graph, Alerts, automatic security update settings and actual dependency scan results.
2. Repair reported security vulnerabilities promptly using real installed package/image provenance; independent time-bounded evidence and Security approval are required for any unpatched exceptions. Do not permit scanner errors, no-ops or ignored advisories to appear as success.
3. Re-run owner-specific native runtime, IAM/CP authority, supplier/consumer isolation, replay, migration and negative acceptance tests after a major or security update. No synthetic PSP, carrier, rule or issuer success counts as a real integration.
4. Obtain separate staging/production approvals and deployment evidence. No protected environment, credential, provider or release is activated by this policy adoption.

No CI run or monitoring, PR merge or protected business approval has been claimed.
