# Build from web-services tier (has ALL required dependencies)
FROM ai-content-farm-base:web-services AS base

# Copy application code
COPY containers/content-processor/ .

# Service-specific configuration
ENV SERVICE_NAME=content-processor
ENV LOG_LEVEL=info

# Health check (httpx available from base layers)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
