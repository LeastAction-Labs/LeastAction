# syntax=docker/dockerfile:1.4

# ============================================================================
# Builder Stage - Install dependencies
# ============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy\
    # FIX: Force uv to use the Python 3.12 installed in this image
    UV_PYTHON_PREFERENCE=only-system

WORKDIR /backend

# Install build dependencies needed for compiling Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installer (much faster than pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy only dependency files first (better layer caching).
# Build context is the repo root (see docker-compose: context: ..), so
# dependency files are under backend/.
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies into .venv
# --frozen ensures reproducible builds
# --no-dev excludes development dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ============================================================================
# Runtime Stage - Minimal production image
# ============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /backend

# Create non-root user early
RUN useradd -m -u 1000 celeryuser

# Install git (required by gitpython) and Node.js (required to run the official
# Azure MCP server that the Azure data-plane tools proxy). Pre-bake the pinned
# @azure/mcp package so spawning it at runtime needs no network fetch.
RUN apt-get update && apt-get install -y git curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @azure/mcp@0.5.0 \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary for running commands with "uv run"
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Pre-install the official awslabs MCP servers that the AWS data-plane tools proxy.
# Each lands as a console script on PATH (/usr/local/bin) so runtime spawns need no
# network fetch. Installed isolated via uv tool; creds are passed at spawn time.
ENV UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_CACHE_DIR=/opt/uv-cache
RUN uv tool install awslabs.redshift-mcp-server \
    && uv tool install awslabs.aws-dataprocessing-mcp-server \
    && uv tool install awslabs.s3-tables-mcp-server \
    && uv tool install awslabs.cloudwatch-mcp-server \
    && uv tool install awslabs.billing-cost-management-mcp-server \
    && uv tool install awslabs.aws-documentation-mcp-server \
    && chown -R celeryuser:celeryuser /opt/uv-cache \
    && chmod -R a+rX /opt/uv-tools /opt/uv-cache

# Copy virtual environment from builder
COPY --from=builder --chown=celeryuser:celeryuser /backend/.venv /backend/.venv

# Copy application code (build context is the repo root)
COPY --chown=celeryuser:celeryuser backend/ /backend/

# Bake the shared config and docs into the image. The backend resolves these
# via get_config_path(), which walks up to the dir named "backend" and uses the
# sibling "config"/ — code lives at /backend, so /config and /docs satisfy it.
COPY --chown=celeryuser:celeryuser config /config
COPY --chown=celeryuser:celeryuser docs /docs

# Create logs directory with correct ownership before switching user
# Docker named volumes are initialized from the image directory on first mount
RUN mkdir -p /logs && chown celeryuser:celeryuser /logs

# Switch to non-root user
USER celeryuser

# Default command
CMD ["bash"]
