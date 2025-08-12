from enricher_core import process_content_enrichment
import logging
import azure.functions as func
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient

# Import the shared enrichment logic
import sys
sys.path.append('../ContentEnricher')


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    ContentEnricherManual - HTTP triggered function for manual content enrichment.

    Allows manual processing of existing ranked topics blobs for testing and debugging.
    Uses the same core logic as the automatic ContentEnricher function.

    Request body:
    {
        "blob_name": "ranked_20250812_143000.json"
    }
    """
    logging.info("ContentEnricherManual HTTP trigger started")

    blob_name = None

    try:
        # Parse request body
        req_body = req.get_json()
        if not req_body or 'blob_name' not in req_body:
            return func.HttpResponse(
                json.dumps(
                    {"error": "Request body must contain 'blob_name' parameter"}),
                status_code=400,
                mimetype="application/json"
            )

        blob_name = req_body['blob_name']
        logging.info(f"Manual enrichment requested for blob: {blob_name}")

        # Initialize blob service client
        connection_string = os.environ['AzureWebJobsStorage']
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string)

        # Download input blob
        container_name = "content-pipeline"
        blob_path = f"ranked-topics/{blob_name}"

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        if not blob_client.exists():
            return func.HttpResponse(
                json.dumps({"error": f"Blob not found: {blob_path}"}),
                status_code=404,
                mimetype="application/json"
            )

        # Read and parse ranked topics data
        blob_content = blob_client.download_blob().readall().decode('utf-8')
        ranked_data = json.loads(blob_content)

        total_topics = ranked_data.get('total_topics', 0)
        logging.info(
            f"Processing {total_topics} ranked topics from {blob_name}")

        # Process content enrichment using functional core
        enrichment_result = process_content_enrichment(ranked_data)

        # Upload enriched result to blob storage
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_blob_name = f"enriched-topics/enriched_{timestamp}.json"

        output_blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=output_blob_name
        )

        output_json = json.dumps(enrichment_result, indent=2)
        output_blob_client.upload_blob(output_json, overwrite=True)

        # Log and return results
        stats = enrichment_result['enrichment_statistics']

        response_data = {
            "status": "success",
            "input_blob": blob_path,
            "output_blob": output_blob_name,
            "statistics": stats,
            "message": f"Successfully enriched {stats['total_topics']} topics"
        }

        logging.info(f"ContentEnricherManual completed: {stats}")

        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing error: {e}"
        logging.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        error_msg = f"Unexpected error in ContentEnricherManual: {e}"
        logging.error(error_msg)
        if blob_name:
            logging.error(f"Failed processing blob: {blob_name}")

        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=500,
            mimetype="application/json"
        )
