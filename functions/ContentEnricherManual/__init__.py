import logging
import azure.functions as func
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from azure.storage.blob import BlobServiceClient

# Import the shared enrichment logic
import sys
sys.path.append('../ContentEnricher')
try:
    from enricher_core import process_content_enrichment
except ImportError:
    logging.error("Failed to import enricher_core - ensure ContentEnricher is deployed")
    process_content_enrichment = None


def create_standard_response(status: str, message: str, data: Optional[Dict[str, Any]] = None, 
                           errors: Optional[List[str]] = None, execution_time_ms: int = 0) -> Dict[str, Any]:
    """Create standardized REST API response following project conventions."""
    return {
        "status": status,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "function": "ContentEnricher",
            "version": "1.0.0",
            "execution_time_ms": execution_time_ms
        }
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    ContentEnricher Manual API - HTTP endpoint for manual content enrichment.
    
    POST /api/content-enricher/process
    Body: {"blob_name": "ranked_2025-08-12_14-30-00.json"}
    
    Returns: Standardized REST response with enrichment results.
    """
    start_time = datetime.utcnow()
    logging.info("ContentEnricher Manual API called")

    blob_name = None

    try:
        # Validate request method
        if req.method != 'POST':
            response = create_standard_response(
                "error",
                f"Method {req.method} not allowed. Use POST.",
                errors=["HTTP method must be POST"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=405,
                mimetype="application/json"
            )

        # Parse and validate request body
        try:
            req_body = req.get_json()
        except ValueError:
            response = create_standard_response(
                "error", 
                "Invalid JSON in request body",
                errors=["Request body must be valid JSON"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=400,
                mimetype="application/json"
            )
        
        if not req_body:
            response = create_standard_response(
                "error",
                "Missing request body", 
                errors=["Request body is required"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=400,
                mimetype="application/json"
            )
        
        if 'blob_name' not in req_body:
            response = create_standard_response(
                "error",
                "Missing required parameter",
                errors=["Request body must contain 'blob_name' parameter"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=400,
                mimetype="application/json"
            )

        blob_name = req_body['blob_name']
        logging.info(f"Processing ranked topics blob: {blob_name}")

        # Validate environment variables
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            response = create_standard_response(
                "error",
                "Storage configuration missing",
                errors=["AzureWebJobsStorage environment variable not configured"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=500,
                mimetype="application/json"
            )

        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Check if input blob exists
        input_blob_path = f"ranked-topics/{blob_name}"
        input_blob_client = blob_service_client.get_blob_client(
            container="content-pipeline",
            blob=input_blob_path
        )

        if not input_blob_client.exists():
            response = create_standard_response(
                "error",
                f"Input blob not found",
                errors=[f"Blob '{input_blob_path}' does not exist in 'content-pipeline' container"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=404,
                mimetype="application/json"
            )

        # Download and parse ranked topics data
        try:
            blob_content = input_blob_client.download_blob().readall().decode('utf-8')
            ranked_data = json.loads(blob_content)
        except json.JSONDecodeError as e:
            response = create_standard_response(
                "error",
                "Invalid JSON in input blob",
                errors=[f"Failed to parse ranked topics: {str(e)}"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=400,
                mimetype="application/json"
            )

        # Validate enrichment service availability
        if process_content_enrichment is None:
            response = create_standard_response(
                "error",
                "Content enrichment service unavailable",
                errors=["enricher_core module not available - check ContentEnricher deployment"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=503,
                mimetype="application/json"
            )

        total_topics = ranked_data.get('total_topics', 0)
        logging.info(f"Processing {total_topics} ranked topics from {blob_name}")

        # Process content enrichment using functional core
        enrichment_result = process_content_enrichment(ranked_data)

        # Upload enriched result to blob storage
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        output_blob_path = f"enriched-topics/enriched_manual_{timestamp}.json"

        output_blob_client = blob_service_client.get_blob_client(
            container="content-pipeline",
            blob=output_blob_path
        )

        output_json = json.dumps(enrichment_result, indent=2)
        output_blob_client.upload_blob(output_json, overwrite=True)

        # Calculate execution time
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Create success response
        stats = enrichment_result['enrichment_statistics']
        response_data = {
            "input_blob": f"content-pipeline/{input_blob_path}",
            "output_blob": f"content-pipeline/{output_blob_path}",
            "topics_processed": stats['total_topics'],
            "enrichment_statistics": stats,
            "source_file": enrichment_result.get('source_file', blob_name)
        }

        response = create_standard_response(
            "success",
            f"Successfully enriched {stats['total_topics']} topics with multi-source research",
            response_data,
            execution_time_ms=execution_time
        )

        logging.info(f"ContentEnricher completed: {stats}")

        return func.HttpResponse(
            json.dumps(response, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        error_msg = f"Unexpected error during content enrichment: {str(e)}"
        logging.error(error_msg)
        
        response = create_standard_response(
            "error",
            error_msg,
            errors=[str(e)],
            execution_time_ms=execution_time
        )
        
        return func.HttpResponse(
            json.dumps(response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
