import logging
import azure.functions as func
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from azure.storage.blob import BlobServiceClient

# Import the shared ranking logic
import sys
sys.path.append('../ContentRanker')
try:
    from ranker_core import process_content_ranking
except ImportError:
    logging.error("Failed to import ranker_core - ensure ContentRanker is deployed")
    process_content_ranking = None


# Ranking configuration
RANKING_CONFIG = {
    'min_score_threshold': int(os.environ.get('MIN_SCORE_THRESHOLD', '100')),
    'min_comments_threshold': int(os.environ.get('MIN_COMMENTS_THRESHOLD', '10')),
    'weights': {
        'engagement': float(os.environ.get('ENGAGEMENT_WEIGHT', '0.4')),
        'freshness': float(os.environ.get('FRESHNESS_WEIGHT', '0.2')),
        'monetization': float(os.environ.get('MONETIZATION_WEIGHT', '0.3')),
        'seo': float(os.environ.get('SEO_WEIGHT', '0.1'))
    }
}


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
            "function": "ContentRanker",
            "version": "1.0.0",
            "execution_time_ms": execution_time_ms
        }
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    ContentRanker Manual API - HTTP endpoint for manual content ranking.
    
    POST /api/content-ranker/process
    Body: {"blob_name": "20250811_135221_reddit_technology.json"}
    
    Returns: Standardized REST response with ranking results.
    """
    start_time = datetime.utcnow()
    logging.info("ContentRanker Manual API called")
    
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
        logging.info(f"Processing blob: {blob_name}")
        
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
        input_blob_client = blob_service_client.get_blob_client(
            container="hot-topics", 
            blob=blob_name
        )
        
        if not input_blob_client.exists():
            response = create_standard_response(
                "error",
                f"Input blob not found",
                errors=[f"Blob '{blob_name}' does not exist in 'hot-topics' container"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=404,
                mimetype="application/json"
            )
        
        # Download and parse input blob
        try:
            blob_data_bytes = input_blob_client.download_blob().readall()
            blob_content = blob_data_bytes.decode('utf-8')
            blob_data = json.loads(blob_content)
        except json.JSONDecodeError as e:
            response = create_standard_response(
                "error",
                "Invalid JSON in input blob",
                errors=[f"Failed to parse blob content: {str(e)}"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process content ranking using shared core
        if process_content_ranking is None:
            response = create_standard_response(
                "error",
                "Content ranking service unavailable",
                errors=["ranker_core module not available - check ContentRanker deployment"]
            )
            return func.HttpResponse(
                json.dumps(response, indent=2),
                status_code=503,
                mimetype="application/json"
            )
        
        logging.info(f"Processing {blob_data.get('count', 0)} topics from {blob_name}")
        ranking_result = process_content_ranking(blob_data, RANKING_CONFIG)
        
        # Ensure content-pipeline container exists
        try:
            container_client = blob_service_client.get_container_client("content-pipeline")
            if not container_client.exists():
                container_client.create_container()
                logging.info("Created content-pipeline container")
        except Exception as e:
            logging.warning(f"Container creation issue (may already exist): {e}")
        
        # Save output to content-pipeline/ranked-topics/
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        output_blob_path = f"ranked-topics/ranked_manual_{timestamp}.json"
        
        output_blob_client = blob_service_client.get_blob_client(
            container="content-pipeline",
            blob=output_blob_path
        )
        
        output_json = json.dumps(ranking_result, indent=2)
        output_blob_client.upload_blob(output_json, overwrite=True)
        
        # Calculate execution time
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Create success response
        response_data = {
            "input_blob": f"hot-topics/{blob_name}",
            "output_blob": f"content-pipeline/{output_blob_path}",
            "topics_processed": ranking_result['total_topics'],
            "original_topic_count": blob_data.get('count', 0),
            "ranking_statistics": ranking_result.get('ranking_statistics', {}),
            "source_file": ranking_result.get('source_file', blob_name)
        }
        
        response = create_standard_response(
            "success",
            f"Successfully ranked {ranking_result['total_topics']} topics from {blob_name}",
            response_data,
            execution_time_ms=execution_time
        )
        
        logging.info(f"ContentRanker completed successfully: {ranking_result['total_topics']} topics ranked")
        
        return func.HttpResponse(
            json.dumps(response, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        error_msg = f"Unexpected error during content ranking: {str(e)}"
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
