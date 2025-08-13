import azure.functions as func
import json
import logging
from datetime import datetime

app = func.FunctionApp()

# Test Function - Minimal validation function


@app.route(route="test", auth_level=func.AuthLevel.ANONYMOUS)
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    """Simple test function to validate runtime works"""
    logging.info('Test function processed a request.')

    return func.HttpResponse(
        json.dumps({
            "status": "success",
            "message": "Test function is working correctly",
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
                "function": "test_function",
                "runtime": "Azure Functions v4 Python"
            },
            "metadata": {
                "version": "1.0.0",
                "model": "new_programming_model"
            }
        }),
        status_code=200,
        mimetype="application/json"
    )

# Health check endpoint


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ai-content-farm-functions"
        }),
        status_code=200,
        mimetype="application/json"
    )
