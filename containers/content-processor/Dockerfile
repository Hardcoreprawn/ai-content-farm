# Multi-stage build for efficiency using Microsoft's official Azure Functions Python base
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies to a standard location
WORKDIR /app
# Copy requirements from the container directory when using repo-root build context
COPY containers/content-processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage using Microsoft's official Azure Functions Python base
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
WORKDIR /app
COPY containers/content-processor/ .

# Copy top-level libs so runtime code can import `libs.blob_storage`
COPY libs /app/libs
# Install shared libs package
RUN pip install --no-cache-dir /app/libs

# Set ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add user's local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
