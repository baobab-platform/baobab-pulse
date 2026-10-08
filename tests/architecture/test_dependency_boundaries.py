"""Required architectural tests #1-5 (platform brief item 129).

Static (AST-based) import scanning rather than runtime import-hook tricks:
it catches a forbidden import even in a module nothing else happens to
import during a given test run, and it needs no test doubles or monkey-
patching to work.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "baobab_pulse"

_HAYSTACK_PREFIXES = ("haystack",)
_QDRANT_PREFIXES = ("qdrant_client", "haystack_integrations")
_HTTP_FRAMEWORK_PREFIXES = ("fastapi", "starlette", "uvicorn")
_DATABASE_PREFIXES = ("asyncpg", "sqlalchemy", "psycopg", "psycopg2")
_CLOUD_SDK_PREFIXES = ("boto3", "botocore", "google.cloud", "azure")
_MODEL_PROVIDER_SDK_PREFIXES = ("openai", "anthropic")


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _files_under(*relative_dirs: str) -> list[Path]:
    files: list[Path] = []
    for relative_dir in relative_dirs:
        files.extend((SRC_ROOT / relative_dir).rglob("*.py"))
    return files


def _assert_no_forbidden_imports(files: list[Path], forbidden_prefixes: tuple[str, ...], boundary_name: str) -> None:
    violations: list[str] = []
    for file in files:
        for module in _imported_top_level_modules(file):
            if module.startswith(forbidden_prefixes) or module in forbidden_prefixes:
                violations.append(f"{file.relative_to(SRC_ROOT)} imports {module!r}")
    assert not violations, f"{boundary_name} boundary violated:\n" + "\n".join(violations)


def test_domain_does_not_import_haystack() -> None:
    _assert_no_forbidden_imports(_files_under("domain"), _HAYSTACK_PREFIXES, "domain -> Haystack")


def test_domain_does_not_import_an_http_framework() -> None:
    _assert_no_forbidden_imports(_files_under("domain"), _HTTP_FRAMEWORK_PREFIXES, "domain -> HTTP framework")


def test_domain_does_not_import_a_database_driver_or_orm() -> None:
    _assert_no_forbidden_imports(_files_under("domain"), _DATABASE_PREFIXES, "domain -> database driver/ORM")


def test_domain_does_not_import_a_cloud_or_model_provider_sdk() -> None:
    _assert_no_forbidden_imports(
        _files_under("domain"), _CLOUD_SDK_PREFIXES + _MODEL_PROVIDER_SDK_PREFIXES, "domain -> cloud/provider SDK"
    )


def test_application_does_not_import_haystack_directly() -> None:
    # Application code depends on PipelinePort/ModelExecutionPort — the
    # *port*, never the concrete Haystack implementation behind it. Only
    # `infrastructure.haystack` may import `haystack`.
    _assert_no_forbidden_imports(_files_under("application"), _HAYSTACK_PREFIXES, "application -> Haystack")


def test_application_does_not_import_an_http_framework_or_database_driver() -> None:
    _assert_no_forbidden_imports(
        _files_under("application"),
        _HTTP_FRAMEWORK_PREFIXES + _DATABASE_PREFIXES,
        "application -> HTTP framework/database driver",
    )


def test_canonical_contracts_do_not_expose_haystack_types() -> None:
    _assert_no_forbidden_imports(_files_under("contracts"), _HAYSTACK_PREFIXES, "contracts -> Haystack")


def test_only_the_haystack_infrastructure_package_imports_haystack() -> None:
    everything_except_haystack_infra = [
        f
        for f in SRC_ROOT.rglob("*.py")
        if "infrastructure/haystack" not in f.as_posix() and "infrastructure\\haystack" not in f.as_posix()
    ]
    _assert_no_forbidden_imports(
        everything_except_haystack_infra, _HAYSTACK_PREFIXES, "codebase (outside infrastructure.haystack) -> Haystack"
    )


# -- Qdrant (Qdrant refactor item 14, 34, 128): the same anti-corruption
# boundary applies to qdrant_client/haystack_integrations as already applies
# to bare haystack — a qdrant_client.PointStruct/Filter/ScoredPoint or a
# haystack_integrations Qdrant type SHALL never cross out of
# infrastructure.haystack.document_stores.qdrant_projection_store. Ports
# (VectorProjectionPort/SemanticRetrievalPort) and canonical contracts only
# ever see plain Pulse types (ProjectionRecord/SemanticCandidate/...).


def test_domain_does_not_import_qdrant() -> None:
    _assert_no_forbidden_imports(_files_under("domain"), _QDRANT_PREFIXES, "domain -> Qdrant")


def test_application_does_not_import_qdrant_directly() -> None:
    # Application code depends on VectorProjectionPort/SemanticRetrievalPort
    # — the *port*, never the concrete Qdrant implementation behind it.
    _assert_no_forbidden_imports(_files_under("application"), _QDRANT_PREFIXES, "application -> Qdrant")


def test_canonical_contracts_do_not_expose_qdrant_types() -> None:
    _assert_no_forbidden_imports(_files_under("contracts"), _QDRANT_PREFIXES, "contracts -> Qdrant")


def test_only_the_haystack_infrastructure_package_imports_qdrant() -> None:
    everything_except_haystack_infra = [
        f
        for f in SRC_ROOT.rglob("*.py")
        if "infrastructure/haystack" not in f.as_posix() and "infrastructure\\haystack" not in f.as_posix()
    ]
    _assert_no_forbidden_imports(
        everything_except_haystack_infra, _QDRANT_PREFIXES, "codebase (outside infrastructure.haystack) -> Qdrant"
    )
