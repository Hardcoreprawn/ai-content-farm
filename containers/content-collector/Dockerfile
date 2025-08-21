# Build from data-processing tier (includes web + data processing deps)
FROM ai-content-farm-base:data-processing AS base

# Add ONLY service-specific dependencies  
# (FastAPI, beautifulsoup4, feedparser, etc. come from data-processing tier)
COPY containers/content-collector/requirements-unique.txt .
RUN pip install --no-cache-dir -r requirements-unique.txt

# Copy application code
COPY containers/content-collector/ .

# Service-specific configuration
ENV SERVICE_NAME=content-collector
ENV LOG_LEVEL=info

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
