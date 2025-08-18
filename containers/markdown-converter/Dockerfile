FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (use container path for repo-root build context)
COPY containers/markdown-converter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/output /app/site

# Copy application code
# Copy top-level libs so runtime code can import `libs.blob_storage`
COPY libs /app/libs
# Install shared libs package
RUN pip install --no-cache-dir /app/libs

# Copy application code from its container directory
COPY containers/markdown-converter/ .

# Create a basic health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/healthcheck.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
