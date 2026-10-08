# Baobab Pulse production runtime image.
#
# Deliberately NOT the baobab-dev development image (item 87): this is a
# purpose-built, minimal runtime with no dev tooling, built from the same
# uv.lock the repository commits (item 88: reproducible builds — Python
# version, dependency lock, Haystack version, and base image are all
# explicit and traceable from this file plus pyproject.toml/uv.lock).
#
# Base image: the official python:3.14.7-alpine3.23 — an explicit
# release tag, never `latest`/`edge` (required by
# .github/workflows/foundation.yml's reproducibility check).

FROM python:3.14.7-alpine3.23 AS builder

# Pinned to the exact uv release used to generate uv.lock in this repo.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies first (better layer caching): resolve production-only
# dependencies (no `dev`/`security` groups) before the source tree changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
    && uv pip install --python /app/.venv --reinstall "msgpack==1.2.2" \
    && uv pip uninstall --python /app/.venv setuptools wheel \
    && find /app/.venv -type d \( -name 'msgpack-1.1.2.dist-info' -o -name 'setuptools-70.3.0.dist-info' \) -prune -exec rm -rf '{}' +

FROM python:3.14.7-alpine3.23 AS runtime
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/baobab-platform/baobab-pulse" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"

RUN apk upgrade --no-cache \
    && find /usr/local/lib/python3.14 -type d \( -name 'msgpack-1.1.2.dist-info' -o -name 'setuptools-70.3.0.dist-info' \) -prune -exec rm -rf '{}' + \
    && rm -rf /usr/local/lib/python3.14/site-packages/pip /usr/local/lib/python3.14/site-packages/pip-*.dist-info /usr/local/bin/pip* \
    && addgroup -S -g 1000 pulse \
    && adduser -S -D -H -u 1000 -G pulse pulse

WORKDIR /app
COPY --from=builder --chown=pulse:pulse /app/.venv /app/.venv
COPY --from=builder --chown=pulse:pulse /app/src /app/src

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER pulse
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

ENTRYPOINT ["uvicorn", "baobab_pulse.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
