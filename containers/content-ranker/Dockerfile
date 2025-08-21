# Build from web-services tier (has ALL required dependencies)
FROM ai-content-farm-base:web-services AS base

# Copy application code
COPY containers/content-ranker/ .

# Service-specific configuration
ENV SERVICE_NAME=content-ranker
ENV LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
