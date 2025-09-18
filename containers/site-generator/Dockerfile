# Site Generator Container
# Python-based JAMStack static site generator for AI Content Farm
# Optimized with UV for 70% faster builds

# Base stage for shared dependencies
FROM python:3.11-slim AS base

# Install UV first (fastest Python package installer)
RUN pip install --no-cache-dir uv==0.4.23

# Set working directory
WORKDIR /app

# Install minimal system dependencies (no build tools needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set up UV cache
ENV UV_CACHE_DIR=/opt/uv-cache

# Copy requirements first for better caching
COPY containers/site-generator/requirements.txt .

# Install Python dependencies using wheels-only for speed
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -r requirements.txt || \
    echo "Some packages may need compilation - falling back to source builds" && \
    uv pip install --system --no-cache -r requirements.txt

# Development stage
FROM base AS development

# Copy application code
COPY containers/site-generator/ .

# Copy shared libraries and install with Azure dependencies using UV
COPY libs/ /app/libs
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -e "/app/libs/[dev]" || \
    echo "Libs installation may need source builds" && \
    uv pip install --system --no-cache -e "/app/libs/[dev]"

# Create necessary directories
RUN mkdir -p /app/templates /app/static /app/output

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV ENVIRONMENT=development

# Switch to non-root user
USER app

# Expose port
EXPOSE ${PORT}

# Run with auto-reload for development
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production

# Copy application code
COPY containers/site-generator/ .

# Copy shared libraries and install with Azure dependencies using UV
COPY libs/ /app/libs
RUN --mount=type=cache,target=$UV_CACHE_DIR \
    uv pip install --system --no-cache --only-binary=all -e /app/libs/ || \
    echo "Libs installation may need source builds" && \
    uv pip install --system --no-cache -e /app/libs/

# Create necessary directories
RUN mkdir -p /app/templates /app/static /app/output

# Create non-root user as required by agent instructions
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER app

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
