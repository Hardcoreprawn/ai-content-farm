# Multi-stage Dockerfile for both development/test and production environments
# Usage:
#   Development/Test: docker build --target development
#   Production:       docker build --target production (default)
# Updated for smart deployment testing

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
COPY containers/content-processor/requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Development/Test stage - includes development tools
FROM base AS development

# Install development tools for debugging
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir ipdb pdbpp rich

# Copy shared libraries
COPY libs/ ./libs/

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

# Copy shared libraries
COPY libs/ ./libs/

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
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
