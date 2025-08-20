FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY libs /app/libs
# Install shared libs package
RUN pip install --no-cache-dir /app/libs
COPY containers/collector-scheduler/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY containers/collector-scheduler/ /app

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check (assuming the scheduler creates a health endpoint or file)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ps aux | grep -v grep | grep python || exit 1

CMD ["python", "main.py"]
