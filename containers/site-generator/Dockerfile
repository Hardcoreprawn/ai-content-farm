# Build from web-services tier (inherits foundation + common + web deps)
FROM ai-content-farm-base:web-services AS base

# Add ONLY service-specific dependencies
# (FastAPI, uvicorn, pydantic, Azure SDK, etc. come from base layers)
COPY containers/site-generator/requirements-unique.txt .
RUN pip install --no-cache-dir -r requirements-unique.txt

# Copy application code
COPY containers/site-generator/ .

# Service-specific configuration
ENV SERVICE_NAME=site-generator
ENV LOG_LEVEL=info

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check configuration (use curl directly)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
