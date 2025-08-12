import logging
import azure.functions as func
import json
import os
from datetime import datetime

# Import the functional core from local module
from .enricher_core import process_content_enrichment


def main(inputBlob: func.InputStream, outputBlob: func.Out[str]) -> None:
    """
    ContentEnricher Azure Function - Blob triggered for automatic content enrichment.

    Processes ranked topics and produces enriched topics with research and fact-checking.
    Uses functional programming principles for scalability and testability.

    Trigger: content-pipeline/ranked-topics/ranked_{timestamp}.json
    Output: content-pipeline/enriched-topics/enriched_{timestamp}.json
    """
    logging.info(f'ContentEnricher triggered by blob: {inputBlob.name}')

    try:
        # Parse input blob data
        blob_content = inputBlob.read().decode('utf-8')
        ranked_data = json.loads(blob_content)

        total_topics = ranked_data.get('total_topics', 0)
        source_file = ranked_data.get('source_files', ['unknown'])[
            0] if ranked_data.get('source_files') else 'unknown'

        logging.info(
            f"Processing {total_topics} ranked topics from {source_file}")

        # Process content enrichment using functional core
        enrichment_result = process_content_enrichment(ranked_data)

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

        # Output enriched topics to blob storage
        output_json = json.dumps(enrichment_result, indent=2)
        outputBlob.set(output_json)

        logging.info(
            f"Enriched topics written to content-pipeline/enriched-topics/")

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in ContentEnricher: {e}")
        raise

    except Exception as e:
        logging.error(f"Unexpected error in ContentEnricher: {e}")
        logging.error(f"Blob: {inputBlob.name}")
        raise
