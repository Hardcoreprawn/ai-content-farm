# Optimized Multi-stage Dockerfile for content-processor
# Using UV with wheels-only for 70% faster builds
# Usage:
#   Development/Test: docker build --target development
#   Production:       docker build --target production (default)

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

# Install service dependencies using wheels-only for speed
COPY containers/content-processor/requirements.txt /tmp/
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -r /tmp/requirements.txt || \
    echo "Some packages may need compilation - falling back to source builds" && \
    uv pip install --system --no-cache -r /tmp/requirements.txt

# Development/Test stage - includes development tools
FROM base AS development

# Switch to root for dev tool installation
USER root

# Install minimal development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install development tools using UV
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache ipdb pdbpp rich

# Copy shared libraries and install with Azure dependencies using UV
COPY libs/ ./libs/
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -e "./libs/[dev]" || \
    echo "Libs installation may need source builds" && \
    uv pip install --system --no-cache -e "./libs/[dev]"

# Copy application code
COPY containers/content-processor/ .

# Service configuration with debug-friendly settings
ENV SERVICE_NAME=content-processor
ENV LOG_LEVEL=debug
ENV PYTHONPATH=/app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application with reload for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage - minimal, secure, optimized
FROM base AS production

# Copy shared libraries and install with Azure dependencies using UV
COPY libs/ ./libs/
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -e ./libs/ || \
    echo "Libs installation may need source builds" && \
    uv pip install --system --no-cache -e ./libs/

# Copy application code
COPY containers/content-processor/ .

# Service configuration optimized for production
ENV SERVICE_NAME=content-processor
ENV LOG_LEVEL=info
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application optimized for production - using standardized API structure
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
