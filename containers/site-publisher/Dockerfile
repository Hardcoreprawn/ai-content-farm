# Multi-stage Dockerfile for site-publisher
# Stage 1: Build Hugo binary from Go
# Stage 2: Python runtime with Hugo

# =============================================================================
# Stage 1: Hugo Builder (Go)
# =============================================================================
FROM golang:1.24-alpine AS hugo-builder

# Hugo version (pinned for security)
ARG HUGO_VERSION=0.151.0

# Install Hugo from source
RUN apk add --no-cache git && \
    go install github.com/gohugoio/hugo@v${HUGO_VERSION}

# Verify Hugo installed correctly
RUN hugo version

# =============================================================================
# Stage 2: Python Runtime (with Hugo)
# =============================================================================
FROM python:3.13-slim AS production

# Labels for container metadata
LABEL maintainer="AI Content Farm Team"
LABEL description="Static site publisher with Hugo"
LABEL version="1.0.0"

# Copy Hugo binary from builder stage
COPY --from=hugo-builder /go/bin/hugo /usr/local/bin/hugo

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Verify Hugo works
RUN hugo version

# Create non-root user (SECURITY REQUIREMENT)
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY containers/site-publisher/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy shared libraries from monorepo
COPY --chown=app:app libs /app/libs

# Copy application code
COPY --chown=app:app containers/site-publisher/. .

# Ensure Hugo config is accessible
RUN chmod -R 755 /app/hugo-config

# Switch to non-root user (SECURITY REQUIREMENT)
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
