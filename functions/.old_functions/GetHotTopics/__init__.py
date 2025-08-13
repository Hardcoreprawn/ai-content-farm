import logging
import azure.functions as func
import json
import requests
import os
import time
from datetime import datetime

# Test 5: Full pipeline test - comprehensive change (2025-08-12T11:10:30Z)

def check_job_status(womble_url, job_id, headers):
    """Helper function to check job status"""
    try:
        status_response = requests.post(
            womble_url,
            json={"action": "status", "job_id": job_id},
            headers=headers,
            timeout=15
        )
        
        if status_response.status_code == 200:
            return status_response.json()
        else:
            logging.error(f"Status check failed: {status_response.status_code} - {status_response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Failed to check job status: {e}")
        return None


def main(mytimer: func.TimerRequest) -> None:
    logging.info('Timer trigger started - calling Summary Womble.')

    # Configuration for the scheduled run
    womble_config = {
        "source": "reddit",
        "topics": [
            "technology",
            "programming", 
            "MachineLearning",
            "datascience",
            "computerscience",
            "gadgets",
            "Futurology"
        ],
        "limit": 10,
        "credentials": {
            "source": "keyvault"  # Use default Key Vault setup
        },
        "storage": {
            # Use environment variables (set by Azure Function App settings)
        }
    }

    try:
        # Get the function app URL
        function_app_name = os.environ.get("WEBSITE_SITE_NAME", "hot-topics-func")
        womble_url = f"https://{function_app_name}.azurewebsites.net/api/SummaryWomble"
        
        # Optional: include function key for authorization if provided via app settings/Key Vault
        # Recommended for staging/production where SummaryWomble uses authLevel "function"
        womble_key = os.environ.get("SUMMARY_WOMBLE_KEY") or os.environ.get("FUNCTIONS_SUMMARYWOMBLE_KEY")

        logging.info(f"Calling Summary Womble at: {womble_url}")
        
        # Make the HTTP request to the womble function
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "summary-wombles-timer/1.0"
        }

        if womble_key:
            headers["x-functions-key"] = womble_key
            logging.info("Using function key for Summary Womble call (x-functions-key header set)")
        else:
            logging.info("No function key provided for Summary Womble call; expecting anonymous or internal access")
        
        response = requests.post(
            womble_url,
            json=womble_config,
            headers=headers,
            timeout=30  # Reduced timeout since we're just getting a job ticket
        )
        
        if response.status_code == 202:  # Accepted - job started
            result_data = response.json()
            job_id = result_data.get('job_id')
            
            logging.info(f"Summary Womble job started successfully: {job_id}")
            logging.info(f"Topics requested: {result_data.get('topics_requested', [])}")
            logging.info(f"Job status: {result_data.get('status', 'unknown')}")
            
            # Optionally, check job status after a short delay
            if job_id:
                time.sleep(10)  # Wait 10 seconds then check status
                
                status_data = check_job_status(womble_url, job_id, headers)
                if status_data:
                    logging.info(f"Job {job_id} status check: {status_data.get('status', 'unknown')}")
                    
                    progress = status_data.get('progress', {})
                    if progress:
                        logging.info(f"Progress: {progress.get('step', 'unknown')} - {progress.get('completed', 0)}/{progress.get('total', 0)}")
                        
                    if status_data.get('status') == 'completed':
                        results = status_data.get('results', {})
                        total_topics = results.get('total_topics', 0)
                        total_subreddits = results.get('total_subreddits', 0)
                        logging.info(f"Job completed: {total_topics} topics from {total_subreddits} subreddits")
                        
                        # Log individual results
                        for result in results.get('results', []):
                            if result.get('status') == 'success':
                                logging.info(f"subreddit success r/{result['subreddit']}: {result['topics_count']} topics -> {result['blob_name']}")
                            else:
                                logging.error(f"subreddit error r/{result['subreddit']}: {result.get('status')} - {result.get('error', 'Unknown error')}")
                    elif status_data.get('status') == 'failed':
                        error = status_data.get('error', 'Unknown error')
                        logging.error(f"Job {job_id} failed: {error}")
                    else:
                        logging.info(f"Job {job_id} still processing... Status: {status_data.get('status')}")
                else:
                    logging.warning(f"Could not check job status for {job_id}")
                    
        elif response.status_code == 200:
            # Handle legacy response format (direct completion)
            result_data = response.json()
            total_topics = result_data.get('total_topics', 0)
            total_subreddits = result_data.get('total_subreddits', 0)
            
            logging.info(f"Summary Womble completed successfully: {total_topics} topics from {total_subreddits} subreddits")
            
            # Log individual results
            for result in result_data.get('results', []):
                if result.get('status') == 'success':
                    logging.info(f"subreddit success r/{result['subreddit']}: {result['topics_count']} topics -> {result['blob_name']}")
                else:
                    logging.error(f"subreddit error r/{result['subreddit']}: {result.get('status')} - {result.get('error', 'Unknown error')}")
                    
        else:
            error_text = response.text
            logging.error(f"Summary Womble failed with status {response.status_code}: {error_text}")
            
    except requests.exceptions.Timeout:
        logging.error("Summary Womble request timed out")
    except Exception as e:
        logging.error(f"Failed to call Summary Womble: {e}")

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Timer trigger completed.')
