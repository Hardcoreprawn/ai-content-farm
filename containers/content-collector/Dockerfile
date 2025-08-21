# Standard Python base image (migrated from Azure Functions)
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy top-level libs so runtime code can import `libs.blob_storage`
COPY libs /app/libs
# Install the shared libs package so runtime imports work without PYTHONPATH
RUN pip install --no-cache-dir /app/libs

# Copy requirements and install dependencies as root first
# (build context is repo root so reference the container path)
COPY containers/content-collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY containers/content-collector/ .

# Set ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
