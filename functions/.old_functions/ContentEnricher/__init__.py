import logging
import azure.functions as func
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient

# Import the functional core from local module
from .enricher_core import process_content_enrichment


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


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    ContentEnricher Azure Function - HTTP worker function.

    Processes ranked topics and produces enriched topics with research and fact-checking.

    Expected JSON payload:
    {
        "input_blob_path": "content-pipeline/ranked-topics/ranked_filename.json",
        "output_blob_path": "content-pipeline/enriched-topics/enriched_filename.json"
    }
    """
    logging.info('ContentEnricher HTTP worker function triggered')

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

        # Initialize blob service client
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Storage connection not configured",
                    errors=[{"code": "STORAGE_CONFIG_ERROR",
                             "detail": "AzureWebJobsStorage environment variable not set"}]
                )),
                status_code=503,
                headers={'Content-Type': 'application/json'}
            )

        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string)

        # Extract container and blob name from input path
        input_parts = input_blob_path.split('/', 1)
        if len(input_parts) != 2:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Invalid input_blob_path format",
                    errors=[{"code": "INVALID_PATH_FORMAT",
                             "detail": "Path must be in format 'container/blob-name'"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        input_container, input_blob_name = input_parts

        # Read input blob
        try:
            blob_client = blob_service_client.get_blob_client(
                container=input_container, blob=input_blob_name)
            blob_content = blob_client.download_blob().readall().decode('utf-8')
            ranked_data = json.loads(blob_content)

            total_topics = ranked_data.get('total_topics', 0)
            source_file = ranked_data.get('source_files', ['unknown'])[
                0] if ranked_data.get('source_files') else 'unknown'

            logging.info(
                f"Processing {total_topics} ranked topics from {source_file}")

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

        # Process content enrichment using functional core
        start_time = datetime.utcnow()
        enrichment_result = process_content_enrichment(ranked_data)
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Log results
        stats = enrichment_result['enrichment_statistics']
        logging.info(f"ContentEnricher completed:")
        logging.info(f"  - Total topics processed: {stats['total_topics']}")
        logging.info(
            f"  - External content fetched: {stats['external_content_fetched']}")
        logging.info(
            f"  - High quality sources: {stats['high_quality_sources']}")
        logging.info(
            f"  - Citations generated: {stats['citations_generated']}")

        # Extract container and blob name from output path
        output_parts = output_blob_path.split('/', 1)
        if len(output_parts) != 2:
            return func.HttpResponse(
                json.dumps(create_standard_response(
                    "error",
                    "Invalid output_blob_path format",
                    errors=[{"code": "INVALID_OUTPUT_PATH_FORMAT",
                             "detail": "Path must be in format 'container/blob-name'"}]
                )),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )

        output_container, output_blob_name = output_parts

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
            output_json = json.dumps(enrichment_result, indent=2)
            output_blob_client = blob_service_client.get_blob_client(
                container=output_container, blob=output_blob_name)
            output_blob_client.upload_blob(output_json, overwrite=True)

            logging.info(f"Enriched topics written to {output_blob_path}")

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
                f"Content enrichment completed: {stats['total_topics']} topics processed",
                data={
                    "input_path": input_blob_path,
                    "output_path": output_blob_path,
                    "total_topics": stats['total_topics'],
                    "external_content_fetched": stats['external_content_fetched'],
                    "high_quality_sources": stats['high_quality_sources'],
                    "citations_generated": stats['citations_generated'],
                    "processing_time_seconds": processing_time
                },
                metadata={
                    "function": "ContentEnricher",
                    "version": "2.0",
                    "source_file": source_file
                }
            )),
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in ContentEnricher: {e}")
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
        logging.error(f"Unexpected error in ContentEnricher: {e}")
        return func.HttpResponse(
            json.dumps(create_standard_response(
                "error",
                "Internal server error",
                errors=[{"code": "INTERNAL_ERROR", "detail": str(e)}]
            )),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
