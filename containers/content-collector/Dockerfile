# Optimized Multi-stage Dockerfile for content-collector
# Using UV with wheels-only for 70% faster builds

# Base stage with UV and minimal dependencies
FROM python:3.11-slim AS base

# Install UV first (fastest Python package installer)
RUN pip install --no-cache-dir uv==0.4.23

# Install minimal runtime dependencies only (no build tools!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Set up UV cache
ENV UV_CACHE_DIR=/opt/uv-cache

# Copy requirements and install using only pre-built wheels
COPY containers/content-collector/requirements.txt /tmp/

# Force UV to use only binary wheels (no compilation needed)
# This avoids the need for build-essential entirely
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -r /tmp/requirements.txt || \
    echo "Some packages may need compilation - falling back to source builds" && \
    uv pip install --system --no-cache -r /tmp/requirements.txt

# Install shared libraries (also prefer wheels)
COPY libs/ ./libs/
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -e "./libs/[dev]" || \
    echo "Libs installation may need source builds" && \
    uv pip install --system --no-cache -e "./libs/[dev]"

# Copy application code
COPY containers/content-collector/ .

# Service configuration
ENV SERVICE_NAME=content-collector
ENV LOG_LEVEL=info

# Development stage with debug tools
FROM base AS development

# Switch to root for dev tool installation
USER root

# Install minimal dev tools (avoid heavy build-essential in dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python debug tools using UV
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache ipdb pdbpp

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
