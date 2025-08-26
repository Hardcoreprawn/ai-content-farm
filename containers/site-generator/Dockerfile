# Multi-stage Dockerfile for site-generator
# Updated: 2025-08-26 - Testing quality gate fixes
# Base stage with common dependencies
FROM python:3.11-slim AS base

# System dependencies (cached layer)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# 1. Install common dependencies first (highest cache hit rate)
COPY containers/base/requirements-common.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements-common.txt

# 2. Install service-specific dependencies
COPY containers/site-generator/requirements-prod.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements-prod.txt

# 3. Copy shared libraries
COPY libs/ ./libs/

# 4. Copy application code (changes most frequently)
COPY containers/site-generator/ .

# Service configuration
ENV SERVICE_NAME=site-generator
ENV LOG_LEVEL=info

# Development stage with test tools
FROM base AS development

# Install test dependencies
COPY containers/site-generator/requirements-test.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements-test.txt

# Install development tools for debugging
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install ipdb pdbpp

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Production stage - optimized and secure
FROM base AS production

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
