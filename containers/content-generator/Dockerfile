# Multi-stage Dockerfile for content-generator
# Base stage with common dependencies
FROM python:3.11-slim AS base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install production dependencies
COPY containers/content-generator/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-prod.txt

# Copy shared libraries
COPY libs/ ./libs/

# Copy application code
COPY containers/content-generator/ .

# Development stage with test tools
FROM base AS development

# Install test dependencies
COPY containers/content-generator/requirements-test.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-test.txt

# Install development tools for debugging
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install ipdb pdbpp

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Production stage - optimized and secure
FROM base AS production

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
