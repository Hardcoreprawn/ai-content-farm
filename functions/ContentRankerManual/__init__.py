import logging
import azure.functions as func
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient

# Import the shared ranking logic
import sys
sys.path.append('../ContentRanker')
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


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    ContentRankerManual - HTTP triggered function for manual content ranking.
    
    Allows manual processing of existing blobs for testing and debugging.
    Uses the same core logic as the automatic ContentRanker function.
    """
    logging.info("ContentRankerManual HTTP trigger started")
    
    blob_name = None
    
    try:
        # Parse request body
        req_body = req.get_json()
        if not req_body or 'blob_name' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body must contain 'blob_name' parameter"}),
                status_code=400,
                mimetype="application/json"
            )
        
        blob_name = req_body['blob_name']
        logging.info(f"Manual processing requested for blob: {blob_name}")
        
        # Read blob data manually
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            raise ValueError("AzureWebJobsStorage environment variable not set")
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(
            container="hot-topics", 
            blob=blob_name
        )
        
        # Download and process blob
        blob_data_bytes = blob_client.download_blob().readall()
        blob_content = blob_data_bytes.decode('utf-8')
        blob_data = json.loads(blob_content)
        
        # Process content ranking using shared core
        ranking_result = process_content_ranking(blob_data, RANKING_CONFIG)
        
        # Save output to ranked-topics container
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_blob_name = f"ranked_manual_{timestamp}.json"
        
        output_blob_client = blob_service_client.get_blob_client(
            container="content-pipeline/ranked-topics",
            blob=output_blob_name
        )
        
        output_json = json.dumps(ranking_result, indent=2)
        output_blob_client.upload_blob(output_json, overwrite=True)
        
        # Return result summary
        result_summary = {
            "status": "success",
            "processed_topics": ranking_result['total_topics'],
            "original_count": blob_data.get('count', 0),
            "output_blob": f"content-pipeline/ranked-topics/{output_blob_name}",
            "processed_at": ranking_result['timestamp']
        }
        
        logging.info(f"Manual ranking completed: {result_summary}")
        
        return func.HttpResponse(
            json.dumps(result_summary, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except FileNotFoundError:
        error_msg = f"Blob '{blob_name}' not found in hot-topics container" if blob_name else "Blob not found"
        logging.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=404,
            mimetype="application/json"
        )
    except Exception as e:
        error_msg = f"Manual ranking error: {str(e)}"
        logging.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=500,
            mimetype="application/json"
        )
