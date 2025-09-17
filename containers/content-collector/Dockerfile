# Multi-stage Dockerfile for content-collector
# Base stage with common dependencies
FROM python:3.11-slim AS base

# System dependencies (cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.12 \
    curl=8.14.1-2 \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install service dependencies
COPY containers/content-collector/requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt

# 3. Install shared libraries with Azure dependencies
COPY libs/ ./libs/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e "./libs/[dev]"

# 4. Copy application code (changes most frequently)
COPY containers/content-collector/ .

# Service configuration
ENV SERVICE_NAME=content-collector
ENV LOG_LEVEL=info

# Development stage with test tools
FROM base AS development

# Install development tools for debugging
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir ipdb pdbpp

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
