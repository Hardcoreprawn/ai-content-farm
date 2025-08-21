# Build from web-services tier (inherits foundation + common + web deps)
FROM ai-content-farm-base:web-services AS base

# Add ONLY service-specific dependencies
# (FastAPI, uvicorn, pydantic, Azure SDK, testing, etc. come from base layers)
COPY containers/content-enricher/requirements-unique.txt .
RUN pip install --no-cache-dir -r requirements-unique.txt

# Copy application code
COPY containers/content-enricher/ .

# Service-specific configuration
ENV SERVICE_NAME=content-enricher
ENV LOG_LEVEL=info

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
