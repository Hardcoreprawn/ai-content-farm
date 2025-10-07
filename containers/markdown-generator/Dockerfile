# Multi-stage build for markdown-generator container

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install (from repository root context)
COPY containers/markdown-generator/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production Runtime
FROM python:3.11-slim AS production

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code (from repository root context)
COPY --chown=app:app containers/markdown-generator/ .

# Set PATH for user packages
ENV PATH=/home/app/.local/bin:$PATH

# Switch to non-root user
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
