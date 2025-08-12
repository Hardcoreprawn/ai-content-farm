import logging
import azure.functions as func
import json
import os
from datetime import datetime

# Test 4: Function-only change for pipeline optimization (2025-08-12T11:09:00Z)
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

# Import the functional core from local module
from ranker_core import process_content_ranking


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

# Standardized container configuration for content pipeline
PIPELINE_CONTAINERS = {
    'input': {
        'topic_collection_queue': 'topic-collection-queue',
        'content_enrichment_complete': 'content-enrichment-complete'
    },
    'output': {
        'content_ranking_complete': 'content-ranking-complete',
        'content_enrichment_queue': 'content-enrichment-queue'
    },
    'status': {
        'job_status': 'job-status',
        'processing_errors': 'processing-errors',
        'dead_letter_queue': 'dead-letter-queue'
    }
}


def create_standard_response(status: str, message: str, data=None, errors=None, metadata=None):
    """Create standardized API response format"""
    response = {
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if data is not None:
        response["data"] = data
    if errors is not None:
        response["errors"] = errors
    if metadata is not None:
        response["metadata"] = metadata
    return response


def get_standardized_blob_client(storage_account_name: str = None):
    """Create standardized blob service client with Managed Identity"""
    if not storage_account_name:
        storage_account_name = os.environ.get('OUTPUT_STORAGE_ACCOUNT')

    if not storage_account_name:
        raise ValueError(
            "Storage account name not provided and OUTPUT_STORAGE_ACCOUNT not set")

    credential = DefaultAzureCredential()
    return BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=credential
    )


def process_blob_path(blob_path: str):
    """Parse and validate blob path in format 'container/blob-name'"""
    if not blob_path:
        raise ValueError("Blob path is required")

    parts = blob_path.split('/', 1)
    if len(parts) != 2:
        raise ValueError("Path must be in format 'container/blob-name'")

    return parts[0], parts[1]  # container, blob_name


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
Test 4: Function-only change for pipeline optimization validation
Updated: 2025-08-12T11:09:00Z

Azure Function implementation for content ranking.
This function processes topics and generates ranking scores.
"""
    import json
    import logging
    import azure.functions as func

    logging.info('ContentRanker HTTP worker function triggered')

    try:
        # Validate HTTP method
        if req.method != 'POST':
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    f"Method {req.method} not allowed. Use POST.",
                    errors=[{"code": "METHOD_NOT_ALLOWED",
                             "detail": "Only POST method is supported"}]
                )),
                status_code=405,
                headers={'Content-Type': 'application/json'}
            )

        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Invalid JSON in request body",
                    errors=[{"code": "INVALID_JSON",
                             "detail": "Request body must be valid JSON"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        if not req_body:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Request body is required",
                    errors=[
                        {"code": "MISSING_BODY", "detail": "JSON body with input_blob_path and output_blob_path is required"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        # Validate required fields
        input_blob_path = req_body.get('input_blob_path')
        output_blob_path = req_body.get('output_blob_path')

        if not input_blob_path:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Missing required field: input_blob_path",
                    errors=[{"code": "MISSING_INPUT_PATH",
                             "detail": "input_blob_path is required"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        if not output_blob_path:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Missing required field: output_blob_path",
                    errors=[{"code": "MISSING_OUTPUT_PATH",
                             "detail": "output_blob_path is required"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        # Initialize blob service client with Managed Identity
        try:
            blob_service_client = get_standardized_blob_client()
        except ValueError as e:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Storage account not configured",
                    errors=[{"code": "STORAGE_CONFIG_ERROR",
                             "detail": str(e)}]
                )),
                status_code=503,
                headers={'Content-Type': 'application/json'}
            )

        # Extract container and blob name from input path
        try:
            input_container, input_blob_name = process_blob_path(
                input_blob_path)
        except ValueError as e:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Invalid input_blob_path format",
                    errors=[{"code": "INVALID_PATH_FORMAT",
                             "detail": str(e)}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        # Read input blob
        try:
            blob_client = blob_service_client.get_blob_client(
                container=input_container, blob=input_blob_name)
            blob_content = blob_client.download_blob().readall().decode('utf-8')
            blob_data = json.loads(blob_content)

            logging.info(
                f"Processing {blob_data.get('count', 0)} topics from {blob_data.get('subject', 'unknown')} subreddit")

        except Exception as e:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    f"Failed to read input blob: {str(e)}",
                    errors=[{"code": "BLOB_READ_ERROR", "detail": str(e)}]
                )),
                status_code=404,
                headers={'Content-Type': 'application/json'}
            )

        # Process content ranking using functional core
        start_time = datetime.utcnow()
        ranking_result = process_content_ranking(blob_data, RANKING_CONFIG)
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Log results
        total_ranked = ranking_result['total_topics']
        original_count = blob_data.get('count', 0)

        logging.info(
            f"ContentRanker completed: {total_ranked}/{original_count} topics ranked and filtered")

        if total_ranked > 0:
            top_score = ranking_result['topics'][0]['ranking_score']
            logging.info(f"Top ranking score: {top_score}")

        # Extract container and blob name from output path
        try:
            output_container, output_blob_name = process_blob_path(
                output_blob_path)
        except ValueError as e:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Invalid output_blob_path format",
                    errors=[{"code": "INVALID_OUTPUT_PATH_FORMAT",
                             "detail": str(e)}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        # Ensure output container exists
        try:
            container_client = blob_service_client.get_container_client(
                output_container)
            container_client.create_container()
            logging.info(f"Created container: {output_container}")
        except Exception:
            # Container might already exist, which is fine
            pass

        # Write output blob
        try:
            output_json = json.dumps(ranking_result, indent=2)
            output_blob_client = blob_service_client.get_blob_client(
                container=output_container, blob=output_blob_name)
            output_blob_client.upload_blob(output_json, overwrite=True)

            logging.info(f"Ranked topics written to {output_blob_path}")

        except Exception as e:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    f"Failed to write output blob: {str(e)}",
                    errors=[{"code": "BLOB_WRITE_ERROR", "detail": str(e)}]
                )),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )

        # Return success response
        return func.HttpResponse(
            json.dumps(create_standard_response(
                "success",
                f"Content ranking completed: {total_ranked}/{original_count} topics ranked and filtered",
                data={
                    "input_path": input_blob_path,
                    "output_path": output_blob_path,
                    "total_ranked": total_ranked,
                    "original_count": original_count,
                    "top_score": ranking_result['topics'][0]['ranking_score'] if total_ranked > 0 else None,
                    "processing_time_seconds": processing_time
                },
                metadata={
                    "function": "ContentRanker",
                    "version": "2.0",
                    "config": RANKING_CONFIG
                }
            )),
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in ContentRanker: {e}")
        return func.HttpResponse(
            json.dumps(create_standard_response(
                "error",
                "JSON parsing error",
                errors=[{"code": "JSON_PARSE_ERROR", "detail": str(e)}]
            )),
            status_code=400,
            headers={'Content-Type': 'application/json'}
        )

    except Exception as e:
        logging.error(f"Unexpected error in ContentRanker: {e}")
        return func.HttpResponse(
            json.dumps(create_standard_response(
                "error",
                "Internal server error",
                errors=[{"code": "INTERNAL_ERROR", "detail": str(e)}]
            )),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
