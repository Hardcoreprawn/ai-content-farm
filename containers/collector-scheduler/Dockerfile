# Build from scheduler tier (has APScheduler, httpx, fastapi, etc.)
FROM ai-content-farm-base:scheduler AS base

# Copy application code
COPY containers/collector-scheduler/ .

# Service-specific configuration
ENV SERVICE_NAME=collector-scheduler
ENV LOG_LEVEL=info

# Health check (check for running python process)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ps aux | grep -v grep | grep python || exit 1

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["python", "main.py"]
