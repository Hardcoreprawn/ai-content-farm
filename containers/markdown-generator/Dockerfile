# Build from web-services tier (has ALL required dependencies)
FROM ai-content-farm-base:web-services AS base

# Copy application code
COPY containers/markdown-generator/ .

# Create application directories in writable location
RUN mkdir -p /tmp/markdown-temp

# Service-specific configuration  
ENV SERVICE_NAME=markdown-generator
ENV LOG_LEVEL=info
ENV TEMP_DIR=/tmp/markdown-temp

# Expose port
EXPOSE 8000

# Health check (curl available in base image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

# Use existing appuser from base image
USER appuser

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
