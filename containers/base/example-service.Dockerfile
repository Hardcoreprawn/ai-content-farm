# Example: Content Generator Container using Multi-Tier Base
# Only contains UNIQUE dependencies for this specific service

# Build from web-services tier (inherits foundation + common + web deps)
FROM ai-content-farm-base:web-services AS base

# Add ONLY service-specific dependencies
# (Everything else comes from the base layers)
COPY containers/content-generator/requirements-unique.txt .
RUN pip install --no-cache-dir -r requirements-unique.txt

# Copy application code
COPY containers/content-generator/ .

# Service-specific configuration
ENV SERVICE_NAME=content-generator
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Default command (inherited from base, but can override)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
