import logging
import azure.functions as func
import json
import os
from datetime import datetime

# Import the functional core from local module
from .ranker_core import process_content_ranking


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


def main(inputBlob: func.InputStream, outputBlob: func.Out[str]) -> None:
    """
    ContentRanker Azure Function - Triggered by new Reddit topics in blob storage.

    Processes raw Reddit topics and produces ranked topics for content enrichment.
    Uses functional programming principles for scalability and testability.
    """
    logging.info(f'ContentRanker triggered by blob: {inputBlob.name}')
    
    try:
        # Parse input blob data
        blob_content = inputBlob.read().decode('utf-8')
        blob_data = json.loads(blob_content)
        
        logging.info(
            f"Processing {blob_data.get('count', 0)} topics from {blob_data.get('subject', 'unknown')} subreddit")
        
        # Process content ranking using functional core
        ranking_result = process_content_ranking(blob_data, RANKING_CONFIG)
        
        # Log results
        total_ranked = ranking_result['total_topics']
        original_count = blob_data.get('count', 0)
        
        logging.info(
            f"ContentRanker completed: {total_ranked}/{original_count} topics ranked and filtered")
        
        if total_ranked > 0:
            top_score = ranking_result['topics'][0]['ranking_score']
            logging.info(f"Top ranking score: {top_score}")
        
        # Output ranked topics to blob storage
        output_json = json.dumps(ranking_result, indent=2)
        outputBlob.set(output_json)
        
        logging.info(
            f"Ranked topics written to content-pipeline/ranked-topics/")
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error in ContentRanker: {e}")
        logging.error(f"Blob content preview: {inputBlob.read()[:200]}")
        raise
        
    except Exception as e:
        logging.error(f"Unexpected error in ContentRanker: {e}")
        logging.error(f"Blob: {inputBlob.name}, Config: {RANKING_CONFIG}")
        raise