# Official Microsoft Azure Functions Python base image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim

# Create non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Install requirements
COPY containers/content-enricher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install shared libs package
COPY libs /app/libs
RUN pip install --no-cache-dir /app/libs

# Copy application code
COPY containers/content-enricher/ .

# Set ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
