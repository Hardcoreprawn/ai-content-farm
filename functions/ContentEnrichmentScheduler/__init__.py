import logging
import azure.functions as func
import json
import os
from datetime import datetime
import requests


def main(inputBlob: func.InputStream) -> None:
    """
    ContentEnrichmentScheduler - Blob trigger scheduler function.

    Monitors content-pipeline/ranked-topics container and triggers ContentEnricher worker function
    when new ranked topic files arrive.
    """
    logging.info(
        f'ContentEnrichmentScheduler triggered by blob: {inputBlob.name}')

    try:
        # Extract blob name for output path generation
        blob_path = inputBlob.name or "unknown"
        blob_name = blob_path.split('/')[-1]  # Get just the filename

        # Generate output blob name
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        if blob_name.startswith('ranked_'):
            # Replace 'ranked_' with 'enriched_'
            output_blob_name = blob_name.replace('ranked_', 'enriched_', 1)
        else:
            output_blob_name = f"enriched_{timestamp}_{blob_name}"

        # Prepare payload for ContentEnricher worker
        payload = {
            "input_blob_path": f"content-pipeline/ranked-topics/{blob_name}",
            "output_blob_path": f"content-pipeline/enriched-topics/{output_blob_name}"
        }

        # Get ContentEnricher function URL and key
        function_app_name = os.environ.get(
            'FUNCTION_APP_NAME', 'ai-content-staging-func')
        function_key = os.environ.get('CONTENT_ENRICHER_KEY')

        if not function_key:
            logging.error("CONTENT_ENRICHER_KEY environment variable not set")
            raise ValueError("ContentEnricher function key not configured")

        # Call ContentEnricher worker function
        enricher_url = f"https://{function_app_name}.azurewebsites.net/api/ContentEnricher?code={function_key}"

        logging.info(
            f"Calling ContentEnricher worker with input: {payload['input_blob_path']}")

        response = requests.post(
            enricher_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60  # Longer timeout for enrichment processing
        )

        if response.status_code == 200:
            result = response.json()
            logging.info(
                f"ContentEnricher worker completed successfully: {result.get('message', 'No message')}")

            # Log processing metrics if available
            if 'data' in result:
                data = result['data']
                logging.info(f"Processed {data.get('total_topics', 0)} topics")
                logging.info(
                    f"Fetched {data.get('external_content_fetched', 0)} external sources")
                logging.info(
                    f"Generated {data.get('citations_generated', 0)} citations")

        else:
            logging.error(
                f"ContentEnricher worker failed with status {response.status_code}: {response.text}")

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in ContentEnrichmentScheduler: {e}")
        raise

    except requests.RequestException as e:
        logging.error(f"HTTP request error in ContentEnrichmentScheduler: {e}")
        raise

    except Exception as e:
        logging.error(f"Unexpected error in ContentEnrichmentScheduler: {e}")
        logging.error(f"Blob: {inputBlob.name}")
        raise
