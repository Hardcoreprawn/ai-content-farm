# Site Generator Container
# Python-based JAMStack static site generator for AI Content Farm

# Base stage for shared dependencies
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY containers/site-generator/requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development

# Copy application code
COPY containers/site-generator/ .

# Copy shared libraries
COPY libs/ /app/libs

# Create necessary directories
RUN mkdir -p /app/templates /app/static /app/output

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV ENVIRONMENT=development

# Expose port
EXPOSE ${PORT}

# Run with auto-reload for development
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production

# Copy application code
COPY containers/site-generator/ .

# Copy shared libraries
COPY libs/ /app/libs

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
