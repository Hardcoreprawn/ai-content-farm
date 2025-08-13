import logging
import azure.functions as func
import json
import os
from datetime import datetime
import requests


def main(inputBlob: func.InputStream) -> None:
    """
    TopicRankingScheduler - Blob trigger scheduler function.

    Monitors hot-topics container and triggers ContentRanker worker function
    when new topic files arrive.
    """
    logging.info(f'TopicRankingScheduler triggered by blob: {inputBlob.name}')

    try:
        # Extract blob name for output path generation
        blob_path = inputBlob.name or "unknown"
        blob_name = blob_path.split('/')[-1]  # Get just the filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_blob_name = f"ranked_{timestamp}_{blob_name}"

        # Prepare payload for ContentRanker worker
        payload = {
            "input_blob_path": f"hot-topics/{blob_name}",
            "output_blob_path": f"content-pipeline/ranked-topics/{output_blob_name}"
        }

        # Get ContentRanker function URL and key
        function_app_name = os.environ.get(
            'FUNCTION_APP_NAME', 'ai-content-staging-func')
        function_key = os.environ.get('CONTENT_RANKER_KEY')

        if not function_key:
            logging.error("CONTENT_RANKER_KEY environment variable not set")
            raise ValueError("ContentRanker function key not configured")

        # Call ContentRanker worker function
        ranker_url = f"https://{function_app_name}.azurewebsites.net/api/ContentRanker?code={function_key}"

        logging.info(
            f"Calling ContentRanker worker with input: {payload['input_blob_path']}")

        response = requests.post(
            ranker_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            logging.info(
                f"ContentRanker worker completed successfully: {result.get('message', 'No message')}")

            # Log processing metrics if available
            if 'data' in result:
                data = result['data']
                logging.info(
                    f"Processed {data.get('total_ranked', 0)}/{data.get('original_count', 0)} topics")

        else:
            logging.error(
                f"ContentRanker worker failed with status {response.status_code}: {response.text}")

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in TopicRankingScheduler: {e}")
        raise

    except requests.RequestException as e:
        logging.error(f"HTTP request error in TopicRankingScheduler: {e}")
        raise

    except Exception as e:
        logging.error(f"Unexpected error in TopicRankingScheduler: {e}")
        logging.error(f"Blob: {inputBlob.name}")
        raise
